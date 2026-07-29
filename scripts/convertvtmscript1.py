"""
Legacy conversion script for .vtm (VTK MultiBlock) datasets.
Superceded by the unified `dpvtkconvert.py` script.
"""

import sys
import argparse
import paraview.simple as pv
from mpi4py import MPI
import pydpvz
from pydpvz.vtk_serializer import serialize_multiblock_dataset

def main():
    parser = argparse.ArgumentParser(description="Convert VTM to DPVTK")
    parser.add_argument("input_files", nargs='+', help="Input dataset path(s). The LAST argument is treated as the output .dpvtk file.")
    args = parser.parse_args()

    if len(args.input_files) < 2:
        print("Error: Must provide at least one input file and one output file.")
        sys.exit(1)

    output_file = args.input_files.pop()
    input_files = args.input_files

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()

    if rank == 0:
        print(f"[{rank}] Reading {len(input_files)} input files...")

    # Load dataset using OpenDataFile (auto-detects format)
    reader = pv.OpenDataFile(input_files)
    reader.UpdatePipeline()
    
    timesteps = reader.TimestepValues
    if not timesteps:
        timesteps = [0.0]

    if rank == 0:
        print(f"[{rank}] Found {len(timesteps)} timesteps.")

    # Open archive in replace mode to overwrite any existing file
    archive = pydpvz.DPvzVtk(output_file, pydpvz.DPvzMode.DPvzReplace, comm, False)
    
    for cycle, t in enumerate(timesteps):
        if rank == 0:
            print(f"[{rank}] Processing timestep {cycle} (time={t})...")
            
        reader.UpdatePipeline(time=t)
        
        # Fetch local rank data
        local_data = reader.GetClientSideObject().GetOutputDataObject(0)
        
        # Serialize to memory
        xml_string = serialize_multiblock_dataset(local_data, rank, cycle, t)
        
        # Write collective
        archive.write(cycle, t, xml_string)
        
    # Close is handled by C++ destructor
    
    if rank == 0:
        print(f"[{rank}] Successfully wrote {len(timesteps)} timesteps to {output_file}")

if __name__ == "__main__":
    main()
