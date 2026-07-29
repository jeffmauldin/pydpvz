#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import glob

def get_mpi_info(pvbatch_path):
    if not os.path.exists(pvbatch_path):
        print(f"Error: Executable not found at {pvbatch_path}")
        sys.exit(1)
        
    def check_ldd(path):
        try:
            output = subprocess.check_output(['ldd', path], text=True, stderr=subprocess.STDOUT)
            for line in output.splitlines():
                if 'mpi' in line.lower() and '=>' in line:
                    parts = line.split('=>')
                    if len(parts) == 2:
                        path_part = parts[1].strip().split(' ')[0]
                        if path_part and path_part != 'not':
                            return path_part
        except subprocess.CalledProcessError:
            pass
        return None

    mpi_lib_path = check_ldd(pvbatch_path)
    
    # If not found directly on pvbatch, try ParaView's libvtkParallelMPI library
    if not mpi_lib_path:
        bin_dir = os.path.dirname(os.path.abspath(pvbatch_path))
        lib_dir = os.path.join(os.path.dirname(bin_dir), 'lib')
        if os.path.exists(lib_dir):
            for so_path in glob.glob(os.path.join(lib_dir, 'libvtkParallelMPI-*.so*')):
                mpi_lib_path = check_ldd(so_path)
                if mpi_lib_path:
                    break
                    
    if not mpi_lib_path:
        print("Could not detect any linked MPI library.")
        sys.exit(1)
        
    flavor = "Unknown"
    lower_path = mpi_lib_path.lower()
    
    if 'mpich' in lower_path or 'libmpi.so.12' in lower_path:
        flavor = "MPICH"
    elif 'openmpi' in lower_path or 'libmpi.so.40' in lower_path:
        flavor = "OpenMPI"
    elif 'intel' in lower_path:
        flavor = "Intel MPI"
        
    # Determine prefix path
    prefix_path = os.path.dirname(os.path.dirname(os.path.abspath(mpi_lib_path)))
    
    print("=================================================")
    print(" MPI Environment Inspector")
    print("=================================================")
    print(f"Target Executable: {pvbatch_path}")
    print(f"Detected MPI Flavor: {flavor}")
    print(f"MPI Library Path:  {mpi_lib_path}")
    print(f"Recommended CMAKE_PREFIX_PATH: {prefix_path}")
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
    print("--------------------------------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect a pvbatch executable to determine its linked MPI environment.")
    parser.add_argument("pvbatch_path", help="Path to the pvbatch executable")
    args = parser.parse_args()
    get_mpi_info(args.pvbatch_path)
