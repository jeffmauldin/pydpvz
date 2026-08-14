#!/bin/bash
# setup_offscreen_env.sh
# Sets up the environment variables for pydpvz and ParaView with off-screen OSMesa rendering

# Dynamically resolve the workspace directory
WORKSPACE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

# Source the base environment
source "${WORKSPACE_DIR}/scripts/setup_env.sh"

# Set environment variables to enforce CPU software off-screen rendering
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe

# Force VTK to use OSMesa for off-screen rendering (resolves EGL/X11 errors)
export VTK_DEFAULT_OPENGL_WINDOW=vtkOSOpenGLRenderWindow

echo "Off-screen rendering environment variables set."
