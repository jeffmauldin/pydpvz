#!/bin/bash
# Probe the generated DPVTK archives (Timestep 0) for array variables and per-rank cell/point geometry counts

# Source environment
source ../scripts/setup_env.sh

echo "Probing can_vtpc.dpvtk:"
mpiexec.mpich -np 4 ../paraview_v610/bin/pvbatch --sym ../scripts/dpvtkprobe.py can_vtpc.dpvtk 0

echo ""
echo "Probing can_exodus.dpvtk:"
mpiexec.mpich -np 4 ../paraview_v610/bin/pvbatch --sym ../scripts/dpvtkprobe.py can_exodus.dpvtk 0
