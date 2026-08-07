#!/bin/bash
# Convert 4-rank VTPC can data into a DPVTK archive using only 1 process (no MPI needed)

# Source environment
source ../scripts/setup_env.sh

# Run the conversion serially using pvbatch without MPI
../paraview_v610/bin/pvbatch ../scripts/dpvtkconvert.py \
    --input ../sample_data/can_data/can_data_4_process_vtpc/can_vtpc_*.vtpc \
    --output can_vtpc_1rank.dpvtk
