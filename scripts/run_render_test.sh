#!/bin/bash

# Ensure we are in the workspace root
cd /workspaces/AllVibesDemo

# Setup the environment correctly
# 1. PYTHONPATH must include our custom pydpvz module so Python can import it
export PYTHONPATH="$(pwd)/pydpvz:$PYTHONPATH"

# 2. LD_LIBRARY_PATH must include both the custom DPvz MPI C++ library and ParaView's libraries
export LD_LIBRARY_PATH="$(pwd)/dpvz/src:$(pwd)/paraview_v610/lib:$LD_LIBRARY_PATH"

# 3. PATH should include the ParaView bin directory for convenience
export PATH="$(pwd)/paraview_v610/bin:$PATH"

# Define inputs and outputs
INPUT_ARCHIVE="output_can_vtpc.dpvtk"
OUTPUT_PNG="can_render.png"

# Check if input exists
if [ ! -f "$INPUT_ARCHIVE" ]; then
    echo "Error: Input archive $INPUT_ARCHIVE not found. Run conversion scripts first."
    exit 1
fi

echo "Environment Setup Complete:"
echo "PYTHONPATH: $PYTHONPATH"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
echo "PATH: $PATH"
echo "--------------------------------------------------"
echo "Launching parallel rendering across 4 processes..."

# Execute pvbatch in symmetric mode using the specific MPICH binary with --mesa
mpiexec.mpich -np 4 pvbatch --sym --mesa scripts/renderdpvtk.py "$INPUT_ARCHIVE" "$OUTPUT_PNG"

echo "--------------------------------------------------"
if [ -f "$OUTPUT_PNG" ]; then
    echo "Rendering completed successfully! Saved to $OUTPUT_PNG"
else
    echo "Error: Failed to generate $OUTPUT_PNG"
fi
