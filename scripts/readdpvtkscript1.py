"""
Legacy test script demonstrating raw deserialization of a .dpvtk archive.
Used during initial development to verify round-robin rank reading logic.
"""

import sys
import paraview.simple as paraview_simple
from mpi4py import MPI
import pydpvz
from pydpvz.vtk_deserializer import populate_pdc_from_buffer
import vtk

def read_dpvtk(filename):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    print(f"[{rank}] Opening archive {filename} for reading...")
    
    archive = pydpvz.DPvzVtk(filename, pydpvz.DPvzMode.DPvzReadOnly, comm, False)
    steps = archive.get_steps()
    
    print(f"[{rank}] Found {steps} time steps in archive.")
    
    # Retrieve the map of all cycles/times
    map_vec = archive.get_map()
    
    for i in range(steps):
        entry = map_vec[i]
        print(f"[{rank}] Processing cycle {entry.cycle}, time {entry.time}, with {entry.ranks} writing ranks.")
        
        # Get the Table of Contents for this specific time step
        step_toc = archive.get_step_toc(entry)
        
        # Determine which rank TOC entry this current reading MPI rank should process.
        # This is a naive load balancing: reading rank processes writing rank of the same ID.
        if rank < entry.ranks:
            rank_entry = step_toc[rank]
            print(f"[{rank}] Extracting data buffer of size {rank_entry.inflated_size} bytes...")
            
            # Extract raw bytes (the VTK XML streams with <FILE NAME> headers)
            buffer_bytes = archive.get_data(rank_entry)
            
            # Put them into a vtkPartitionedDataSetCollection for ParaView pipeline
            pdc = vtk.vtkPartitionedDataSetCollection()
            part_counters = {}
            items = populate_pdc_from_buffer(pdc, buffer_bytes, part_counters)
                
            print(f"[{rank}] Successfully loaded {len(items)} partitions for cycle {entry.cycle}.")
        else:
            print(f"[{rank}] Idle for this cycle (reading ranks {size} > writing ranks {entry.ranks}).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: pvbatch --sym readdpvtkscript1.py <input.dpvtk>")
        sys.exit(1)
        
    filename = sys.argv[1]
    read_dpvtk(filename)
