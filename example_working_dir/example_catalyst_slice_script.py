from paraview.simple import *
import os

def catalyst_initialize():
    pass

def catalyst_execute(info=None):
    global slice_filter
    
    cycle = info.cycle if info else 0
    
    if not os.path.exists('catalyst_extracts'):
        try:
            os.makedirs('catalyst_extracts')
        except FileExistsError:
            pass
            
    print(f"      [Catalyst] Applying slice filter for cycle {cycle}...")
    
    # Construct the pipeline once
    if 'slice_filter' not in globals():
        producer = FindSource("input")
        
        # As requested: convert PDC to MultiBlock to make the Slice filter happy
        converter = ConvertToMultiBlock(Input=producer)
        
        slice_filter = Slice(Input=converter)
        slice_filter.SliceType = "Plane"
        slice_filter.SliceType.Normal = [1.0, 0.0, 0.0]
        
    slice_filter.UpdatePipeline()
    
    out_path = f"catalyst_extracts/slice_output_{cycle:04d}.vtm"
    from mpi4py import MPI
    if MPI.COMM_WORLD.Get_rank() == 0:
        print(f"      [Catalyst] Writing slice data to {out_path}...")
    
    # Use SaveData directly on the multiblock
    SaveData(out_path, proxy=slice_filter)
    
def catalyst_finalize():
    global slice_filter
    if 'slice_filter' in globals():
        Delete(slice_filter)
    print("Catalyst slice script finalized successfully.")
