#!/bin/bash
# Launch the Catalyst driver against the screenshot example script

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

# Auto-detect whether to use xvfb-run for dummy X server displays.
# DOCUMENTATION FOR HPC USERS: 
# On native HPC clusters where ParaView is explicitly built with OSMesa/EGL, 
# xvfb-run is completely unnecessary and can actually cause port collisions across 
# multi-node MPI jobs. This script will try to use it if available (useful for local 
# containers), but if xvfb is installed on your HPC and you need to bypass it, 
# simply set `export DISABLE_XVFB=1` before running.
if command -v xvfb-run &> /dev/null && [ -z "$DISABLE_XVFB" ]; then
    echo "running with xvfb-run (Virtual display detected for local headless rendering)"
    LAUNCH_CMD="xvfb-run mpiexec.mpich"
else
    echo "running without xvfb-run (Native HPC OSMesa/EGL bindings assumed)"
    LAUNCH_CMD="mpiexec.mpich"
fi

echo "Running Catalyst Driver to generate Screenshots..."
${LAUNCH_CMD} -np 4 ../paraview_v610/bin/pvbatch --mesa --force-offscreen-rendering --sym ../scripts/dpvtkcatalyst.py \
    --input can_vtpc.dpvtk \
    --script example_catalyst_screenshot_script.py \
    --channel input
