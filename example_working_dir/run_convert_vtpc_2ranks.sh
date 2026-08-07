#!/bin/bash
# Convert 4-rank VTPC can data into a DPVTK archive using only 2 MPI ranks

# Source environment
source ../scripts/setup_env.sh

# Run the conversion from VTPC to DPVTK in symmetric MPI mode using 2 processes
mpiexec.mpich -np 2 ../paraview_v610/bin/pvbatch --sym ../scripts/dpvtkconvert.py \
    --input ../sample_data/can_data/can_data_4_process_vtpc/can_vtpc_*.vtpc \
    --output can_vtpc_2ranks.dpvtk
