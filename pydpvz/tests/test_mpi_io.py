"""
test_mpi_io.py  –  Phase 3 Task 3.2
Parallel MPI unit tests for pydpvz DPvzVtk using mpi4py.

Run with:
    cd /tmp && mpirun -n 2 python3 -m pytest /workspaces/AllVibesDemo/pydpvz/tests/test_mpi_io.py -v -s
    cd /tmp && mpirun -n 4 python3 -m pytest /workspaces/AllVibesDemo/pydpvz/tests/test_mpi_io.py -v -s

NOTE: Each MPI rank runs all tests; pytest barriers are used via MPI_Barrier
      to synchronise assertions across ranks.
"""

import os
import tempfile
import pytest

from mpi4py import MPI
import pydpvz
from pydpvz import DPvzMode, DPvzVtk

COMM = MPI.COMM_WORLD
RANK = COMM.Get_rank()
SIZE = COMM.Get_size()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def barrier(label=""):
    """Collective barrier with optional label printed on rank 0."""
    COMM.Barrier()
    if RANK == 0 and label:
        print(f"\n  [BARRIER] {label}", flush=True)


def shared_tmp(base_dir="/tmp"):
    """
    All ranks agree on the same temp directory path (rank 0 creates it,
    others just receive it).
    """
    if RANK == 0:
        path = tempfile.mkdtemp(dir=base_dir, prefix="pydpvz_mpi_")
    else:
        path = None
    path = COMM.bcast(path, root=0)
    barrier("shared_tmp created")
    return path


def archive_path(tmp_dir, name):
    return os.path.join(tmp_dir, f"{name}.dpvtk")


# ---------------------------------------------------------------------------
# Task 3.2.A  –  Collective parallel write
# ---------------------------------------------------------------------------

class TestParallelWrite:

    def test_collective_write_single_step(self):
        """All ranks collectively write one time step; verify step count."""
        tmp = shared_tmp()
        path = archive_path(tmp, "par_single_step")

        rank_payload = f"rank{RANK} cycle0 data".encode()

        f = DPvzVtk(path, DPvzMode.DPvzCreate, COMM)
        assert not f.failed(), f"Rank {RANK}: DPvzCreate failed"

        ok = f.write(0, 0.0, rank_payload)
        assert not ok, f"Rank {RANK}: write returned error"

        steps = f.get_steps()
        barrier("after single-step write")
        if RANK == 0:
            print(f"\n  [PAR_WRITE1] {path}: {steps} steps, {SIZE} ranks")
        assert steps == 1, f"Rank {RANK}: expected 1 step, got {steps}"

    def test_collective_write_multiple_steps(self):
        """All ranks collectively write 3 time steps."""
        tmp = shared_tmp()
        path = archive_path(tmp, "par_three_steps")

        f = DPvzVtk(path, DPvzMode.DPvzCreate, COMM)

        for cycle in [0, 10, 20]:
            time = cycle * 0.1
            payload = f"rank{RANK} cycle{cycle}".encode()
            ok = f.write(cycle, time, payload)
            assert not ok, f"Rank {RANK}: write cycle {cycle} returned error"

        steps = f.get_steps()
        barrier("after 3-step write")
        if RANK == 0:
            print(f"\n  [PAR_WRITE3] {path}: {steps} steps")
        assert steps == 3


# ---------------------------------------------------------------------------
# Task 3.2.B  –  TOC verification across ranks
# ---------------------------------------------------------------------------

