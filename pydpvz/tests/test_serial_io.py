"""
test_serial_io.py  –  Phase 3 Task 3.1
Serial unit tests for pydpvz DPvzFile / DPvzVtk using a single MPI rank.

Run with:
    cd /tmp && pytest /workspaces/AllVibesDemo/pydpvz/tests/test_serial_io.py -v
"""

import os
import tempfile
import pytest

# mpi4py MUST be imported before pydpvz so that MPI_Init() is called
# before the dpvz C++ library makes any MPI calls at module load time.
from mpi4py import MPI as _MPI   # noqa: F401  (initializes MPI)

import pydpvz
from pydpvz import DPvzMode, DPvzFile, DPvzVtk, DPvzTocEntry, DPvzRankToc


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

PAYLOAD_1 = b"Hello from cycle 0, rank 0"
PAYLOAD_2 = b"<VTKFile>some xml data cycle 1</VTKFile>"
PAYLOAD_3 = b"Step 2 data buffer, longer content for testing truncation"


def make_vtk_path(tmp_path, name="test_archive"):
    """Return a .dpvtk path inside a pytest tmp_path that does not yet exist."""
    return str(tmp_path / f"{name}.dpvtk")


# ---------------------------------------------------------------------------
# Task 3.1.A  –  File creation modes
# ---------------------------------------------------------------------------

class TestCreationModes:

    def test_create_new_file(self, tmp_path):
        """DPvzCreate opens / creates a new file without error."""
        path = make_vtk_path(tmp_path, "create_new")
        f = DPvzVtk(path, DPvzMode.DPvzCreate)
        assert not f.failed(), "DPvzCreate should succeed on a new file"
        assert f.get_steps() == 0, "Newly created file should have 0 steps"
        print(f"\n  [CREATE] {path}: 0 steps, page_size={f.get_page_size()}")

    def test_replace_existing_file(self, tmp_path):
        """DPvzReplace truncates a file that already exists."""
        path = make_vtk_path(tmp_path, "replace_me")
        # First create and write one step
        f1 = DPvzVtk(path, DPvzMode.DPvzCreate)
        f1.write(0, 0.0, PAYLOAD_1)
        assert f1.get_steps() == 1
        del f1

        # Now replace – should start fresh
        f2 = DPvzVtk(path, DPvzMode.DPvzReplace)
        assert not f2.failed(), "DPvzReplace should succeed on existing file"
        assert f2.get_steps() == 0, "DPvzReplace should reset step count to 0"
        print(f"\n  [REPLACE] {path}: steps after replace = {f2.get_steps()}")

    def test_readwrite_mode_opens_existing(self, tmp_path):
        """DPvzReadWrite opens an existing file and allows writes."""
        path = make_vtk_path(tmp_path, "rw_existing")
        f1 = DPvzVtk(path, DPvzMode.DPvzCreate)
        f1.write(10, 1.0, PAYLOAD_1)
        del f1

        f2 = DPvzVtk(path, DPvzMode.DPvzReadWrite)
        assert not f2.failed(), "DPvzReadWrite should open existing file"
        assert f2.get_steps() == 1
        f2.write(20, 2.0, PAYLOAD_2)
        assert f2.get_steps() == 2
        print(f"\n  [RW] {path}: steps after append = {f2.get_steps()}")


# ---------------------------------------------------------------------------
# Task 3.1.B  –  Serial write and readback (get_data)
# ---------------------------------------------------------------------------

