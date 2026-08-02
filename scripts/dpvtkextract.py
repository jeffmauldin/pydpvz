"""
ParaView symmetric MPI utility to extract a .dpvtk archive back into standard VTK files.

This script executes in parallel, reading distributed data blocks using `pydpvz.DPvzVtk`
and reconstructing a standard ParaView VTK pipeline. It then utilizes `SaveData()` to 
export the distributed datasets back into a standard format like `.vtpc` or `.vtm`,
acting as the reverse operation of `dpvtkconvert.py`.

Execution Context:
Must be launched with `mpiexec -np N pvbatch --sym dpvtkextract.py ...`
"""

import argparse
import sys
import paraview.simple as paraview_simple
from mpi4py import MPI
import pydpvz
from pydpvz.vtk_deserializer import populate_pdc_from_buffer
import vtk

def extract_dpvtk(filename, output_prefix):
    """
    Reads a .dpvtk file and saves each timestep as a standard ParaView VTK dataset.
    
    Args:
        filename (str): The input .dpvtk archive path.
        output_prefix (str): Base prefix for the output VTK files (e.g., 'out' -> 'out_0000.vtpc').
    """
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    if rank == 0:
        print(f"Opening archive {filename} for extraction...")
    
    archive = pydpvz.DPvzVtk(filename, pydpvz.DPvzMode.DPvzReadOnly, comm, False)
    steps = archive.get_steps()
    
    if steps == 0:
        if rank == 0:
            print("Archive contains no timesteps.")
        return

    map_vec = archive.get_map()
    
    # We create a TrivialProducer to hold our data and pass to ParaView
    producer = paraview_simple.TrivialProducer()

    for t in range(steps):
        entry = map_vec[t]
        step_toc = archive.get_step_toc(entry)
        
        pdc = vtk.vtkPartitionedDataSetCollection()
        
        part_counters = {}
        for w_rank in range(rank, entry.ranks, size):
            rank_entry = step_toc[w_rank]
            buffer_bytes = archive.get_data(rank_entry)
            populate_pdc_from_buffer(pdc, buffer_bytes, part_counters)
                
        client_obj = producer.GetClientSideObject()
        client_obj.SetOutput(pdc)
        producer.MarkModified(producer)
        producer.UpdatePipeline()
        
        output_file = f"{output_prefix}_{t:04d}.vtpc"
        
        if rank == 0:
            print(f"Extracting timestep {t} to {output_file}...")
            
        writer = paraview_simple.XMLPartitionedDataSetCollectionWriter(Input=producer, FileName=output_file)
        writer.UpdatePipeline()
        
        if rank == 0:
            print(f"Completed extraction of timestep {t}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract a .dpvtk file into standard VTK files.")
    parser.add_argument("input", help="Input .dpvtk file")
    parser.add_argument("output_prefix", help="Output file prefix (e.g., 'extracted_data' will produce 'extracted_data_0000.vtm')")

    args, unknown = parser.parse_known_args()
    extract_dpvtk(args.input, args.output_prefix)
