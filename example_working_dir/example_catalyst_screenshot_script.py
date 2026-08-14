from paraview.simple import *
import os

def catalyst_initialize():
    pass

def catalyst_execute(info=None):
    global view
    cycle = info.cycle if info else 0
    
    if not os.path.exists('catalyst_extracts'):
        try:
            os.makedirs('catalyst_extracts')
        except FileExistsError:
            pass
            
    print(f"      [Catalyst] Rendering screenshot for cycle {cycle}...")
    
    producer = FindSource("input")
    
    # Create or get the active view
    if 'view' not in globals():
        view = CreateRenderView()
        # Set view size
        view.ViewSize = [800, 600]
        
        # Show the data in the view
        display = Show(producer, view)
        
        # Color by EQPS (Equivalent Plastic Strain) - it is an element/cell array in the CAN dataset
        ColorBy(display, ('CELLS', 'EQPS'))
        display.SetScalarBarVisibility(view, True)
        
        # Set the camera to look parallel to the Y axis in the (0, -1, 0) direction
        # By setting the position to +Y and focal point to the origin, 
        # the view direction vector becomes (0, -1, 0).
        view.CameraPosition = [0.0, 1.0, 0.0]
        view.CameraFocalPoint = [0.0, 0.0, 0.0]
        view.CameraViewUp = [0.0, 0.0, 1.0] # Keep Z axis pointing 'up' visually
        
        # Reset the camera to fit the dataset, which will automatically adjust
        # the camera distance and center the focal point while preserving our angle!
        view.ResetCamera()
        
    # EVERY CYCLE: Update the pipeline to grab the new timestep's data bounds,
    # then dynamically rescale the color legend to the current min/max EQPS range.
    producer.UpdatePipeline()
    display = GetDisplayProperties(producer, view)
    display.RescaleTransferFunctionToDataRange(True, False)
    
    # Save the screenshot
    # ParaView handles the parallel compositing natively
    out_path = f"catalyst_extracts/screenshot_{cycle:04d}.png"
    SaveScreenshot(out_path, view, ImageResolution=[800, 600])

def catalyst_finalize():
    print("Catalyst screenshot script finalized successfully.")
