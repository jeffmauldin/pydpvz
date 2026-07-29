"""
ParaView symmetric MPI utility to render a single screenshot from a .dpvtk archive.

This script uses `pydpvz` to deserialize a single timestep from a .dpvtk file into a 
distributed VTK memory object, then pushes it into ParaView's offscreen rendering pipeline 
via `TrivialProducer`. Camera vectors and JSON styling configurations can be applied before 
compositing a final PNG.

Execution Context:
Must be launched with `mpiexec -np N pvbatch --sym dpvtkscreenshot.py ...`
"""

import sys
import argparse
import ast
import json
from mpi4py import MPI
import paraview.simple as paraview_simple
import pydpvz
from pydpvz.vtk_deserializer import deserialize_vtk_from_buffer
import vtk

def render_dpvtk(filename, output_png, view_direction=None, timestep=0, config_path=None):
    """
    Renders a specific timestep of a .dpvtk archive to a PNG image.
    
    Args:
        filename (str): Path to the input .dpvtk file.
        output_png (str): Path for the output PNG image.
        view_direction (list, optional): 3D vector representing camera look direction. Defaults to [0.0, 0.0, -1.0].
        timestep (int): The timestep index to render. Defaults to 0.
        config_path (str, optional): Path to a JSON configuration for advanced rendering options.
    """
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # 1. Read the DPvz archive and construct the local VTK dataset
    if rank == 0:
        print(f"about to start read of {filename} at timestep {timestep}")
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
    
    pdc = vtk.vtkPartitionedDataSetCollection()
    
    local_part_idx = 0
    for w_rank in range(rank, entry.ranks, size):
        rank_entry = step_toc[w_rank]
        buffer_bytes = archive.get_data(rank_entry)
        datasets = deserialize_vtk_from_buffer(buffer_bytes)
        
        for ds in datasets:
            pdc.SetPartition(0, local_part_idx, ds)
            local_part_idx += 1
            
    if rank == 0:
        print(f"completed read of {filename} at timestep {timestep}")
            
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
    
    # 3.5 Apply optional JSON configuration
    if config_path:
        with open(config_path, 'r') as f:
            config = json.load(f)
        if 'color_by' in config:
            cb = config['color_by']
            display.ColorArrayName = [cb.get('association', 'POINTS'), cb.get('array_name')]
            lut = paraview_simple.GetColorTransferFunction(cb.get('array_name'))
            if 'range_min' in cb and 'range_max' in cb:
                lut.RescaleTransferFunction(cb['range_min'], cb['range_max'])
            display.LookupTable = lut
    
    # Use the user-provided or default viewing direction
    # To look *along* vector V, we place the camera at -V
    view.CameraPosition = [-view_direction[0], -view_direction[1], -view_direction[2]]
    view.CameraFocalPoint = [0.0, 0.0, 0.0]
    
    # Prevent gimbal lock if looking straight down/up the Z axis
    if view_direction[0] == 0.0 and view_direction[1] == 0.0:
        view.CameraViewUp = [0.0, 1.0, 0.0]
    else:
        view.CameraViewUp = [0.0, 0.0, 1.0]

    # Reset camera to fit the newly loaded dataset while preserving the viewing direction
    paraview_simple.ResetCamera(view)

    
    # Ensure the view is rendered
    paraview_simple.Render()

    # 4. Save screenshot
    # Only rank 0 actually writes the final composited PNG file
    if rank == 0:
        print(f"about to save screenshot {output_png} for timestep {timestep}")
        paraview_simple.SaveScreenshot(output_png, view, ImageResolution=[1920, 1080])
        print(f"completed save screenshot {output_png} for timestep {timestep}")
    else:
        # In symmetric mode, other ranks participate in parallel rendering but don't write the file.
        paraview_simple.SaveScreenshot(output_png, view, ImageResolution=[1920, 1080])

def parse_vector(val):
    try:
        vec = ast.literal_eval(val)
        if not isinstance(vec, list) or len(vec) != 3:
            raise ValueError()
        return [float(x) for x in vec]
    except Exception:
        raise argparse.ArgumentTypeError("View direction must be a list of 3 numbers, e.g., '[0,1,0]'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render a .dpvtk file to an image.")
    parser.add_argument("input", help="Input .dpvtk file")
    parser.add_argument("output", help="Output .png file")
    parser.add_argument("--viewdirection", "-vwdr", type=parse_vector, default=[0.0, 0.0, -1.0],
                        help="Optional look direction vector, e.g. '[0, 0, -1]'. Defaults to [0, 0, -1].")
    parser.add_argument("--timestep", type=int, default=0, help="Timestep index to render (defaults to 0).")
    parser.add_argument("--config", type=str, default=None, help="Path to JSON configuration file for rendering options.")

    # Use parse_known_args because pvbatch passes its own arguments (e.g. --sym, --mesa)
    args, unknown = parser.parse_known_args()
        
    render_dpvtk(args.input, args.output, args.viewdirection, args.timestep, args.config)
