import os
import subprocess
import pytest
import shutil
import glob

# Ensure we have a valid test file to work with
@pytest.fixture(scope="module")
def sample_dpvtk():
    out_file = "test_utils_can.dpvtk"
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    
    # Ensure it's generated
    cmd = [
        "mpiexec.mpich", "-np", "4",
        "./paraview_v610/bin/pvbatch", "--sym",
        "scripts/convertvtpcscript1.py",
        "sample_data/can_data/can_data_4_process_vtpc/can_vtpc_0.vtpc",
        out_file
    ]
    # We must source setup_env.sh in bash to get python paths correct, so we use bash -c
    bash_cmd = f"source scripts/setup_env.sh && {' '.join(cmd)}"
    subprocess.run(["bash", "-c", bash_cmd], cwd=root_dir, check=True)
    
    yield os.path.join(root_dir, out_file)
    
    # Teardown
    if os.path.exists(os.path.join(root_dir, out_file)):
        os.remove(os.path.join(root_dir, out_file))

def test_dpvtkextract(sample_dpvtk):
    root_dir = os.path.dirname(sample_dpvtk)
    out_prefix = "extracted_can"
    
    cmd = [
        "mpiexec.mpich", "-np", "4",
        "./paraview_v610/bin/pvbatch", "--sym", "--mesa",
        "scripts/dpvtkextract.py",
        sample_dpvtk,
        out_prefix
    ]
    bash_cmd = f"source scripts/setup_env.sh && {' '.join(cmd)}"
    subprocess.run(["bash", "-c", bash_cmd], cwd=root_dir, check=True)
    
    # Check if files were created
    vtm_files = glob.glob(os.path.join(root_dir, f"{out_prefix}_*.vtpc"))
    assert len(vtm_files) > 0, "No .vtpc files were extracted!"
    
    # Cleanup
    for f in vtm_files:
        os.remove(f)
        # Also remove associated directories
        d = f.replace(".vtpc", "")
        if os.path.exists(d) and os.path.isdir(d):
            shutil.rmtree(d)

def test_dpvtksplice_and_diff(sample_dpvtk):
    root_dir = os.path.dirname(sample_dpvtk)
    out_splice = "spliced_can.dpvtk"
    
    # Splice two copies of the same file
    cmd = [
        "mpiexec.mpich", "-np", "2",
        "python3", "scripts/dpvtksplice.py",
        out_splice, sample_dpvtk, sample_dpvtk
    ]
    bash_cmd = f"source scripts/setup_env.sh && {' '.join(cmd)}"
    subprocess.run(["bash", "-c", bash_cmd], cwd=root_dir, check=True)
    
    assert os.path.exists(os.path.join(root_dir, out_splice))
    
    # Now use dpvtkdiff to assert the original and spliced differ in steps
    diff_cmd = [
        "python3", "scripts/dpvtkdiff.py",
        sample_dpvtk, out_splice
    ]
    bash_diff_cmd = f"source scripts/setup_env.sh && {' '.join(diff_cmd)}"
    result = subprocess.run(["bash", "-c", bash_diff_cmd], cwd=root_dir)
    assert result.returncode != 0, "Diff should fail because spliced has double the steps"
    
    # Splice again to another file and ensure diff perfectly matches
    out_splice2 = "spliced_can2.dpvtk"
    cmd2 = [
        "mpiexec.mpich", "-np", "2",
        "python3", "scripts/dpvtksplice.py",
        out_splice2, sample_dpvtk, sample_dpvtk
    ]
    bash_cmd2 = f"source scripts/setup_env.sh && {' '.join(cmd2)}"
    subprocess.run(["bash", "-c", bash_cmd2], cwd=root_dir, check=True)
    
    diff_cmd2 = [
        "python3", "scripts/dpvtkdiff.py",
        out_splice, out_splice2
    ]
    bash_diff_cmd2 = f"source scripts/setup_env.sh && {' '.join(diff_cmd2)}"
    result2 = subprocess.run(["bash", "-c", bash_diff_cmd2], cwd=root_dir)
    assert result2.returncode == 0, "Diff should pass because both splices are identical"
    
    # Cleanup
    os.remove(os.path.join(root_dir, out_splice))
    os.remove(os.path.join(root_dir, out_splice2))

def test_dpvtkfilter(sample_dpvtk):
    root_dir = os.path.dirname(sample_dpvtk)
    out_filter = "filtered_can.dpvtk"
    
    cmd = [
        "mpiexec.mpich", "-np", "4",
        "./paraview_v610/bin/pvbatch", "--sym", "--mesa",
        "scripts/dpvtkfilter.py",
        sample_dpvtk, out_filter, "--filter", "slice"
    ]
    bash_cmd = f"source scripts/setup_env.sh && {' '.join(cmd)}"
    subprocess.run(["bash", "-c", bash_cmd], cwd=root_dir, check=True)
    
    assert os.path.exists(os.path.join(root_dir, out_filter))
    
    # Check that file size is smaller
    orig_size = os.path.getsize(sample_dpvtk)
    filt_size = os.path.getsize(os.path.join(root_dir, out_filter))
    assert filt_size < orig_size, "Filtered dataset should be smaller than original dataset"
    
    os.remove(os.path.join(root_dir, out_filter))

def test_dpvtkvideo(sample_dpvtk):
    root_dir = os.path.dirname(sample_dpvtk)
    out_mp4 = "test_vid.mp4"
    
    cmd = [
        "python3", "scripts/dpvtkvideo.py",
        sample_dpvtk, out_mp4, "--timesteprange", "[0,2]"
    ]
    bash_cmd = f"source scripts/setup_env.sh && {' '.join(cmd)}"
    subprocess.run(["bash", "-c", bash_cmd], cwd=root_dir, check=True)
    
    # Note: If ffmpeg is missing, out_mp4 might not be created.
    # The script should exit with 0 regardless.
    if shutil.which("ffmpeg"):
        assert os.path.exists(os.path.join(root_dir, out_mp4))
        os.remove(os.path.join(root_dir, out_mp4))

def test_dpvtkscreenshot_with_config(sample_dpvtk):
    root_dir = os.path.dirname(sample_dpvtk)
    out_png = "test_screenshot_config.png"
    config_file = "sample_render_config.json"
    
    cmd = [
        "mpiexec.mpich", "-np", "4",
        "./paraview_v610/bin/pvbatch", "--sym", "--mesa",
        "scripts/dpvtkscreenshot.py",
        sample_dpvtk, out_png, "--config", config_file
    ]
    bash_cmd = f"source scripts/setup_env.sh && {' '.join(cmd)}"
    subprocess.run(["bash", "-c", bash_cmd], cwd=root_dir, check=True)
    
    assert os.path.exists(os.path.join(root_dir, out_png))
    os.remove(os.path.join(root_dir, out_png))

def test_dpvtkprobe(sample_dpvtk):
    root_dir = os.path.dirname(sample_dpvtk)
    
    cmd = [
        "mpiexec.mpich", "-np", "4",
        "./paraview_v610/bin/pvbatch", "--sym", "scripts/dpvtkprobe.py",
        sample_dpvtk, "--timestep", "0"
    ]
    bash_cmd = f"source scripts/setup_env.sh && {' '.join(cmd)}"
    result = subprocess.run(["bash", "-c", bash_cmd], cwd=root_dir, check=True, capture_output=True, text=True)
    
    # Verify expected structure is in the standard output
    assert "--- DPvz Probe" in result.stdout
    assert "Point Data Arrays" in result.stdout
    assert "Cell Data Arrays" in result.stdout
    assert "Field Data Arrays" in result.stdout

