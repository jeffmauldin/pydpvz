"""
ParaView symmetric MPI utility to probe a .dpvtk archive for available data arrays.

This script deserializes a specific timestep of a .dpvtk file and inspects the underlying
VTK blocks (`vtkPartitionedDataSetCollection`). It extracts the names of all Point, Cell, 
and Field arrays. It uses an MPI Reduction (`comm.reduce`) with a custom set-union operator 
to safely aggregate array names across all participating ranks, ensuring that even sparsely 
distributed arrays are accurately reported.

Execution Context:
Must be launched with `mpiexec -np N pvbatch --sym dpvtkprobe.py ...`
"""

import sys
import argparse
from mpi4py import MPI
import pydpvz
from pydpvz.vtk_deserializer import deserialize_vtk_from_buffer

def set_union(set_a, set_b, datatype):
    """Custom MPI reduction operator to union two sets of strings."""
    return set_a.union(set_b)

def get_array_names(vtk_data_object):
    """Extracts a set of array names from a VTK field data object (e.g., PointData)."""
    names = set()
    if vtk_data_object is None:
        return names
    for i in range(vtk_data_object.GetNumberOfArrays()):
        names.add(vtk_data_object.GetArrayName(i))
    return names

def probe_dpvtk(filename, timestep=0):
    """
    Opens a .dpvtk file, deserializes a specific timestep, and probes its VTK arrays.
    
    Args:
        filename (str): The input .dpvtk file.
        timestep (int): The integer timestep index to probe.
    """
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    archive = pydpvz.DPvzVtk(filename, pydpvz.DPvzMode.DPvzReadOnly, comm, False)
    steps = archive.get_steps()
    
    if steps == 0:
        if rank == 0:
            print("Archive contains no timesteps.")
        return
        
    if timestep < 0 or timestep >= steps:
        if rank == 0:
            print(f"Error: Requested timestep {timestep} is out of bounds (0 to {steps-1}).")
        return
        
    map_vec = archive.get_map()
    entry = map_vec[timestep]
    step_toc = archive.get_step_toc(entry)
    
    local_point_arrays = set()
    local_cell_arrays = set()
    local_field_arrays = set()
    local_counts = {}
    
    for w_rank in range(rank, entry.ranks, size):
        rank_entry = step_toc[w_rank]
        buffer_bytes = archive.get_data(rank_entry)
        items = deserialize_vtk_from_buffer(buffer_bytes)
        
        if w_rank not in local_counts:
            local_counts[w_rank] = {'points': 0, 'cells': 0}
            
        for item in items:
            ds = item["dataset"]
            if ds is not None:
                local_point_arrays.update(get_array_names(ds.GetPointData()))
                local_cell_arrays.update(get_array_names(ds.GetCellData()))
                local_field_arrays.update(get_array_names(ds.GetFieldData()))
                
                local_counts[w_rank]['points'] += ds.GetNumberOfPoints()
                local_counts[w_rank]['cells'] += ds.GetNumberOfCells()
                
    # Create custom MPI Op for set union
    set_union_op = MPI.Op.Create(set_union, commute=True)
    
    global_point_arrays = comm.reduce(local_point_arrays, op=set_union_op, root=0)
    global_cell_arrays = comm.reduce(local_cell_arrays, op=set_union_op, root=0)
    global_field_arrays = comm.reduce(local_field_arrays, op=set_union_op, root=0)
    set_union_op.Free()
    
    # Gather rank counts
    gathered_counts = comm.gather(local_counts, root=0)
    
    if rank == 0:
        global_counts = {}
        for gc in gathered_counts:
            global_counts.update(gc)
            
        total_points = sum(c['points'] for c in global_counts.values())
        total_cells = sum(c['cells'] for c in global_counts.values())
        
        print(f"\n--- DPvz Probe: {filename} (Timestep {timestep}) ---")
        
        print(f"\nGlobal Dataset Structure:")
        print(f"  Total Points : {total_points:,}")
        print(f"  Total Cells  : {total_cells:,}")
        
        print(f"\nPer-Rank Breakdown ({entry.ranks} original writing ranks):")
        
        # We print all ranks if <= 16 or verbose is enabled
        if entry.ranks <= 16 or args.verbose:
            for r in range(entry.ranks):
                pts = global_counts.get(r, {}).get('points', 0)
                cls = global_counts.get(r, {}).get('cells', 0)
                print(f"  Rank {r:3d}: {pts:10,} pts, {cls:10,} cls")
        else:
            pt_list = [c['points'] for c in global_counts.values()]
            cl_list = [c['cells'] for c in global_counts.values()]
            print(f"  (Output truncated. Use --verbose to see all {entry.ranks} ranks)")
            print(f"  Points per Rank -> Min: {min(pt_list):,}, Max: {max(pt_list):,}, Avg: {int(sum(pt_list)/len(pt_list)):,}")
            print(f"  Cells per Rank  -> Min: {min(cl_list):,}, Max: {max(cl_list):,}, Avg: {int(sum(cl_list)/len(cl_list)):,}")
            
        print(f"\nData Arrays:")
        print(f"  Point Data : {list(global_point_arrays) if global_point_arrays else 'None'}")
        print(f"  Cell Data  : {list(global_cell_arrays) if global_cell_arrays else 'None'}")
        print(f"  Field Data : {list(global_field_arrays) if global_field_arrays else 'None'}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Probe a .dpvtk archive for available data arrays.")
    parser.add_argument("input", help="Input .dpvtk file")
    parser.add_argument("--timestep", type=int, default=0, help="Timestep index to probe (defaults to 0).")
    parser.add_argument("--verbose", action="store_true", help="Print complete output including massive rank count lists.")
    
    # Use parse_known_args in case it's run via pvbatch
    args, unknown = parser.parse_known_args()
    
    probe_dpvtk(args.input, args.timestep)
