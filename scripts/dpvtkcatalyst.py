"""
ParaView symmetric MPI utility to act as a Catalyst V2 driver for a .dpvtk archive.

This script parses a user-provided Catalyst Python script, dynamically imports it,
and feeds it partitioned VTK data iteratively for each timestep in the archive. 
It uses a `TrivialProducer` to mock the Catalyst simulation input channel.

Execution Context:
Must be launched with `mpiexec -np N pvbatch --sym dpvtkcatalyst.py ...`
"""

import sys
import os
import argparse
import importlib.util
from mpi4py import MPI
import paraview.simple as paraview_simple
import pydpvz
from pydpvz.vtk_deserializer import populate_pdc_from_buffer
import vtk

class MockInfo:
    """Mocks the Catalyst V2 info object passed to catalyst_execute(info)."""
    def __init__(self, time, cycle):
        self.time = time
        self.cycle = cycle

def run_catalyst_driver(archive_path, script_path, channel_name):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    if not os.path.isfile(script_path):
        if rank == 0:
            print(f"Error: Script file '{script_path}' not found.")
        return
        
    if rank == 0:
        print(f"Loading user script: {script_path}")
        
    # Dynamically import the user's catalyst script
    spec = importlib.util.spec_from_file_location("user_catalyst_module", script_path)
    user_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(user_module)
    
    # 1. Catalyst Initialize
    if hasattr(user_module, "catalyst_initialize"):
        if rank == 0:
            print("Calling catalyst_initialize()...")
        user_module.catalyst_initialize()
        
    # 2. Setup the mock producer (must match the channel name expected by the script)
    # The registration name is key to how the Catalyst script will find it.
    producer = paraview_simple.TrivialProducer(registrationName=channel_name)
    
    # 3. Read archive map
    archive = pydpvz.DPvzVtk(archive_path, pydpvz.DPvzMode.DPvzReadOnly, comm, False)
    steps = archive.get_steps()
    
    if steps == 0:
        if rank == 0:
            print("Archive contains no timesteps.")
        return
        
    map_vec = archive.get_map()
    
    # 4. Loop over all timesteps
    for timestep in range(steps):
        entry = map_vec[timestep]
        step_toc = archive.get_step_toc(entry)
        
        if rank == 0:
            print(f"Processing Timestep {timestep} (Cycle {entry.cycle}, Time {entry.time})...")
            
        # Reconstruct the distributed VTK dataset for this timestep
        pdc = vtk.vtkPartitionedDataSetCollection()
        part_counters = {}
        
        for w_rank in range(rank, entry.ranks, size):
            rank_entry = step_toc[w_rank]
            buffer_bytes = archive.get_data(rank_entry)
            populate_pdc_from_buffer(pdc, buffer_bytes, part_counters)
            
        if rank == 0:
            print("  -> Setting dataset output to TrivialProducer...")
        # Update the pipeline source with the newly loaded data
        producer.GetClientSideObject().SetOutput(pdc)
        
        if rank == 0:
            print("  -> Marking producer as modified...")
        producer.MarkModified(producer)
        
        if rank == 0:
            print("  -> Updating pipeline time...")
        producer.UpdatePipeline(entry.time)
        
        # 5. Catalyst Execute
        if hasattr(user_module, "catalyst_execute"):
            if rank == 0:
                print("  -> Entering user catalyst_execute...")
            info = MockInfo(time=entry.time, cycle=entry.cycle)
            user_module.catalyst_execute(info)
            if rank == 0:
                print("  -> Exited user catalyst_execute.")
            
    # 6. Catalyst Finalize
    if hasattr(user_module, "catalyst_finalize"):
        if rank == 0:
            print("Calling catalyst_finalize()...")
        user_module.catalyst_finalize()
        
    if rank == 0:
        print("Catalyst driver execution complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ParaView Catalyst V2 Mock Driver")
    parser.add_argument("--input", required=True, help="Input .dpvtk dataset file")
    parser.add_argument("--script", required=True, help="User Catalyst python script to execute")
    parser.add_argument("--channel", default="input", help="Data channel name (defaults to 'input')")
    
    args, unknown = parser.parse_known_args()
    
    run_catalyst_driver(args.input, args.script, args.channel)
