# conftest.py for pydpvz tests
# Ensures MPI is initialized before any test imports pydpvz,
# and finalized after the session. This is needed even for serial
# tests because pydpvz._pydpvz is compiled with DPVZ_MPI=1.

import pytest

def pytest_configure(config):
    """Initialize MPI at pytest startup, before collection."""
    from mpi4py import MPI
    # MPI.Init() is called automatically by mpi4py on import, so this
    # is a no-op in practice – but makes the dependency explicit.
    _ = MPI.COMM_WORLD.Get_rank()