class TestParallelToc:

    def _write_5steps(self, tmp):
        path = archive_path(tmp, "par_toc_5steps")
        f = DPvzVtk(path, DPvzMode.DPvzCreate, COMM)
        for i in range(5):
            payload = f"rank{RANK} step{i}".encode()
            f.write(i * 100, float(i), payload)
        barrier("after 5-step write")
        return path

    def test_toc_entry_count(self):
        """get_map returns 5 entries after 5 collective writes."""
        tmp = shared_tmp()
        path = self._write_5steps(tmp)

        f = DPvzVtk(path, DPvzMode.DPvzReadOnly, COMM)
        toc = f.get_map()
        if RANK == 0:
            print(f"\n  [TOC] {len(toc)} entries: {[(e.cycle, round(e.time,2)) for e in toc]}")
        assert len(toc) == 5

    def test_toc_each_entry_has_all_ranks(self):
        """Each DPvzTocEntry.ranks equals the MPI communicator size."""
        tmp = shared_tmp()
        path = self._write_5steps(tmp)

        f = DPvzVtk(path, DPvzMode.DPvzReadOnly, COMM)
        toc = f.get_map()
        for entry in toc:
            assert entry.ranks == SIZE, \
                f"Rank {RANK}: entry cycle={entry.cycle} has ranks={entry.ranks}, expected {SIZE}"
        if RANK == 0:
            print(f"\n  [TOC_RANKS] all entries have ranks={SIZE}")

    def test_toc_cycles_and_times(self):
        """TOC entries carry correct cycle numbers (0,100,200,300,400) and times."""
        tmp = shared_tmp()
        path = self._write_5steps(tmp)

        f = DPvzVtk(path, DPvzMode.DPvzReadOnly, COMM)
        toc = f.get_map()
        expected_cycles = [0, 100, 200, 300, 400]
        for i, entry in enumerate(toc):
            assert entry.cycle == expected_cycles[i], \
                f"Rank {RANK}: entry[{i}].cycle={entry.cycle}, expected {expected_cycles[i]}"
            assert abs(entry.time - float(i)) < 1e-9, \
                f"Rank {RANK}: entry[{i}].time={entry.time}, expected {float(i)}"
        if RANK == 0:
            print(f"\n  [TOC_VALS] cycles/times verified correctly")


# ---------------------------------------------------------------------------
# Task 3.2.C  –  Parallel read-back of per-rank payloads
# ---------------------------------------------------------------------------

class TestParallelReadback:

    def _write_and_path(self, tmp):
        path = archive_path(tmp, "par_readback")
        f = DPvzVtk(path, DPvzMode.DPvzCreate, COMM)
        # Each rank writes a unique, identifiable payload
        payload = f"RANK{RANK:02d}_CYCLE0_DATA".encode()
        f.write(0, 0.0, payload)
        barrier("write done")
        return path

    def test_each_rank_reads_its_own_data(self):
        """After a parallel write, each rank can read back its own payload."""
        tmp = shared_tmp()
        path = self._write_and_path(tmp)

        f = DPvzVtk(path, DPvzMode.DPvzReadOnly, COMM)
        toc = f.get_map()
        step = toc[0]
        step_toc = f.get_step_toc(step)

        assert len(step_toc) == SIZE, \
            f"Rank {RANK}: expected {SIZE} rank entries, got {len(step_toc)}"

        # Read this rank's own entry (step_toc is indexed by rank order)
        own_toc = step_toc[RANK]
        data = f.get_data(own_toc)
        expected = f"RANK{RANK:02d}_CYCLE0_DATA".encode()
        print(f"\n  [READBACK] rank{RANK}: got {data!r}, expected {expected!r}")
        assert data == expected, \
            f"Rank {RANK}: data mismatch: {data!r} != {expected!r}"

    def test_rank0_reads_all_other_ranks_data(self):
        """Rank 0 can read any rank's payload from the shared archive."""
        tmp = shared_tmp()
        path = self._write_and_path(tmp)

        if RANK == 0:
            f = DPvzVtk(path, DPvzMode.DPvzReadOnly, COMM)
            toc = f.get_map()
            step_toc = f.get_step_toc(toc[0])
            for r in range(SIZE):
                data = f.get_data(step_toc[r])
                expected = f"RANK{r:02d}_CYCLE0_DATA".encode()
                print(f"  [READBACK_ALL] rank0 reads rank{r}: {data!r}")
                assert data == expected
        else:
            # Non-rank-0 processes open read-only too (needed for collective ops)
            f = DPvzVtk(path, DPvzMode.DPvzReadOnly, COMM)
        barrier("readback_all done")


# ---------------------------------------------------------------------------
# Task 3.2.D  –  Parallel truncation
# ---------------------------------------------------------------------------

class TestParallelTruncation:

    def test_parallel_truncate(self):
        """Collective truncate(1) removes steps 1+ from a 3-step archive."""
        tmp = shared_tmp()
        path = archive_path(tmp, "par_trunc")

        f = DPvzVtk(path, DPvzMode.DPvzCreate, COMM)
        for cycle in [0, 10, 20]:
            f.write(cycle, float(cycle), f"rank{RANK} c{cycle}".encode())

        barrier("before truncate")
        assert f.get_steps() == 3

        ok = f.truncate(1)
        assert not ok, f"Rank {RANK}: truncate returned error"
        steps = f.get_steps()
        barrier("after truncate")
        if RANK == 0:
            print(f"\n  [PAR_TRUNC] steps after truncate(1): {steps}")
        assert steps == 1
