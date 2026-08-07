#!/bin/bash
# Extract the generated DPVTK archives back out into partitioned VTK files (.vtpc)

# Source environment
source ../scripts/setup_env.sh

echo "Extracting can_vtpc.dpvtk..."
mpiexec.mpich -np 4 ../paraview_v610/bin/pvbatch --sym ../scripts/dpvtkextract.py can_vtpc.dpvtk extracted_can_vtpc

echo "Extracting can_exodus.dpvtk..."
mpiexec.mpich -np 4 ../paraview_v610/bin/pvbatch --sym ../scripts/dpvtkextract.py can_exodus.dpvtk extracted_can_exodus
