import subprocess
import os
import pytest
import glob
import pydpvz
from mpi4py import MPI

def test_convert_can_exodus():
    env = os.environ.copy()
    env["PYTHONPATH"] = f"/workspaces/AllVibesDemo/pydpvz:{env.get('PYTHONPATH', '')}"
    
    cmd = [
        "mpiexec.mpich", "-np", "4", 
        "./paraview_v610/bin/pvbatch", "--sym", 
        "scripts/convertvtpcscript1.py", 
        "sample_data/can_data/can_data_4_process_exodus/can.ex2.4.0", 
        "output_can_ex.dpvtk"
    ]
    
    result = subprocess.run(cmd, env=env, cwd="/workspaces/AllVibesDemo", capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0
    
    # Verify archive has multiple timesteps using pydpvz directly
    archive = pydpvz.DPvzVtk("output_can_ex.dpvtk", pydpvz.DPvzMode.DPvzReadOnly, MPI.COMM_WORLD, False)
    assert archive.get_steps() == 44

def test_convert_can_vtpc():
    env = os.environ.copy()
    env["PYTHONPATH"] = f"/workspaces/AllVibesDemo/pydpvz:{env.get('PYTHONPATH', '')}"
    
    input_files = glob.glob("sample_data/can_data/can_data_4_process_vtpc/can_vtpc_*.vtpc")
    input_files.sort()
    
    cmd = [
        "mpiexec.mpich", "-np", "4", 
        "./paraview_v610/bin/pvbatch", "--sym", 
        "scripts/convertvtpcscript1.py"
    ] + input_files + [
        "output_can_vtpc.dpvtk"
    ]
    
    result = subprocess.run(cmd, env=env, cwd="/workspaces/AllVibesDemo", capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0
    
    archive = pydpvz.DPvzVtk("output_can_vtpc.dpvtk", pydpvz.DPvzMode.DPvzReadOnly, MPI.COMM_WORLD, False)
    assert archive.get_steps() == 44

def test_convert_hifire_vtpc():
    env = os.environ.copy()
    env["PYTHONPATH"] = f"/workspaces/AllVibesDemo/pydpvz:{env.get('PYTHONPATH', '')}"
    
    cmd = [
        "mpiexec.mpich", "-np", "4", 
        "./paraview_v610/bin/pvbatch", "--sym", 
        "scripts/convertvtpcscript1.py", 
        "sample_data/hifire_example_data/hifire_volume_0001.vtpc", 
        "output_hifire.dpvtk"
    ]
    
    result = subprocess.run(cmd, env=env, cwd="/workspaces/AllVibesDemo", capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0
    
    archive = pydpvz.DPvzVtk("output_hifire.dpvtk", pydpvz.DPvzMode.DPvzReadOnly, MPI.COMM_WORLD, False)
    assert archive.get_steps() == 1
