"""
Utility script to recursively compare the metadata and payload sizes of two .dpvtk archives.

This tool validates the structural integrity of a conversion by comparing the number of timesteps, 
rank participation, and both deflated/inflated bytes for every single MPI partition inside the archive.

Execution Context:
Can be run serially with standard Python or in parallel via mpiexec.
"""

import argparse
import sys
import pydpvz
from mpi4py import MPI

def diff_dpvtk(file1, file2):
    """
    Compares two .dpvtk archives for equivalence in timesteps and block payloads.
    
    Args:
        file1 (str): Path to the first .dpvtk file.
        file2 (str): Path to the second .dpvtk file.
        
    Returns:
        bool: True if perfectly matched, False otherwise.
    """
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    
    if rank == 0:
        print(f"Comparing {file1} and {file2}...")
        
    try:
        archive1 = pydpvz.DPvzVtk(file1, pydpvz.DPvzMode.DPvzReadOnly, comm, False)
        archive2 = pydpvz.DPvzVtk(file2, pydpvz.DPvzMode.DPvzReadOnly, comm, False)
    except Exception as e:
        if rank == 0:
            print(f"Error opening files: {e}")
        return False
        
    steps1 = archive1.get_steps()
    steps2 = archive2.get_steps()
    
    if steps1 != steps2:
        if rank == 0:
            print(f"DIFFERENCE: {file1} has {steps1} steps, but {file2} has {steps2} steps.")
        return False
        
    if rank == 0:
        print(f"Both archives have {steps1} timesteps. Comparing metadata and payloads...")
        
    map1 = archive1.get_map()
    map2 = archive2.get_map()
    
    match = True
    
    for t in range(steps1):
        entry1 = map1[t]
        entry2 = map2[t]
        
        if entry1.time != entry2.time:
            if rank == 0:
                print(f"DIFFERENCE at step {t}: Time values differ ({entry1.time} vs {entry2.time})")
            match = False
            
        if entry1.ranks != entry2.ranks:
            if rank == 0:
                print(f"DIFFERENCE at step {t}: Rank counts differ ({entry1.ranks} vs {entry2.ranks})")
            match = False
            continue
            
        toc1 = archive1.get_step_toc(entry1)
        toc2 = archive2.get_step_toc(entry2)
        
        for r in range(entry1.ranks):
            rtoc1 = toc1[r]
            rtoc2 = toc2[r]
            
            if rtoc1.deflated_size != rtoc2.deflated_size:
                if rank == 0:
                    print(f"DIFFERENCE at step {t}, rank {r}: deflated_size differs ({rtoc1.deflated_size} vs {rtoc2.deflated_size})")
                match = False
                
            if rtoc1.inflated_size != rtoc2.inflated_size:
                if rank == 0:
                    print(f"DIFFERENCE at step {t}, rank {r}: inflated_size differs ({rtoc1.inflated_size} vs {rtoc2.inflated_size})")
                match = False
                
    if match and rank == 0:
        print("SUCCESS: The metadata and compressed payload sizes perfectly match!")
        
    return match

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare two .dpvtk files.")
    parser.add_argument("file1", help="First .dpvtk file")
    parser.add_argument("file2", help="Second .dpvtk file")

    args = parser.parse_args()
    success = diff_dpvtk(args.file1, args.file2)
    sys.exit(0 if success else 1)
