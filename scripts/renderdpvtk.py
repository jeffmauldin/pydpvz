"""
Legacy test script for rendering a single frame. 
Superceded by the robust `dpvtkscreenshot.py`.
"""

import sys
from mpi4py import MPI
import paraview.simple as paraview_simple
import pydpvz
from pydpvz.vtk_deserializer import deserialize_vtk_from_buffer
import vtk

def render_dpvtk(filename, output_png):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # 1. Read the DPvz archive and construct the local VTK dataset
    archive = pydpvz.DPvzVtk(filename, pydpvz.DPvzMode.DPvzReadOnly, comm, False)
    steps = archive.get_steps()
    
    if steps == 0:
        if rank == 0:
            print("Archive contains no timesteps.")
        return

    map_vec = archive.get_map()
    entry = map_vec[0] # Just render the first timestep
    step_toc = archive.get_step_toc(entry)
    
    pdc = vtk.vtkPartitionedDataSetCollection()
    
    part_counters = {}
    if rank < entry.ranks:
        rank_entry = step_toc[rank]
        buffer_bytes = archive.get_data(rank_entry)
        items = deserialize_vtk_from_buffer(buffer_bytes)
        
        for item in items:
            idx = item["index"]
            name = item["name"]
            ds = item["dataset"]
            while pdc.GetNumberOfPartitionedDataSets() <= idx:
                pdc.SetNumberOfPartitionedDataSets(idx + 1)
            if name:
                meta = pdc.GetMetaData(idx)
                if meta:
                    meta.Set(vtk.vtkCompositeDataSet.NAME(), name)
            if ds is not None:
                p_idx = part_counters.get(idx, 0)
                pdc.SetPartition(idx, p_idx, ds)
                part_counters[idx] = p_idx + 1
            
    # 2. Push the local VTK dataset into the ParaView pipeline
    # TrivialProducer allows us to bridge raw VTK objects in Python memory 
    # to ParaView's proxy-based pipeline.
    producer = paraview_simple.TrivialProducer()
    
    # Get the underlying C++ VTK algorithm object for this proxy and set its dataset
    client_obj = producer.GetClientSideObject()
    client_obj.SetOutput(pdc)
    
    # Update the pipeline so ParaView knows about the data bounds, etc.
    producer.UpdatePipeline()

    # 3. Setup ParaView visualization
    # We only need to configure the view and save the screenshot on rank 0,
    # but the pipeline update and rendering commands are collective in symmetric mode.
    view = paraview_simple.GetActiveViewOrCreate('RenderView')
    
    # Show the producer
    display = paraview_simple.Show(producer, view, 'GeometryRepresentation')
    
    # Default coloring is fine
    
    # Reset camera to fit the newly loaded dataset
    paraview_simple.ResetCamera(view)
    
    # Ensure the view is rendered
    paraview_simple.Render()

    # 4. Save screenshot
    # Only rank 0 actually writes the final composited PNG file
    if rank == 0:
        print(f"[0] Saving screenshot to {output_png}...")
        paraview_simple.SaveScreenshot(output_png, view, ImageResolution=[1920, 1080])
        print(f"[0] Screenshot saved successfully!")
    else:
        # In symmetric mode, other ranks participate in parallel rendering but don't write the file.
        paraview_simple.SaveScreenshot(output_png, view, ImageResolution=[1920, 1080])

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: pvbatch --sym renderdpvtk.py <input.dpvtk> <output.png>")
        sys.exit(1)
        
    filename = sys.argv[1]
    output_png = sys.argv[2]
    render_dpvtk(filename, output_png)
