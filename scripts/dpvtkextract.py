import argparse
import sys
from mpi4py import MPI
import paraview.simple as paraview_simple
import pydpvz
from pydpvz.vtk_deserializer import deserialize_vtk_from_buffer
import vtk

def extract_dpvtk(filename, output_prefix):
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
        
        local_part_idx = 0
        for w_rank in range(rank, entry.ranks, size):
            rank_entry = step_toc[w_rank]
            buffer_bytes = archive.get_data(rank_entry)
            datasets = deserialize_vtk_from_buffer(buffer_bytes)
            
            for ds in datasets:
                pdc.SetPartition(0, local_part_idx, ds)
                local_part_idx += 1
                
        client_obj = producer.GetClientSideObject()
        client_obj.SetOutput(pdc)
        producer.MarkModified(producer)
        producer.UpdatePipeline()
        
        output_file = f"{output_prefix}_{t:04d}.vtpc"
        
        if rank == 0:
            print(f"Extracting timestep {t} to {output_file}...")
            
        paraview_simple.SaveData(output_file, proxy=producer)
        
        if rank == 0:
            print(f"Completed extraction of timestep {t}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract a .dpvtk file into standard VTK files.")
    parser.add_argument("input", help="Input .dpvtk file")
    parser.add_argument("output_prefix", help="Output file prefix (e.g., 'extracted_data' will produce 'extracted_data_0000.vtm')")

    args, unknown = parser.parse_known_args()
    extract_dpvtk(args.input, args.output_prefix)
