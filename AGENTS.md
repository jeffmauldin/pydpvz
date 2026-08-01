# Agent Context & Harness Information

Welcome, fellow AI Agent! If you have been invoked to work on this repository, this document provides the critical context and architectural constraints you need to avoid common pitfalls.

## Project Overview
This repository contains `pydpvz`, a set of lightweight Python bindings for Sandia National Laboratories' `dpvz` parallel I/O library. Alongside it is a suite of utility scripts (`scripts/`) designed to be run inside ParaView's `pvbatch` environment. The goal is to allow highly efficient, parallel serialization and deserialization of massive VTK datasets directly to/from `.dpvtk` archives without overwhelming parallel file systems.

## Key Files & Directories
- **`PLAN.md`**: This is the master architectural document. It contains the history of decisions, the step-by-step build instructions, and the original execution plan. **Always read `PLAN.md` before proposing architectural changes.**
- **`pydpvz/`**: Contains the `pybind11` C++ extensions and Python wrappers. It wraps the core `dpvz` C++ library.
- **`scripts/`**: Contains the ParaView utilities (`dpvtkscreenshot.py`, `dpvtkfilter.py`, etc.). These are designed to be run via `pvbatch --sym`.
- **`dpvz/`**: The upstream C++ parallel I/O library.

## Critical Architectural Constraints (DO NOT IGNORE)

1. **MPI ABI Compatibility**: 
   ParaView ships with its own embedded MPI runtime (often MPICH). If you compile `pydpvz` or `libDPvzMpi.so` against a different MPI implementation (like OpenMPI), it will cause silent deadlocks or immediate segmentation faults. You must ensure the `mpicxx` compiler wrapper used matches ParaView's MPI runtime.

2. **ParaView Symmetric Mode (`pvbatch --sym`)**:
   Any utility script that executes collective MPI operations (like `dpvz.write()`) *must* be launched using `pvbatch --sym`. Without `--sym`, ParaView defaults to asymmetric client-server mode, where Python only executes on Rank 0, leaving Ranks 1+ sitting idle in a C++ event loop. This guarantees a permanent MPI deadlock.

3. **Round-Robin Chunk Distribution on Read**:
   When reading from `.dpvtk` archives, you cannot assume a 1-to-1 mapping between the reading MPI rank and the data block index. Datasets written by `N` ranks might be read by `M` ranks. You **MUST** use a round-robin distribution loop to load chunks:
   ```python
   part_counters = {}
   for w_rank in range(rank, entry.ranks, size):
       rank_entry = step_toc[w_rank]
       buffer_bytes = archive.get_data(rank_entry)
       items = deserialize_vtk_from_buffer(buffer_bytes)
       for item in items:
           idx = item["index"]
           name = item["name"]
           ds = item["dataset"]
           while pdc.GetNumberOfPartitionedDataSets() <= idx:
               pdc.SetNumberOfPartitionedDataSets(idx + 1)
           if name:
               meta = pdc.GetMetaData(idx)
               if meta:
                   meta.Set(vtk.vtkCompositeDataSet.NAME(), name)
           if ds is not None:
               p_idx = part_counters.get(idx, 0)
               pdc.SetPartition(idx, p_idx, ds)
               part_counters[idx] = p_idx + 1
   ```
   ParaView will securely and natively composite these disjoint blocks inside the `vtkPartitionedDataSetCollection` while preserving block hierarchy and names.

4. **VTK Pipeline Requirements**:
   When extracting data from ParaView filters (like `Slice`), always use `.GetClientSideObject().GetOutputDataObject(0)`. Do not just use `.GetOutput()`, as some algorithms return `vtkDataObject` instead of `vtkDataSet`, which will crash the serialization logic.

5. **Dependency Minimalism**:
   This project prides itself on having an ultra-lean dependency tree. Do not introduce heavy libraries like `numpy`, `scipy`, `pandas`, or `h5py` unless absolutely unavoidable and explicitly approved by the human user. The core relies entirely on `mpi4py`, `zlib`, and the Python standard library.

6. **Parallel Piece Extent Synchronization (`RequestUpdateExtent`)**:
   When implementing custom VTK writer algorithms or pipeline sinks (such as `DPvtkWriter` in `scripts/dpvtk_writer_plugin.py`), you **MUST** implement `RequestUpdateExtent(self, request, inInfo, outInfo)` to dynamically set `UPDATE_PIECE_NUMBER()` to the local MPI rank and `UPDATE_NUMBER_OF_PIECES()` to the communicator size on upstream executive ports. Without this explicit request, upstream readers default to serial piece requests (piece 0 of 1 on every process), causing every MPI rank to read and write an identical copy of the full dataset into the archive ($N\times$ redundant bloat).

7. **Hierarchical Dataset Preservation & Empty Partitions**:
   When serializing composite datasets (`vtkMultiBlockDataSet` or `vtkPartitionedDataSetCollection`) to `.dpvtk` archives, never blindly flatten top-level blocks into a single unstructured grid. You must maintain block hierarchy and block names by using `pydpvz.vtk_serializer.extract_hierarchy_and_blocks()`, which embeds a `<FILE NAME='hierarchy.json'>` metadata manifest into each rank's archive stream. In parallel runs, some ranks may own zero geometry cells/points for specific blocks; you must preserve these block entries in `hierarchy.json` without executing or writing empty mesh byte payloads.

## How to Proceed
If the user has asked you to add a new feature or utility:
1. Check `PLAN.md` to see if a similar phase already exists.
2. Read the source code of an existing utility (e.g., `scripts/dpvtkscreenshot.py`) to understand the boilerplate for initializing `pydpvz` and the `TrivialProducer`.
3. Plan your changes, keeping the constraints above in mind.
