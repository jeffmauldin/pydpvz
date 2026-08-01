# pydpvz

Python bindings and VTK serialization utilities for Sandia National Laboratories' **DPvz** parallel I/O library.

## Overview & Modules

`pydpvz` consists of native pybind11 C++ bindings (`DPvzFile`, `DPvzVtk`, `DPvzMode`) and pure Python VTK stream transformation modules:
- **`pydpvz.vtk_serializer`**: Converts VTK dataset objects into byte streams suitable for direct ingestion into `DPvzVtk.write()`. Specifically, `extract_hierarchy_and_blocks()` traverses complex multi-block (`vtkMultiBlockDataSet`) and partitioned (`vtkPartitionedDataSetCollection`) structures, generating an embedded `hierarchy.json` metadata record to retain exact component indices and names without creating empty geometry meshes on parallel ranks.
- **`pydpvz.vtk_deserializer`**: Unpacks archive binary buffers (`deserialize_vtk_from_buffer`), interrogates any embedded `hierarchy.json` records, and transparently populates native `vtkPartitionedDataSetCollection` objects while preserving original multi-block naming schemes.

## Installation
```bash
# Set CC and CXX to match your ParaView MPI wrapper (e.g. mpicc.mpich / mpicxx.mpich)
CC=mpicc.mpich CXX=mpicxx.mpich pip install -e .
```
