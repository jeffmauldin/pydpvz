import argparse
import sys
from mpi4py import MPI
import paraview.simple as paraview_simple
import pydpvz
from pydpvz.vtk_deserializer import deserialize_vtk_from_buffer
import pydpvz.vtk_serializer as vtk_serializer
import vtk

def filter_dpvtk(input_file, output_file, filter_name):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    if rank == 0:
        print(f"Opening archive {input_file} for filtering...")
    
    in_archive = pydpvz.DPvzVtk(input_file, pydpvz.DPvzMode.DPvzReadOnly, comm, False)
    out_archive = pydpvz.DPvzVtk(output_file, pydpvz.DPvzMode.DPvzReplace, comm, False)
    
    steps = in_archive.get_steps()
    if steps == 0:
        if rank == 0:
            print("Archive contains no timesteps.")
        return

    map_vec = in_archive.get_map()
    
    producer = paraview_simple.TrivialProducer()
    
    # Instantiate the requested filter
    filter_name = filter_name.lower()
    if filter_name == "slice":
        pv_filter = paraview_simple.Slice(Input=producer)
    elif filter_name == "contour":
        pv_filter = paraview_simple.Contour(Input=producer)
    else:
        if rank == 0:
            print(f"Error: Unknown filter '{filter_name}'. Supported: slice, contour.")
        return

    for t in range(steps):
        entry = map_vec[t]
        step_toc = in_archive.get_step_toc(entry)
        
        pdc = vtk.vtkPartitionedDataSetCollection()
        
        local_part_idx = 0
        for w_rank in range(rank, entry.ranks, size):
            rank_entry = step_toc[w_rank]
            buffer_bytes = in_archive.get_data(rank_entry)
            datasets = deserialize_vtk_from_buffer(buffer_bytes)
            
            for ds in datasets:
                pdc.SetPartition(0, local_part_idx, ds)
                local_part_idx += 1
                
        client_obj = producer.GetClientSideObject()
        client_obj.SetOutput(pdc)
        producer.MarkModified(producer)
        producer.UpdatePipeline()
        
        if rank == 0:
            print(f"Applying {filter_name} filter to timestep {t}...")
            
        pv_filter.UpdatePipeline()
        # Get the filtered dataset
        filtered_ds = pv_filter.GetClientSideObject().GetOutputDataObject(0)
        
        # Determine current cycle and time from original archive
        time_val = entry.time
        cycle = t
        
        # Re-serialize the filtered VTK data
        if filtered_ds.IsA("vtkPartitionedDataSetCollection"):
            xml_string = vtk_serializer.serialize_partitioned_dataset_collection(filtered_ds, rank, cycle, time_val)
        elif filtered_ds.IsA("vtkMultiBlockDataSet"):
            xml_string = vtk_serializer.serialize_multiblock_dataset(filtered_ds, rank, cycle, time_val)
        else:
            # If it's a generic dataset, convert it to PDC for safe serialization
            new_pdc = vtk.vtkPartitionedDataSetCollection()
            new_pdc.SetPartition(0, 0, filtered_ds)
            xml_string = vtk_serializer.serialize_partitioned_dataset_collection(new_pdc, rank, cycle, time_val)
            
        out_archive.write(cycle, time_val, xml_string)
        
        if rank == 0:
            print(f"Completed filter and write of timestep {t}.")
            
    if rank == 0:
        print(f"Successfully filtered {input_file} into {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply a ParaView filter to a .dpvtk file and save a new one.")
    parser.add_argument("input", help="Input .dpvtk file")
    parser.add_argument("output", help="Output .dpvtk file")
    parser.add_argument("--filter", required=True, help="Filter to apply (e.g. 'slice', 'contour')")

    args, unknown = parser.parse_known_args()
    filter_dpvtk(args.input, args.output, args.filter)
