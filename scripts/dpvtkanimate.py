import sys
import argparse
import ast
from mpi4py import MPI
import paraview.simple as paraview_simple
import pydpvz
from pydpvz.vtk_deserializer import deserialize_vtk_from_buffer
import vtk

def render_dpvtk_animation(filename, output_basename, view_direction=None, timesteprange=None):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # 1. Read the DPvz archive
    if rank == 0:
        print(f"Opening archive {filename} for animation...")
    archive = pydpvz.DPvzVtk(filename, pydpvz.DPvzMode.DPvzReadOnly, comm, False)
    steps = archive.get_steps()
    
    if steps == 0:
        if rank == 0:
            print("Archive contains no timesteps.")
        return

    # 2. Determine timestep range
    start_idx = 0
    end_idx = steps - 1
    
    if timesteprange is not None:
        start_idx, end_idx = timesteprange
        if start_idx < 0:
            start_idx = 0
        if end_idx >= steps:
            end_idx = steps - 1
            
        if start_idx > end_idx or start_idx >= steps:
            if rank == 0:
                print(f"Error: Invalid timestep range {timesteprange} for archive with {steps} steps.")
            return

    map_vec = archive.get_map()

    # 3. Setup ParaView visualization pipeline
    producer = paraview_simple.TrivialProducer()
    view = paraview_simple.GetActiveViewOrCreate('RenderView')
    display = paraview_simple.Show(producer, view, 'GeometryRepresentation')
    
    # Configure camera viewing direction
    view.CameraPosition = [-view_direction[0], -view_direction[1], -view_direction[2]]
    view.CameraFocalPoint = [0.0, 0.0, 0.0]
    if view_direction[0] == 0.0 and view_direction[1] == 0.0:
        view.CameraViewUp = [0.0, 1.0, 0.0]
    else:
        view.CameraViewUp = [0.0, 0.0, 1.0]

    # 4. Loop and render
    for timestep in range(start_idx, end_idx + 1):
        if rank == 0:
            print(f"about to start read of {filename} at timestep {timestep}")
            
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

        # Push data to pipeline
        client_obj = producer.GetClientSideObject()
        client_obj.SetOutput(pdc)
        producer.MarkModified(producer)
        producer.UpdatePipeline()
        
        # Reset camera to fit bounds for the frame while preserving direction
        paraview_simple.ResetCamera(view)
        paraview_simple.Render()
        
        output_png = f"{output_basename}_{timestep:04d}.png"
        
        if rank == 0:
            print(f"about to save screenshot {output_png} for timestep {timestep}")
            paraview_simple.SaveScreenshot(output_png, view, ImageResolution=[1920, 1080])
            print(f"completed save screenshot {output_png} for timestep {timestep}")
        else:
            paraview_simple.SaveScreenshot(output_png, view, ImageResolution=[1920, 1080])


def parse_vector(val):
    try:
        vec = ast.literal_eval(val)
        if not isinstance(vec, list) or len(vec) != 3:
            raise ValueError()
        return [float(x) for x in vec]
    except Exception:
        raise argparse.ArgumentTypeError("View direction must be a list of 3 numbers, e.g., '[0,1,0]'")

def parse_range(val):
    try:
        r = ast.literal_eval(val)
        if not isinstance(r, list) or len(r) != 2:
            raise ValueError()
        return [int(x) for x in r]
    except Exception:
        raise argparse.ArgumentTypeError("Timestep range must be a list of 2 integers, e.g., '[24,36]'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Animate a .dpvtk file into a series of images.")
    parser.add_argument("input", help="Input .dpvtk file")
    parser.add_argument("output_basename", help="Output image base name (e.g. 'basename' -> 'basename_0000.png')")
    parser.add_argument("--viewdirection", "-vwdr", type=parse_vector, default=[0.0, 0.0, -1.0],
                        help="Optional look direction vector, e.g. '[0, 0, -1]'. Defaults to [0, 0, -1].")
    parser.add_argument("--timesteprange", type=parse_range, default=None,
                        help="Optional range of timesteps to render, e.g. '[24,36]'.")

    # Use parse_known_args because pvbatch passes its own arguments (e.g. --sym, --mesa)
    args, unknown = parser.parse_known_args()
        
    render_dpvtk_animation(args.input, args.output_basename, args.viewdirection, args.timesteprange)
