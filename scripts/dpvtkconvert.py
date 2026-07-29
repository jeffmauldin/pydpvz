"""
Unified ParaView conversion utility for ingesting various VTK formats into .dpvtk archives.

This script leverages ParaView's native `OpenDataFile()` reader to ingest formats like `.vtpc` 
(Exodus II), `.tpcs`, or `.vtm`, and then feeds the pipeline into the dynamically loaded 
`DPvtkWriter` plugin. The script features a manual timestep pipeline update loop to provide 
console feedback and ensure robust memory handling.

Execution Context:
Must be executed in ParaView Symmetric MPI mode:
`mpiexec.mpich -np 4 pvbatch --sym scripts/dpvtkconvert.py --input "data_*.vtpc" --output out.dpvtk`
"""

import sys
import glob
import os
import argparse
from paraview.simple import *
from mpi4py import MPI

def main():
    """
    Parses CLI arguments, initializes the MPI communicator, dynamically loads the DPvtkWriter 
    plugin, constructs the ParaView pipeline, and executes the timestepping loop.
    """
    parser = argparse.ArgumentParser(description="Convert ParaView datasets to .dpvtk archives.")
    parser.add_argument("--input", required=True, nargs='+', help="Input file(s) or glob pattern (e.g. 'data_*.vtpc')")
    parser.add_argument("--output", required=True, help="Output .dpvtk file")
    
    # Parse known args because pvbatch might pass extra args
    args, _ = parser.parse_known_args()
    
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()

    expanded_inputs = []
    for f in args.input:
        if '*' in f or '?' in f:
            expanded_inputs.extend(sorted(glob.glob(f)))
        else:
            expanded_inputs.append(f)
            
    if not expanded_inputs:
        if rank == 0:
            print("Error: No input files found matching the provided pattern.")
        sys.exit(1)

    # Load the plugin
    plugin_path = os.path.join(os.path.dirname(__file__), "dpvtk_writer_plugin.py")
    if rank == 0:
        print(f"Loading plugin from {plugin_path}...")
    LoadPlugin(plugin_path, ns=globals())

    if rank == 0:
        print(f"Loading {len(expanded_inputs)} files into a file series reader...")
    reader = OpenDataFile(expanded_inputs)
    
    timesteps = reader.TimestepValues
    if not timesteps:
        timesteps = [0.0]

    if rank == 0:
        print(f"Saving to {args.output} across {len(timesteps)} timesteps via the plugin...")
        
    # Bypass the sometimes-flaky vtkSMWriterFactory by directly instantiating the plugin proxy
    writer = DPvtkWriter(Input=reader, FileName=args.output)
    
    for i, t in enumerate(timesteps):
        if rank == 0:
            print(f"  -> Processing timestep {i+1}/{len(timesteps)} (time={t})...")
        reader.UpdatePipeline(time=t)
        writer.UpdatePipeline()
    
    if rank == 0:
        print("Conversion complete!")

if __name__ == "__main__":
    main()