class TestWriteAndRead:

    def _create_3step_file(self, tmp_path):
        path = make_vtk_path(tmp_path, "three_steps")
        f = DPvzVtk(path, DPvzMode.DPvzCreate)
        f.write(0,  0.0,  PAYLOAD_1)
        f.write(10, 1.0,  PAYLOAD_2)
        f.write(20, 2.0,  PAYLOAD_3)
        return path

    def test_write_three_steps(self, tmp_path):
        """Write 3 time steps and verify step count."""
        path = self._create_3step_file(tmp_path)
        f = DPvzVtk(path, DPvzMode.DPvzReadOnly)
        steps = f.get_steps()
        print(f"\n  [WRITE] {path}: {steps} steps")
        assert steps == 3

    def test_get_map_returns_correct_cycles_and_times(self, tmp_path):
        """get_map returns DPvzTocEntry list with correct cycle/time values."""
        path = self._create_3step_file(tmp_path)
        f = DPvzVtk(path, DPvzMode.DPvzReadOnly)
        toc_map = f.get_map()
        print(f"\n  [MAP] entries: {[(e.cycle, e.time) for e in toc_map]}")
        assert len(toc_map) == 3
        assert toc_map[0].cycle == 0  and abs(toc_map[0].time - 0.0) < 1e-9
        assert toc_map[1].cycle == 10 and abs(toc_map[1].time - 1.0) < 1e-9
        assert toc_map[2].cycle == 20 and abs(toc_map[2].time - 2.0) < 1e-9

    def test_get_map_entry_has_rank_count(self, tmp_path):
        """Each DPvzTocEntry.ranks == 1 for a single-rank write."""
        path = self._create_3step_file(tmp_path)
        f = DPvzVtk(path, DPvzMode.DPvzReadOnly)
        for entry in f.get_map():
            print(f"\n  [MAP] cycle={entry.cycle} ranks={entry.ranks}")
            assert entry.ranks == 1

    def test_get_step_toc(self, tmp_path):
        """get_step_toc returns one DPvzRankToc per rank (1 rank here)."""
        path = self._create_3step_file(tmp_path)
        f = DPvzVtk(path, DPvzMode.DPvzReadOnly)
        toc_map = f.get_map()
        rank_toc = f.get_step_toc(toc_map[0])
        print(f"\n  [STEP_TOC] step0: {rank_toc}")
        assert len(rank_toc) == 1
        rt = rank_toc[0]
        assert rt.inflated_size > 0

    def test_readback_payload_step0(self, tmp_path):
        """get_data returns the decompressed original payload for step 0."""
        path = self._create_3step_file(tmp_path)
        f = DPvzVtk(path, DPvzMode.DPvzReadOnly)
        toc_map = f.get_map()
        rank_toc = f.get_step_toc(toc_map[0])
        data = f.get_data(rank_toc[0])
        print(f"\n  [DATA0] inflated={rank_toc[0].inflated_size} bytes read={len(data)}")
        assert data == PAYLOAD_1

    def test_readback_payload_step1(self, tmp_path):
        """get_data returns the correct payload for step 1."""
        path = self._create_3step_file(tmp_path)
        f = DPvzVtk(path, DPvzMode.DPvzReadOnly)
        toc_map = f.get_map()
        rank_toc = f.get_step_toc(toc_map[1])
        data = f.get_data(rank_toc[0])
        print(f"\n  [DATA1] inflated={rank_toc[0].inflated_size} bytes read={len(data)}")
        assert data == PAYLOAD_2

    def test_readback_payload_step2(self, tmp_path):
        """get_data returns the correct payload for step 2."""
        path = self._create_3step_file(tmp_path)
        f = DPvzVtk(path, DPvzMode.DPvzReadOnly)
        toc_map = f.get_map()
        rank_toc = f.get_step_toc(toc_map[2])
        data = f.get_data(rank_toc[0])
        print(f"\n  [DATA2] inflated={rank_toc[0].inflated_size} bytes read={len(data)}")
        assert data == PAYLOAD_3


# ---------------------------------------------------------------------------
# Task 3.1.C  –  File truncation
# ---------------------------------------------------------------------------

class TestTruncation:

    def _create_3step_file(self, tmp_path):
        path = make_vtk_path(tmp_path, "trunc_test")
        f = DPvzVtk(path, DPvzMode.DPvzCreate)
        f.write(0,  0.0,  PAYLOAD_1)
        f.write(10, 1.0,  PAYLOAD_2)
        f.write(20, 2.0,  PAYLOAD_3)
        return path

    def test_truncate_from_step1(self, tmp_path):
        """truncate(1) removes steps 1 and 2, leaving only step 0."""
        path = self._create_3step_file(tmp_path)
        f = DPvzVtk(path, DPvzMode.DPvzReadWrite)
        assert f.get_steps() == 3
        ok = f.truncate(1)
        assert not ok, "truncate should return False (no error)"
        steps = f.get_steps()
        print(f"\n  [TRUNC1] steps after truncate(1): {steps}")
        assert steps == 1

    def test_truncate_from_step0_empties_file(self, tmp_path):
        """truncate(0) empties the file."""
        path = self._create_3step_file(tmp_path)
        f = DPvzVtk(path, DPvzMode.DPvzReadWrite)
        f.truncate(0)
        steps = f.get_steps()
        print(f"\n  [TRUNC0] steps after truncate(0): {steps}")
        assert steps == 0

    def test_truncate_then_rewrite(self, tmp_path):
        """After truncation we can write new steps into the file."""
        path = self._create_3step_file(tmp_path)
        f = DPvzVtk(path, DPvzMode.DPvzReadWrite)
        f.truncate(1)
        # Write a brand-new step
        new_payload = b"new data after truncation"
        f.write(99, 9.9, new_payload)
        assert f.get_steps() == 2
        toc_map = f.get_map()
        rank_toc = f.get_step_toc(toc_map[1])
        data = f.get_data(rank_toc[0])
        print(f"\n  [TRUNC_REWRITE] new step data: {data}")
        assert data == new_payload


# ---------------------------------------------------------------------------
# Task 3.1.D  –  DPvzVtk.list() and DPvzVtk.show() static methods
# ---------------------------------------------------------------------------

class TestStaticMethods:

    def test_list_on_sample_file(self):
        """DPvzVtk.list() should succeed on the bundled sample archive."""
        sample = "/workspaces/AllVibesDemo/dpvz/utils/hohler-stilp-2ranks-5cycles.dpvtk"
        if not os.path.exists(sample):
            pytest.skip("Sample dpvtk file not found")
        rc = DPvzVtk.list(sample, ".")
        print(f"\n  [LIST] return code = {rc}")
        assert rc == 0

    def test_show_on_sample_file(self):
        """DPvzVtk.show() should succeed on the bundled sample archive."""
        sample = "/workspaces/AllVibesDemo/dpvz/utils/hohler-stilp-2ranks-5cycles.dpvtk"
        if not os.path.exists(sample):
            pytest.skip("Sample dpvtk file not found")
        rc = DPvzVtk.show(sample, ".")
        print(f"\n  [SHOW] return code = {rc}")
        assert rc == 0
