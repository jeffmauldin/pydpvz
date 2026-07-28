import subprocess
import os
import pytest
import glob
import pydpvz
from mpi4py import MPI

def test_convert_can_vtm():
    env = os.environ.copy()
    env["PYTHONPATH"] = f"/workspaces/AllVibesDemo/pydpvz:{env.get('PYTHONPATH', '')}"
    
    input_files = glob.glob("sample_data/can_data/can_data_4_process_vtkm/can_vtkm_*.vtm")
    input_files.sort()
    
    cmd = [
        "mpiexec.mpich", "-np", "4", 
        "./paraview_v610/bin/pvbatch", "--sym", 
        "scripts/convertvtmscript1.py"
    ] + input_files + [
        "output_can_vtm.dpvtk"
    ]
    
    result = subprocess.run(cmd, env=env, cwd="/workspaces/AllVibesDemo", capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0
    
    archive = pydpvz.DPvzVtk("output_can_vtm.dpvtk", pydpvz.DPvzMode.DPvzReadOnly, MPI.COMM_WORLD, False)
    assert archive.get_steps() == 44

def test_convert_rigid_vtm():
    env = os.environ.copy()
    env["PYTHONPATH"] = f"/workspaces/AllVibesDemo/pydpvz:{env.get('PYTHONPATH', '')}"
    
    input_files = glob.glob("sample_data/rigid_body_data/rigid_body_vtm/rigid_body_test_volume_vtm_*.vtm")
    input_files.sort()
    
    cmd = [
        "mpiexec.mpich", "-np", "4", 
        "./paraview_v610/bin/pvbatch", "--sym", 
        "scripts/convertvtmscript1.py"
    ] + input_files + [
        "output_rigid_vtm.dpvtk"
    ]
    
    result = subprocess.run(cmd, env=env, cwd="/workspaces/AllVibesDemo", capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0
    
    archive = pydpvz.DPvzVtk("output_rigid_vtm.dpvtk", pydpvz.DPvzMode.DPvzReadOnly, MPI.COMM_WORLD, False)
    assert archive.get_steps() > 1
