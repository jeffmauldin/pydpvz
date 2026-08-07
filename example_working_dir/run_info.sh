#!/bin/bash
# Print metadata information for the DPVTK archives without loading bulk payload data

# Source environment
source ../scripts/setup_env.sh

echo "Info for can_vtpc.dpvtk:"
../paraview_v610/bin/pvbatch ../scripts/dpvtkinfo.py can_vtpc.dpvtk

echo ""
echo "Info for can_exodus.dpvtk:"
../paraview_v610/bin/pvbatch ../scripts/dpvtkinfo.py can_exodus.dpvtk
