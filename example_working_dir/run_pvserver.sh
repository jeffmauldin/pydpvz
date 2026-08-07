#!/bin/bash
# Launch pvserver in parallel across 4 MPI processes with Mesa off-screen rendering enabled

# Source environment
source ../scripts/setup_env.sh

# Set environment variables to enforce CPU software off-screen rendering via Mesa/LLVMpipe
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe

# Launch pvserver
# Note: You can connect to this server from an external ParaView GUI using localhost:11111
mpiexec.mpich -np 4 ../paraview_v610/bin/pvserver --mesa --force-offscreen-rendering --bind-address 0.0.0.0 --server-port 11111
