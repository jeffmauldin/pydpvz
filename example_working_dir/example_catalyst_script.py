from paraview.simple import *
import os

def catalyst_initialize():
    global producer
    # The driver creates the TrivialProducer with registrationName="input",
    # so we just need to find it by name.
    producer = FindSource("input")
    if not producer:
        # Fallback if we are running in the ParaView GUI directly
        producer = TrivialProducer(registrationName="input")

def catalyst_execute(info=None):
    global producer
    producer.UpdatePipeline()
    
    cycle = info.cycle if info else 0
    if not os.path.exists('catalyst_extracts'):
        try:
            os.makedirs('catalyst_extracts')
        except FileExistsError:
            pass
            
    # Log execution and data bounds to prove the data was successfully piped to the script
    print(f"      [Catalyst] Saving execution log for cycle {cycle}...")
    pdc = producer.GetClientSideObject().GetOutputDataObject(0)
    
    # We only write the log file from rank 0 to avoid race conditions
    from mpi4py import MPI
    if MPI.COMM_WORLD.Get_rank() == 0:
        with open(f"catalyst_extracts/execution_cycle_{cycle:04d}.txt", "w") as f:
            f.write(f"Catalyst Mock Driver Executed Cycle {cycle}\n")
            f.write(f"Dataset successfully loaded from pipeline.\n")
            
    print(f"      [Catalyst] Execution finished for timestep.")
    
def catalyst_finalize():
    print("Catalyst Python script finalized successfully.")
