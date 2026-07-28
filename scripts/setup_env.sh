#!/bin/bash
# setup_env.sh
# Sets up the environment variables for pydpvz and ParaView

# Dynamically resolve the workspace directory
WORKSPACE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

# ParaView installation directory (adjust if yours is installed elsewhere)
PARAVIEW_DIR="${WORKSPACE_DIR}/paraview_v610"

export PYTHONPATH="${WORKSPACE_DIR}/pydpvz:$PYTHONPATH"
export LD_LIBRARY_PATH="${WORKSPACE_DIR}/dpvz/src:${PARAVIEW_DIR}/lib:$LD_LIBRARY_PATH"

echo "Environment configured for pydpvz and dpvz."
echo "ParaView Library Path: ${PARAVIEW_DIR}/lib"
