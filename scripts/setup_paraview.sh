#!/bin/bash
set -e

# Dynamically resolve the workspace directory
WORKSPACE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

DEST_DIR="${WORKSPACE_DIR}/paraview_v610"
ARCHIVE_PATH="${WORKSPACE_DIR}/paraview_6.1.0.tar.gz"

echo "================================================="
echo " Setting up ParaView 6.1.0 (MPI + Python 3.12) "
echo "================================================="

# Helper function to detect MPI version
detect_mpi() {
    echo "================================================="
    echo "[!] Checking ParaView's embedded MPI version..."
    echo "[!] This will tell you which MPI wrapper (e.g., mpicxx.mpich or mpicxx.openmpi)"
    echo "[!] you MUST use when building the dpvz C++ library and pydpvz."
    ldd "$DEST_DIR/bin/pvbatch" | grep -i mpi || echo "Could not detect MPI library automatically."
    echo "================================================="
}

if [ -f "$DEST_DIR/bin/pvpython" ] && [ -f "$DEST_DIR/bin/pvbatch" ]; then
    echo "[+] ParaView 6.1.0 is already installed and verified at: $DEST_DIR"
    detect_mpi
    exit 0
fi

if [ ! -f "$ARCHIVE_PATH" ]; then
    echo "[!] Error: Cached archive $ARCHIVE_PATH not found."
    echo "[!] Please download the ParaView 6.1.0 MPI-enabled tarball from paraview.org"
    echo "[!] (e.g., ParaView-5.11.0-MPI-Linux-Python3.9-x86_64.tar.gz) and place it in the root directory"
    echo "[!] as 'paraview_6.1.0.tar.gz', then run this script again."
    exit 1
fi

echo "[+] Extracting ParaView archive into $DEST_DIR..."
mkdir -p "$DEST_DIR"
tar -xzmf "$ARCHIVE_PATH" -C "$DEST_DIR" --strip-components=1

echo "[+] Extraction complete!"
detect_mpi
