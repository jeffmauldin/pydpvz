#!/bin/bash
# Launch the Catalyst driver against the slice example script

# Source environment
source ../scripts/setup_env.sh

# Ensure that can_vtpc.dpvtk exists first
if [ ! -f "can_vtpc.dpvtk" ]; then
    echo "can_vtpc.dpvtk not found. Please run ./run_convert_vtpc.sh first."
    exit 1
fi

# Set environment variables to enforce CPU software off-screen rendering
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe

echo "Running Catalyst Driver with Slice Filter..."
mpiexec.mpich -np 4 ../paraview_v610/bin/pvbatch --mesa --force-offscreen-rendering --sym ../scripts/dpvtkcatalyst.py \
    --input can_vtpc.dpvtk \
    --script example_catalyst_slice_script.py \
    --channel input
