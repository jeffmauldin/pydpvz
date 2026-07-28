"""
pydpvz: Python bindings for Sandia National Laboratories DPvz parallel I/O library.

mpi4py is imported first to ensure MPI_Init() is called before the dpvz C++
shared library makes any MPI calls (e.g. MPI_Comm_rank) during module load.
"""

# IMPORTANT: mpi4py must be imported before _pydpvz so that OpenMPI is
# initialized before the dpvz C++ library references any MPI state.
from mpi4py import MPI as _MPI  # noqa: F401

from ._pydpvz import (
    DPvzMode,
    DPvzTocEntry,
    DPvzRankToc,
    DPvzFile,
    DPvzVtk,
)

__all__ = [
    "DPvzMode",
    "DPvzTocEntry",
    "DPvzRankToc",
    "DPvzFile",
    "DPvzVtk",
]
