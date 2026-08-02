#!/usr/bin/env python3
"""
Diagnostic utility to dynamically detect the MPI and Python ABI environments linked to a ParaView binary.

In High Performance Computing contexts, attempting to link `pydpvz` or launch `pvbatch`
with a mismatched MPI ABI (e.g., OpenMPI vs MPICH) or a mismatched Python ABI 
(e.g., Python 3.12 vs 3.13) will cause silent deadlocks or segfaults.
This script inspects `pvbatch` and its libraries to output a Spack `packages.yaml` 
snippet to force matching external dependencies during build.
"""

import argparse
import subprocess
import sys
import os
import glob
import re

def get_env_info(pvbatch_path):
    """
    Inspects an executable to detect its dynamically linked MPI flavor and Python ABI.
    """
    if not os.path.exists(pvbatch_path):
        print(f"Error: Executable not found at {pvbatch_path}")
        sys.exit(1)
        
    bin_dir = os.path.dirname(os.path.abspath(pvbatch_path))
    lib_dir = os.path.join(os.path.dirname(bin_dir), 'lib')
        
    def check_ldd(path, target_string):
        try:
            output = subprocess.check_output(['ldd', path], text=True, stderr=subprocess.STDOUT)
            for line in output.splitlines():
                if target_string in line.lower() and '=>' in line:
                    parts = line.split('=>')
                    if len(parts) == 2:
                        path_part = parts[1].strip().split(' ')[0]
                        if path_part and path_part != 'not':
                            return path_part
        except subprocess.CalledProcessError:
            pass
        return None

    # 1. Detect MPI
    mpi_lib_path = check_ldd(pvbatch_path, 'mpi')
    if not mpi_lib_path and os.path.exists(lib_dir):
        for so_path in glob.glob(os.path.join(lib_dir, 'libvtkParallelMPI-*.so*')):
            mpi_lib_path = check_ldd(so_path, 'mpi')
            if mpi_lib_path:
                break
                
    flavor = "Unknown"
    prefix_path = "Unknown"
    if mpi_lib_path:
        lower_path = mpi_lib_path.lower()
        if 'mpich' in lower_path or 'libmpi.so.12' in lower_path:
            flavor = "MPICH"
        elif 'openmpi' in lower_path or 'libmpi.so.40' in lower_path:
            flavor = "OpenMPI"
        elif 'intel' in lower_path:
            flavor = "Intel MPI"
        prefix_path = os.path.dirname(os.path.dirname(os.path.abspath(mpi_lib_path)))

    # 2. Detect Python ABI
    python_abi = "Unknown"
    # Primary method: Direct Interpreter Inquiry
    try:
        py_out = subprocess.check_output([pvbatch_path, '-c', 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'], text=True, stderr=subprocess.STDOUT)
        if py_out.strip():
            python_abi = py_out.strip().splitlines()[-1].strip()
    except Exception:
        pass
        
    # Fallback method: Inspect libvtkWrappingPythonCore
    if python_abi == "Unknown" and os.path.exists(lib_dir):
        for so_path in glob.glob(os.path.join(lib_dir, 'libvtkWrappingPythonCore*-*.so*')):
            basename = os.path.basename(so_path)
            match = re.search(r'libvtkWrappingPythonCore(\d+\.\d+)', basename)
            if match:
                python_abi = match.group(1)
                break

    print("=================================================")
    print(" ParaView Environment Inspector")
    print("=================================================")
    print(f"Target Executable : {pvbatch_path}")
    print(f"Detected MPI      : {flavor}")
    if mpi_lib_path:
        print(f"MPI Library Path  : {mpi_lib_path}")
        print(f"Recommended Prefix: {prefix_path}")
    print(f"Target Python ABI : {python_abi}")
    print("=================================================")

    # Determine Spack package name
    spack_pkg = "mpi"
    if flavor == "MPICH":
        spack_pkg = "mpich"
    elif flavor == "OpenMPI":
        spack_pkg = "openmpi"
    elif flavor == "Intel MPI":
        spack_pkg = "intel-mpi"

    print("\n--- Spack External Package Snippet ---")
    print("  packages:")
    print(f"    {spack_pkg}:")
    print("      buildable: false")
    print("      externals:")
    print(f"      - spec: {spack_pkg}")
    print(f"        prefix: {prefix_path}")
    
    if python_abi != "Unknown":
        print(f"    python:")
        print("      buildable: false")
        print("      externals:")
        print(f"      - spec: python@{python_abi}")
        # In a real cluster we might use `which python3` or similar for the prefix, 
        # but specifying the explicit version constraint is the critical part for ABI matching.
    print("--------------------------------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect a pvbatch executable to determine its linked MPI and Python ABI environment.")
    parser.add_argument("pvbatch_path", help="Path to the pvbatch executable")
    args = parser.parse_args()
    get_env_info(args.pvbatch_path)
