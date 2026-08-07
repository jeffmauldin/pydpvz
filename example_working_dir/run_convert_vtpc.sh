#!/bin/bash
# Convert 4-rank VTPC can data into a DPVTK archive

# Source environment
source ../scripts/setup_env.sh

# Run the 4-process conversion from VTPC to DPVTK in symmetric MPI mode using mpiexec.mpich
mpiexec.mpich -np 4 ../paraview_v610/bin/pvbatch --sym ../scripts/dpvtkconvert.py \
    --input ../sample_data/can_data/can_data_4_process_vtpc/can_vtpc_*.vtpc \
    --output can_vtpc.dpvtk
