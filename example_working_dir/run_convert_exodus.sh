#!/bin/bash
# Convert 4-process Exodus can data into a DPVTK archive

# Source environment
source ../scripts/setup_env.sh

# Run the 4-process conversion from Exodus to DPVTK in symmetric MPI mode using mpiexec.mpich
mpiexec.mpich -np 4 ../paraview_v610/bin/pvbatch --sym ../scripts/dpvtkconvert.py \
    --input ../sample_data/can_data/can_data_4_process_exodus/can.ex2.4* \
    --output can_exodus.dpvtk
