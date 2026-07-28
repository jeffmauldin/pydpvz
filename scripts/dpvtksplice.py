import argparse
import sys
from mpi4py import MPI
import pydpvz

def splice_dpvtk(input_files, output_file):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    if rank == 0:
        print(f"Creating spliced output archive {output_file}...")
        
    out_archive = pydpvz.DPvzVtk(output_file, pydpvz.DPvzMode.DPvzReplace, comm, False)
    
    global_cycle = 0
    
    for in_file in input_files:
        if rank == 0:
            print(f"Splicing input archive {in_file}...")
            
        in_archive = pydpvz.DPvzVtk(in_file, pydpvz.DPvzMode.DPvzReadOnly, comm, False)
        steps = in_archive.get_steps()
        
        if steps == 0:
            if rank == 0:
                print(f"Archive {in_file} contains no timesteps, skipping.")
            continue
            
        map_vec = in_archive.get_map()
        
        for t in range(steps):
            entry = map_vec[t]
            step_toc = in_archive.get_step_toc(entry)
            
            buffer_bytes = b""
            if rank < entry.ranks:
                rank_entry = step_toc[rank]
                buffer_bytes = in_archive.get_data(rank_entry)
            
            # Write raw buffer directly into the new archive
            time_val = entry.time
            out_archive.write(global_cycle, time_val, buffer_bytes)
            global_cycle += 1
            
        # We must explicitly clean up the input archive before opening the next
        del in_archive

    if rank == 0:
        print(f"Successfully spliced {len(input_files)} files into {output_file} (Total timesteps: {global_cycle})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Splice multiple .dpvtk files together into a single archive.")
    parser.add_argument("output", help="Output .dpvtk file")
    parser.add_argument("inputs", nargs='+', help="Input .dpvtk files to merge in order")

    args, unknown = parser.parse_known_args()
    splice_dpvtk(args.inputs, args.output)
