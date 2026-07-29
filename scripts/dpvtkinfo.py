"""
Utility script to inspect .dpvtk archive metadata without loading bulk payload data.

This operates nearly instantaneously by reading only the header and table of contents.
It reports the number of timesteps, rank participation per step, and the exact 
deflated/inflated byte sizes of every MPI partition.

Execution Context:
Typically run serially via standard `python3 dpvtkinfo.py ...`, though it is MPI-safe.
"""

import sys
import argparse
from mpi4py import MPI
import pydpvz

def report_metadata(filename, terse=False):
    """
    Parses and prints the table of contents of a .dpvtk archive.
    
    Args:
        filename (str): The input .dpvtk file.
        terse (bool): If True, suppresses detailed partition-by-partition byte sizes.
    """
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    
    # Only rank 0 should print output to avoid duplicated lines
    if rank != 0:
        return

    try:
        # Load only the metadata (headers and table of contents).
        # This operates very fast and bypasses any bulk data loading.
        archive = pydpvz.DPvzVtk(filename, pydpvz.DPvzMode.DPvzReadOnly, comm, False)
    except Exception as e:
        print(f"Error opening {filename}: {e}")
        return

    steps = archive.get_steps()
    print(f"File: {filename}")
    print(f"Total timesteps: {steps}")
    
    if steps == 0:
        return

    map_vec = archive.get_map()
    print(f"\n{'Step':<6} | {'Cycle':<8} | {'Time':<12} | {'Participating Ranks':<20}")
    print("-" * 55)
    for i, entry in enumerate(map_vec):
        print(f"{i:<6} | {entry.cycle:<8} | {entry.time:<12.6g} | {entry.ranks:<20}")

    if not terse:
        print("\n=== Rank Data Size Details ===")
        for i, entry in enumerate(map_vec):
            print(f"\nStep {i} (Cycle {entry.cycle}, Time {entry.time}):")
            print(f"{'Rank':<6} | {'Compressed (Bytes)':<20} | {'Uncompressed (Bytes)':<20}")
            print("-" * 55)
            step_toc = archive.get_step_toc(entry)
            for r, rank_info in enumerate(step_toc):
                print(f"{r:<6} | {rank_info.deflated_size:<20} | {rank_info.inflated_size:<20}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Report metadata of a .dpvtk file without loading bulk data.")
    parser.add_argument("input", help="Input .dpvtk file path")
    parser.add_argument("--terse", action="store_true", help="Skip detailed rank size output")
    args = parser.parse_args()
    report_metadata(args.input, args.terse)

