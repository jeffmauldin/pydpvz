# Master Implementation Plan: Parallel DPvz Python Wrappers and ParaView Integration

## Executive Summary
This master plan outlines the engineering steps to build a standalone, reusable Python library (**`pydpvz`**) wrapping Sandia National Laboratories' **DPvz** C++ parallel I/O library (`dpvz`), and integrate it with ParaView's `pvbatch` / `pvpython` environment (**ParaView 6.1.0**).

The primary goal is to enable parallel `pvbatch` jobs to read complex partitioned and multi-block datasets (specifically **Exodus II / `.vtpc`** via `IOSSReader()`, and **`.vtm`** via `XMLMultiBlockReader()`), serialize them in memory across MPI ranks, and export them into single-file compressed `.dpvz` / `.dpvtk` archives without overwhelming parallel file system metadata servers (MDTs/OSTs).

### Key Workflow Targets

1. **Partitioned Dataset / Exodus II Target (`.vtpc` / `.ex2`)**:
   ```bash
   mpiexec.mpich -np 4 ./paraview_v610/bin/pvbatch --sym scripts/dpvtkconvert.py --input sample_data/can_data/can_data_4_process_exodus/can.ex2.4.0 --output output_can_exodus.dpvtk
   mpiexec.mpich -np 4 ./paraview_v610/bin/pvbatch --sym scripts/dpvtkconvert.py --input sample_data/can_data/can_data_4_process_vtpc/can_vtpc_0.vtpc --output output_can_vtpc.dpvtk
   mpiexec.mpich -np 4 ./paraview_v610/bin/pvbatch --sym scripts/dpvtkconvert.py --input sample_data/hifire_example_data/hifire_volume_0001.vtpc --output output_hifire.dpvtk
   ```
   Where `dpvtkconvert.py` executes in parallel across 4 MPI ranks:
   - `IOSSReader()` reads `.vtpc` / `.ex2` / Exodus dataset partitions in parallel across all 4 MPI processes.
   - `pydpvz.vtk_serializer` serializes local rank partitions in memory into VTK XML string streams.
   - `pydpvz.DPvzVtk` executes a collective MPI write operation (`dpvz.write(cycle, time, buffer)`), writing compressed rank streams directly into a single page-aligned `.dpvtk` archive file.

2. **MultiBlock Dataset (`.vtm`) Target**:
   ```bash
   mpiexec -np 4 pvbatch scripts/convertvtmscript1.py sample_data/can_data/can_data_4_process_vtkm/can_vtkm_0.vtm output_can_vtm.dpvtk
   mpiexec -np 4 pvbatch scripts/convertvtmscript1.py sample_data/rigid_body_data/rigid_body_vtm/rigid_body_test_volume_vtm_0.vtm output_rigid_vtm.dpvtk
   ```
   Where `convertvtmscript1.py` executes in parallel across 4 MPI ranks:
   - `XMLMultiBlockReader()` (`vtkXMLPMultiBlockDataReader`) reads `.vtm` multi-block datasets in parallel across all 4 MPI processes.
   - `pydpvz.vtk_serializer` serializes local rank multi-block dataset pieces in memory into VTK XML string streams.
   - `pydpvz.DPvzVtk` executes a collective MPI write operation (`dpvz.write(cycle, time, buffer)`), outputting a single page-aligned `.dpvtk` archive.

---

## 1. Environment & Storage Analysis

### 1.1 Storage Requirements
* **Location**: `/workspaces/AllVibesDemo` on Drive `D:\`
* **Available Space**: **~62 GB** free (Verified via `df -h`).
* **Existing Sample Datasets (`sample_data/`)**: **~250 MB**.
  - `can_data/`: Single-process `.ex2`, 4-process split `.ex2` (`can.ex2.4.0..3`), 4-process `.vtpc`, 4-process `.vtm`.
  - `rigid_body_data/`: Multi-timestep `.vtm`, multi-timestep `.vtpc`, `.pvd`/`.vtu` unstructured grid, single-timestep subfolder.
  - `hifire_example_data/`: 1-timestep fluid dynamics simulation `.vtpc` split across 4 ranks (`hifire_volume_0001.vtpc`).
* **Expected Total Storage Consumption**:
  - **ParaView 6.1.0 Archive (`paraview_6.1.0.tar.gz`)**: ~827 MB (Cached locally in workspace for instant re-use).
  - **Extracted ParaView 6.1.0 (`paraview_bin/`)**: **~2.4 GB**.
  - **`pydpvz` Extension Library**: **< 50 MB**.
  - **Total Footprint**: **< 3.5 GB**.

> **Disk Space Conclusion**: The total workspace footprint with ParaView 6.1.0 and all sample datasets is less than 3.5 GB. The 62 GB on `D:\` is more than enough, so **there is no need to attach or use the external `G:\` drive**.

---

## 2. Socratic Architectural Analysis & Key Decisions

### Decision 1: Parallel Repository & Sample Data Structure
* **Socratic Question**: *How should sample data and parallel repositories be organized in the workspace?*
* **Analysis**: Placing test datasets in `/workspaces/AllVibesDemo/sample_data/` isolates test assets from code repositories. `dpvz` remains clean upstream C++ code, `pydpvz` contains Python wrapper source code and unit tests, and `sample_data/` provides deterministic inputs for script integration testing.
* **Decision**: Organize datasets under `sample_data/can_data`, `sample_data/rigid_body_data`, and `sample_data/hifire_example_data`.

### Decision 2: Comprehensive Unit & Integration Testing Strategy
* **Socratic Question**: *How should unit tests for the `pydpvz` library and conversion scripts be structured?*
* **Analysis**:
  - **`pydpvz` C++ Extension Unit Tests**: Test serial (`DPvzFile`, `DPvzVtk`) and parallel (`mpi4py`) API calls directly via `pytest` to ensure Python wrappers function correctly independent of ParaView.
  - **Conversion Script Integration Tests**: Test `dpvtkconvert.py` by launching `mpiexec.mpich -np 4 pvbatch --sym` against the actual `sample_data/` files, then verifying the generated `.dpvtk` archives using `dpvz/utils/dpvtk-ar-ser --list` and `--extract`.
* **Decision**: Implement dual test suites in `pydpvz/tests/` (unit tests) and `scripts/tests/` (conversion script integration tests).

### Decision 3: C++ Binding Technology
* **Socratic Question**: *What binding tool should be used for `pydpvz`?*
* **Analysis**: **pybind11** is ideal. It binds C++ classes (`DPvzFile`, `DPvzVtk`), handles STL strings/buffers natively, and supports custom type casters for `mpi4py` communicators.
* **Decision**: Build `pydpvz` using pybind11 and `setuptools`/`scikit-build-core`.

### Decision 4: MPI Communicator Interoperability
* **Socratic Question**: *How do we convert Python `mpi4py.MPI.COMM_WORLD` into native C++ `MPI_Comm`?*
* **Analysis**: `mpi4py` provides raw C-API pointers and integer handles (`MPI_Comm_f2c`).
* **Decision**: Implement a C++ type caster in `pydpvz/src/mpi_caster.h` allowing Python code to pass `mpi4py.MPI.COMM_WORLD` directly into `pydpvz.DPvzVtk` constructors.

### Decision 5: ParaView 6.1.0 MPI & Python 3.12 Compatibility
* **Socratic Question**: *How do we prevent ABI crashes between ParaView 6.1.0's MPI runtime and `pydpvz`?*
* **Analysis**: ParaView 6.1.0 links against a specific MPI library and runs Python 3.12. `libDPvzMpi.so` and `pydpvz` must be compiled using an MPI compiler wrapper (`mpicxx`) that is ABI-compatible with ParaView 6.1.0.
* **Decision**: Inspect ParaView 6.1.0's embedded MPI headers/libraries prior to compiling `pydpvz`.

### Decision 6: Dynamic Rank Mapping (Round-Robin) for VTK Readers
* **Socratic Question**: *How do we ensure all dataset blocks are loaded when the number of reading ranks is less than the number of writing ranks?*
* **Analysis**: If the read utilities naively index `step_toc[rank]`, any dataset written by `N` ranks but read by `M` ranks (where `M < N`) will truncate and silently lose `N - M` blocks of data.
* **Decision**: All `.dpvtk` reading utilities (`dpvtkscreenshot.py`, `dpvtkanimate.py`, `dpvtkextract.py`, etc.) MUST implement a round-robin chunk distribution loop (`for w_rank in range(rank, entry.ranks, size):`). This gracefully assigns multiple written data chunks to each available reading process. ParaView natively composites these disjoint blocks securely inside a `vtkPartitionedDataSetCollection`.

### Decision 7: Parallel Piece Request Coordination (`RequestUpdateExtent`)
* **Socratic Question**: *How do we ensure each MPI rank converts only its local slice of a distributed dataset instead of duplicating the entire global mesh on every process?*
* **Analysis**: When ParaView executes a distributed filter pipeline in symmetric batch mode (`pvbatch --sym`), data sources (such as `XMLMultiBlockReader` or `IOSSReader`) rely on downstream sink algorithms to instruct them on how to partition the data across MPI processes. If a writer plugin does not implement an explicit update extent request, VTK falls back to serial default requests (piece 0 of 1 on every process), causing all $N$ ranks to read and write an identical full-dataset copy into the `.dpvtk` file ($N\times$ redundant bloat).
* **Decision**: All custom VTK writer algorithm plugins (`DPvtkWriter`) MUST implement `RequestUpdateExtent(self, request, inInfo, outInfo)`. Within this method, the plugin must query `MPI.COMM_WORLD` and set `UPDATE_PIECE_NUMBER()` to `comm.Get_rank()` and `UPDATE_NUMBER_OF_PIECES()` to `comm.Get_size()`. This ensures true distributed partitioning with zero data duplication.

### Decision 8: Hierarchical Dataset Preservation & Metadata Serialization
* **Socratic Question**: *How do we preserve complex multi-block hierarchies and component names when serializing data to DPvz archives, especially when partitions on some MPI ranks contain zero cells or points?*
* **Analysis**: Converting composite datasets (`vtkMultiBlockDataSet` or `vtkPartitionedDataSetCollection`) by flattening all top-level blocks into a single amorphous unstructured grid destroys critical simulation metadata (e.g., structural part names like `block_1`, `block_2` in car crash or aerospace meshes). Furthermore, in partitioned MPI environments, a local rank might own geometry for `block_1` but zero cells for `block_2`. If empty partitions cause serialization errors or omit hierarchy structure, reconstruction upon reading will fail or lose block identities.
* **Decision**: `pydpvz.vtk_serializer` MUST implement hierarchical block traversal (`extract_hierarchy_and_blocks()`). Instead of merging disjoint blocks, it extracts individual top-level blocks with their indices and names and serializes an explicit `<FILE NAME='hierarchy.json'>` manifest into every rank's archive stream alongside non-empty geometry blocks. Conversely, `pydpvz.vtk_deserializer` and all ParaView reading scripts must parse `hierarchy.json` to reconstruct the exact multi-block tree inside a native `vtkPartitionedDataSetCollection`, assigning block metadata accurately even when local geometries are empty.

---

## 3. Parallel Directory Layout

```text
/workspaces/AllVibesDemo/
├── PLAN.md                         # Master workspace plan and state tracker
├── paraview_6.1.0.tar.gz          # LOCAL CACHED PARAVIEW 6.1.0 TARBALL (827 MB)
├── sample_data/                    # SAMPLE TEST DATASETS
│   ├── can_data/                   # "Can" crash demo dataset
│   │   ├── can_data_1_process_exodus/    # single process can.ex2
│   │   ├── can_data_4_process_exodus/    # 4-process split can.ex2.4.0..3
│   │   ├── can_data_4_process_vtpc/      # 4-process .vtpc timesteps
│   │   └── can_data_4_process_vtkm/      # 4-process .vtm timesteps
│   ├── rigid_body_data/            # Rigid body simulation dataset
│   │   ├── rigid_body_vtm/           # .vtm timesteps
│   │   ├── rigid_body_vtpc/          # .vtpc timesteps
│   │   ├── rigid_body_vtm_one_timestep/ # 1 timestep .vtpc & .vtm
│   │   └── rigid_body_pvd_unstructured_grid/ # .pvd / .vtu dataset
│   └── hifire_example_data/        # HiFIRE fluid dynamics dataset
│       └── hifire_volume_0001.vtpc # 1-timestep 4-process .vtpc dataset
├── dpvz/                           # Upstream Sandia C++ repository
│   ├── CMakeLists.txt
│   ├── src/                        # Core C++ source code (DPvzFile.C, etc.)
│   ├── doc/                        # Design PDF documentation
│   └── utils/                      # dpvtk-ar utility & sample dataset
├── pydpvz/                         # STANDALONE PYTHON WRAPPER REPOSITORY
│   ├── pyproject.toml              # PEP 517 packaging metadata
│   ├── setup.py                    # setuptools build file
│   ├── CMakeLists.txt              # pybind11 module compilation
│   ├── src/
│   │   ├── main_bindings.cpp       # pybind11 C++ class bindings
│   │   └── mpi_caster.h            # mpi4py <-> MPI_Comm type casting
│   ├── pydpvz/                     # Python package namespace
│   │   ├── __init__.py             # Exposes DPvzFile, DPvzVtk, DPvzMode
│   │   └── vtk_serializer.py       # VTK in-memory dataset serializer
│   └── tests/                      # PYDPVZ UNIT TEST SUITE
│       ├── test_serial_io.py       # Unit tests for serial DPvzFile / DPvzVtk
│       └── test_mpi_io.py          # Unit tests for parallel mpi4py DPvzVtk
└── scripts/                        # WORKSPACE CONVERSION & INTEGRATION SCRIPTS
    ├── setup_paraview.sh           # ParaView 6.1.0 download and environment setup
    ├── dpvtkconvert.py             # Unified parallel pvbatch script (all ParaView formats -> .dpvtk)
    ├── convertvtmscript1.py        # Parallel pvbatch script (.vtm -> .dpvtk)
    └── tests/                      # CONVERSION SCRIPT INTEGRATION TESTS
        ├── test_convert_vtpc.py    # Integration tests running mpiexec pvbatch convertvtpcscript1.py
        └── test_convert_vtm.py     # Integration tests running mpiexec pvbatch convertvtmscript1.py
```

---

## 4. Phased Execution Plan & Progress Tracking

AI assistants or developers executing this plan **MUST update the checkboxes (`[ ]` -> `[x]`)** as tasks are completed.

### Phase 1: Environment Setup & Sample Data Verification [COMPLETED]
- [x] **Task 1.1**: Verify existing datasets in `sample_data/` (`can_data`, `rigid_body_data`, `hifire_example_data`).
- [x] **Task 1.2**: Write `scripts/setup_paraview.sh` to fetch and locally cache ParaView 6.1.0 (`paraview_6.1.0.tar.gz`).
- [x] **Task 1.3**: Extract ParaView 6.1.0 into `/workspaces/AllVibesDemo/paraview_v610`.
- [x] **Task 1.4**: Test `pvpython` and `pvbatch` execution, verifying Python 3.12 version and embedded MPI runtime.
- [x] **Task 1.5**: Confirm disk space remaining on `D:\`.

### Phase 2: Create Parallel `pydpvz` Repository & C++ Bindings [COMPLETED]
- [x] **Task 2.1**: Initialize the parallel directory `/workspaces/AllVibesDemo/pydpvz` with `pyproject.toml`, `setup.py`, and `CMakeLists.txt`.
- [x] **Task 2.2**: Implement `pydpvz/src/mpi_caster.h` for `mpi4py` to `MPI_Comm` pointer casting.
- [x] **Task 2.3**: Implement `pydpvz/src/main_bindings.cpp` exposing:
  - `DPvzMode` enum (`DPvzReadOnly`, `DPvzReadWrite`, `DPvzCreate`, `DPvzReplace`)
  - `DPvzFile` C++ class bindings
  - `DPvzVtk` C++ class bindings (`write`, `get_map`, `get_step_toc`, `get_data`, `truncate`, `close`)
  - `DPvzTocEntry` and `DPvzRankToc` struct bindings
- [x] **Task 2.4**: Build `pydpvz` in editable mode (`pip install -e /workspaces/AllVibesDemo/pydpvz`) and verify `import pydpvz` in `python3` and `pvpython`.

### Phase 3: `pydpvz` Package Unit Testing Suite [COMPLETED]
- [x] **Task 3.1**: Create `pydpvz/tests/test_serial_io.py` testing:
  - File creation (`DPvzCreate`, `DPvzReplace`).
  - Serial buffer writing and reading (`write`, `get_data`).
  - Map and TOC retrieval (`get_map`, `get_step_toc`).
  - File truncation (`truncate`).
- [x] **Task 3.2**: Create `pydpvz/tests/test_mpi_io.py` testing:
  - Collective parallel writing with `mpi4py.MPI.COMM_WORLD`.
  - Parallel TOC indexing across 2 and 4 ranks.
- [x] **Task 3.3**: Run `pytest` and `mpirun -n 2 python3 -m pytest` on `pydpvz/tests/`.
- [x] **Task 3.4**: Validate output archives using `dpvz/utils/dpvtk-ar-ser --list`.

### Phase 4: VTK Dataset Serializer Implementation (`.vtpc`, `.ex2`, `.vtm`) [COMPLETED]
- [x] **Task 4.1**: Implement `pydpvz/pydpvz/vtk_serializer.py` containing:
  - `serialize_partitioned_dataset_collection(pdc, rank, cycle, time)`
  - `serialize_multiblock_dataset(mb, rank, cycle, time)`
  - `convert_pdc_to_multiblock(pdc)` using `vtkConvertToMultiBlockFilter`.
- [x] **Task 4.2**: Verify in-memory XML stream serialization in `pvpython` against `sample_data/can_data` and `sample_data/rigid_body_data`.

### Phase 5: Parallel `pvbatch` Conversion Scripts & Integration Testing Suite [COMPLETED]
- [x] **Task 5.1**: Write `scripts/convertvtpcscript1.py` for Exodus II / `.vtpc` datasets:
  - Initializes `paraview.simple`.
  - Reads dataset in parallel via `OpenDataFile()`.
  - Serializes local partitions in memory via `pydpvz.vtk_serializer`.
  - Performs collective `dpvz.write()` across MPI ranks to `.dpvtk` output file.
- [x] **Task 5.2**: Write `scripts/convertvtmscript1.py` for `.vtm` datasets:
  - Initializes `paraview.simple`.
  - Reads dataset in parallel via `OpenDataFile()`.
  - Serializes local multi-block dataset pieces in memory via `pydpvz.vtk_serializer`.
  - Performs collective `dpvz.write()` across MPI ranks to `.dpvtk` output file.
- [x] **Task 5.3**: Write conversion script integration tests (`scripts/tests/test_convert_vtpc.py` and `scripts/tests/test_convert_vtm.py`) executing:
  - `mpiexec -np 4 pvbatch scripts/convertvtpcscript1.py sample_data/can_data/can_data_4_process_exodus/can.ex2.4.0 output_can_ex.dpvtk`
  - `mpiexec -np 4 pvbatch scripts/convertvtpcscript1.py sample_data/can_data/can_data_4_process_vtpc/can_vtpc_0.vtpc output_can_vtpc.dpvtk`
  - `mpiexec -np 4 pvbatch scripts/convertvtpcscript1.py sample_data/hifire_example_data/hifire_volume_0001.vtpc output_hifire.dpvtk`
  - `mpiexec -np 4 pvbatch scripts/convertvtmscript1.py sample_data/can_data/can_data_4_process_vtkm/can_vtkm_0.vtm output_can_vtm.dpvtk`
  - `mpiexec -np 4 pvbatch scripts/convertvtmscript1.py sample_data/rigid_body_data/rigid_body_vtm/rigid_body_test_volume_vtm_0.vtm output_rigid_vtm.dpvtk`
- [x] **Task 5.4**: Execute integration test runner and verify produced `.dpvtk` archives with `dpvz/utils/dpvtk-ar-ser --list` and `--extract`.

### Phase 6: Implement Reader Capability [COMPLETED]
- [x] **Task 6.1**: Implement ability to read `.dpvtk` files back into ParaView.
- [x] **Task 6.2**: Test parallel `.dpvtk` reading performance.

### Phase 7: Utility Scripts Library - `pvbatch` Screenshot & Environment Setup [COMPLETED]
- [x] **Task 7.1**: Write a shell script (`scripts/setup_env.sh`) that sets the appropriate `PYTHONPATH` and `LD_LIBRARY_PATH` so that `pydpvz` and `dpvz` are accessible by `pvbatch` / `pvpython` when sourced.
- [x] **Task 7.2**: Write `scripts/dpvtkscreenshot.py` that utilizes ParaView to open a `.dpvtk` file, apply the `Show()` command, position the camera appropriately, and save a screenshot as a `.png` via `SaveScreenshot()`. The script must support both serial (1 process) and parallel MPI execution. The script must accept an optional `--viewdirection` / `-vwdr` argument defaulting to `[0, 0, -1]`, and provide process-zero console feedback before and after reading data and saving the image.
- [x] **Task 7.3**: Write tests/validations to confirm the screenshot script functions correctly (testing with `--mesa` to ensure off-screen rendering works).
- [x] **Task 7.4**: Ensure `osmesa` or `--mesa` dependencies are satisfied or appropriately installed if required for offscreen rendering.

### Phase 8: Utility Scripts Library - `dpvtkinfo` Metadata Reporter [COMPLETED]
- [x] **Task 8.1**: Write a Python script (`scripts/dpvtkinfo.py`) that uses `pydpvz` to load a `.dpvtk` file and report its metadata (number of timesteps, time values, number of participating ranks). Also include a detailed data size report listing compressed (`deflated_size`) and uncompressed (`inflated_size`) bytes for every rank in each timestep, which can be skipped if a `--terse` flag is provided.
- [x] **Task 8.2**: Ensure the utility runs extremely fast by only querying metadata (the TOC/map) and bypassing any bulk data loading.
- [x] **Task 8.3**: Verify the utility runs in a standard `python3` environment without needing `pvbatch`, `pvpython`, or an MPI controller.

### Phase 9: Multi-Timestep Support for Conversion Scripts [COMPLETED]
- [x] **Task 9.1**: Modify `scripts/convertvtpcscript1.py` to loop over all available timesteps in the input dataset.
  - Interrogate `reader.TimestepValues` (defaulting to `[0.0]` if empty).
  - Inside a loop, call `reader.UpdatePipeline(time=t)` to explicitly fetch each timestep into memory.
  - Serialize the newly fetched data and append it using `archive.write(cycle, t, xml_string)`.
- [x] **Task 9.2**: Modify `scripts/convertvtmscript1.py` to implement the exact same multi-timestep looping logic for `.vtm` datasets.
- [x] **Task 9.3**: Update conversion script integration tests in `scripts/tests/` to assert that the generated `.dpvtk` files now contain the correct multiple timesteps rather than just a single step.

### Phase 10: Add Timestep Selection to Screenshot Utility [COMPLETED]
- [x] **Task 10.1**: Update `scripts/dpvtkscreenshot.py` to parse an optional `--timestep` integer argument.
- [x] **Task 10.2**: When rendering, instruct the ParaView reader (`OpenDataFile`) to load the specifically requested timestep (e.g., using `reader.UpdatePipeline(time=...)` or `reader.UpdatePipeline()` with the corresponding time value from `reader.TimestepValues`). If `--timestep` is not provided, default to timestep index `0`.
- [x] **Task 10.3**: Ensure process zero console feedback mentions the chosen timestep during the "about to load..." and "about to save screenshot..." print statements.
- [x] **Task 10.4**: Provide documentation/examples on how to execute the script with the `--timestep` argument.

### Phase 11: Create Animation Utility (`dpvtkanimate.py`) [COMPLETED]
- [x] **Task 11.1**: Create `scripts/dpvtkanimate.py` reusing the core ParaView and `pydpvz` logic from `dpvtkscreenshot.py`.
- [x] **Task 11.2**: Set up arguments:
  - `input`: Input `.dpvtk` file.
  - `output_basename`: Output image base name (e.g. `basename` to output `basename_0000.png`).
  - `--viewdirection`: Same vector parsing logic as the screenshot utility.
  - `--timesteprange`: Optional argument parsing a list of two integers (e.g., `[24,36]`).
  - **No** `--timestep` argument.
- [x] **Task 11.3**: Determine the loop range:
  - Read `steps = archive.get_steps()`.
  - If `--timesteprange` is provided, validate the bounds against `steps` and set the loop boundaries.
  - If omitted, default to looping over all timesteps (`0` to `steps - 1`).
- [x] **Task 11.4**: Loop over the determined range. For each `timestep`:
  - Fetch the step TOC and deserialize the partitions (identical to screenshot).
  - Push data to a `paraview.simple.TrivialProducer` (create it once, then use `SetOutput()`, **critically call `producer.MarkModified(producer)`**, and `UpdatePipeline()` per timestep so ParaView recognizes the cached geometry has changed).
  - Configure the camera (same logic).
  - Call `paraview.simple.SaveScreenshot()` outputting zero-padded filenames (e.g. `f"{output_basename}_{timestep:04d}.png"`).
- [x] **Task 11.5**: Implement process-zero console feedback, printing progress inside the loop for each timestep read and image saved.

### Phase 12: Data Extraction Utility (`dpvtkextract.py`) [COMPLETED]
- [x] **Task 12.1**: Create `scripts/dpvtkextract.py` accepting an input `.dpvtk` file and an output `.vtm` or `.vtu` prefix.
- [x] **Task 12.2**: Instantiate a `TrivialProducer` and loop over every timestep in the input `.dpvtk`.
- [x] **Task 12.3**: For each timestep, deserialize the VTK partition, push it to the producer, and use `paraview.simple.SaveData()` to export the raw VTK geometry to disk (e.g., `prefix_0000.vtm`).
- [x] **Task 12.4**: Ensure it runs properly via `pvbatch --sym` so that the output files are partitioned correctly in parallel.

### Phase 13: Splicing Utility (`dpvtksplice.py`) [COMPLETED]
- [x] **Task 13.1**: Create `scripts/dpvtksplice.py` accepting multiple input `.dpvtk` files (via `nargs='+'`) and a single output `.dpvtk` file.
- [x] **Task 13.2**: Initialize a new output `DPvzVtk` archive in `DPvzCreate` or `DPvzReplace` mode.
- [x] **Task 13.3**: For each input archive, loop over its map/timesteps.
- [x] **Task 13.4**: For each timestep and each rank, perform an ultra-fast pure binary copy. Instead of deserializing VTK objects, simply read `buffer_bytes = archive.get_data(rank_entry)` and write it directly to the new archive via `out_archive.write(cycle, time, buffer_bytes)`. Update cycle/time monotonically.

### Phase 14: Filtering Utility (`dpvtkfilter.py`) [COMPLETED]
- [x] **Task 14.1**: Create `scripts/dpvtkfilter.py` accepting an input `.dpvtk`, output `.dpvtk`, and a `--filter` argument (e.g., `slice` or `contour`).
- [x] **Task 14.2**: For each timestep, load the VTK dataset into a `TrivialProducer`.
- [x] **Task 14.3**: Apply the specified ParaView filter (e.g., `slice_filter = paraview.simple.Slice(Input=producer)`) and call `UpdatePipeline()`.
- [x] **Task 14.4**: Retrieve the filtered dataset (`GetClientSideObject().GetOutput()`), serialize it in-memory via `vtk_serializer.py`, and write it to the output `.dpvtk`.

### Phase 15: Validation & Diff Utility (`dpvtkdiff.py`) [COMPLETED]
- [x] **Task 15.1**: Create `scripts/dpvtkdiff.py` accepting two input `.dpvtk` files.
- [x] **Task 15.2**: Compare their metadata properties (e.g., number of timesteps, number of participating ranks, time values).
- [x] **Task 15.3**: Perform a rank-by-rank byte size comparison of the compressed payloads (`deflated_size`) to ensure the files are roughly or exactly identical.
- [x] **Task 15.4**: Report the exact differences or confirm they match.

### Phase 16: Video Encoding Utility (`dpvtkvideo.py`) [COMPLETED]
- [x] **Task 16.1**: Create `scripts/dpvtkvideo.py` as a wrapper that first executes `pvbatch scripts/dpvtkanimate.py ...` via `subprocess.run()`.
- [x] **Task 16.2**: After PNG frames are successfully generated, use `shutil.which("ffmpeg")` to check if FFmpeg is installed.
- [x] **Task 16.3**: If `ffmpeg` is available, invoke it (e.g., `ffmpeg -framerate 10 -i basename_%04d.png -c:v libx264 -pix_fmt yuv420p output.mp4`) to encode the frames into an MP4 video.
- [x] **Task 16.4**: If `ffmpeg` is *not* found, gracefully log a message explaining that frames were generated but video encoding was skipped.
- [x] **Task 16.5**: Add an optional `--keep-frames` flag to prevent the script from deleting the raw PNGs after successful encoding.

### Phase 17: Utility Integration Testing [COMPLETED]
- [x] **Task 17.1**: Create `scripts/tests/test_utilities.py` to hold automated test cases for the new ecosystem.
- [x] **Task 17.2**: Write a test for `dpvtkextract.py`. Assert that running it produces the expected `.vtm` and associated directory structures.
- [x] **Task 17.3**: Write a test for `dpvtksplice.py` and `dpvtkdiff.py`. Splice two copies of a small test archive together, then verify the output archive has double the timesteps. Use `dpvtkdiff.py` programmatically to compare two identical files and ensure it returns success.
- [x] **Task 17.4**: Write a test for `dpvtkfilter.py`. Execute a slice filter on a known dataset, and assert that the output `.dpvtk` is generated successfully and its file size is strictly smaller than the un-filtered input archive.
- [x] **Task 17.5**: Write a test for `dpvtkvideo.py` testing the generation wrapper (ensuring it runs gracefully regardless of whether `ffmpeg` is installed in the test environment).

### Phase 18: JSON Configuration for Rendering Utilities [COMPLETED]
- [x] **Task 18.1**: Update `dpvtkscreenshot.py` and `dpvtkanimate.py` to accept an optional `--config` argument that takes a path to a `.json` configuration file. Keep the input and output paths as positional arguments to preserve bash-scripting ease.
- [x] **Task 18.2**: If a config file is provided, parse it. Look for a `color_by` block specifying `"association"` (`POINTS` or `CELLS`), `"array_name"`, and optionally `"range_min"` and `"range_max"`.
- [x] **Task 18.3**: When creating the `Display` properties inside ParaView's Python API, if `color_by` is present, set `display.ColorArrayName = [config['color_by']['association'], config['color_by']['array_name']]`.
- [x] **Task 18.4**: Fetch the Color Transfer Function (LUT) via `paraview.simple.GetColorTransferFunction()`. If `range_min` and `range_max` are specified in the JSON, apply them using `lut.RescaleTransferFunction(min, max)`.
- [x] **Task 18.5**: Create a sample JSON configuration file (`sample_render_config.json`) in the project repository to serve as a template.

### Phase 19: Deep Inspection Utility (`dpvtkprobe.py`) [COMPLETED]
- [x] **Task 19.1**: Create `scripts/dpvtkprobe.py` accepting an input `.dpvtk` file and an optional `--timestep` argument (defaulting to 0).
- [x] **Task 19.2**: Use round-robin logic to load block chunks for the specified timestep across the executing MPI ranks.
- [x] **Task 19.3**: Iterate through each local `vtkDataSet`. Use `GetPointData()`, `GetCellData()`, and `GetFieldData()` to extract the names of all arrays present and store them in local Python `set()`s.
- [x] **Task 19.4**: Use `MPI.COMM_WORLD.reduce` with a set union operator to gather all array names from all ranks into a master set on Rank 0.
- [x] **Task 19.5**: Have Rank 0 print a clean, consolidated console output of available Point, Cell, and Field (Global) data arrays.
- [x] **Task 19.6**: Add a test in `scripts/tests/test_utilities.py` ensuring the script runs without errors and correctly identifies expected arrays.

### Phase 20: MPI Environment Inspector Utility (`dpvtkmpiinfo.py`) [COMPLETED]
- [x] **Task 20.1**: Create `scripts/dpvtkmpiinfo.py` accepting a single argument: the path to a `pvbatch` executable (e.g., `./paraview_v610/bin/pvbatch`).
- [x] **Task 20.2**: The script should use `subprocess` to execute `ldd <pvbatch_path>` and parse the output to locate the linked MPI shared library (e.g., `libmpi.so`).
- [x] **Task 20.3**: Identify the MPI flavor (e.g., MPICH, OpenMPI, Intel MPI) based on the library name (e.g., `libmpi.so.12` vs `libmpi.so.40`) or path heuristics.
- [x] **Task 20.4**: Determine the base installation prefix for the MPI runtime by resolving the library's path (e.g., stripping `lib/...` or `lib64/...` from the directory structure) and format it as a valid `CMAKE_PREFIX_PATH` that can be fed into CMake to guarantee ABI compatibility with ParaView.
- [x] **Task 20.5**: Print a concise, human-readable summary to the console detailing the discovered MPI flavor, the absolute path to the loaded library, and the recommended `CMAKE_PREFIX_PATH`.

---

## 5. Instructions to Redo Work From Scratch

To recreate the entire project environment on a fresh machine/container, it is **critical** to use the correct MPI environment. ParaView's pre-compiled binaries ship with their own embedded MPI runtime. If you compile `pydpvz` against a different MPI (e.g., building against OpenMPI when ParaView uses MPICH), you will get crashes, hangs, or `suspicious MPI execution environment` warnings.

**How to determine your MPI version:**
Run the setup script (`./scripts/setup_paraview.sh`). At the end, it will run `ldd path/to/pvbatch | grep mpi` and output the linked library (e.g., `libmpi.so.12` often indicates MPICH, `libmpi.so.40` often indicates OpenMPI).
* If MPICH: Use `mpicxx.mpich` and `mpicc.mpich`.
* If OpenMPI: Use `mpicxx.openmpi` and `mpicc.openmpi`.
*(The examples below assume MPICH. Adjust accordingly!)*

1. **Clone Core C++ Repository & Build Parallel Library via CMake**:
   Note: Upstream `dpvz` omits internal test directories (`tests/mpi`, `tests/ser`) in its public repo. To build cleanly with CMake without crashing on those missing directories, pass `-DDPVZ_TEST_MPI=OFF -DDPVZ_TEST_SERIAL=OFF`:
   ```bash
   git clone https://github.com/sandialabs/dpvz.git dpvz
   cd dpvz
   # Configure with CMake with test targets disabled and appropriate MPI compilers
   cmake -B build -S . -DCMAKE_BUILD_TYPE=Release -DDPVZ_MPI=ON -DDPVZ_SERIAL=OFF -DDPVZ_TEST_MPI=OFF -DDPVZ_TEST_SERIAL=OFF -DMPI_C_COMPILER=mpicc.mpich -DMPI_CXX_COMPILER=mpicxx.mpich
   # Build parallel library
   cmake --build build -j
   ```

2. **Setup Standalone `pydpvz` Package & Run Package Unit Tests**:
   ```bash
   cd ../pydpvz
   # Ensure CC/CXX point to the correct MPI wrapper to prevent mixing
   CC=mpicc.mpich CXX=mpicxx.mpich pip install -e .
   pytest tests/test_serial_io.py
   mpiexec.mpich -n 2 python3 -m pytest tests/test_mpi_io.py
   ```

3. **Download & Configure ParaView 6.1.0**:
   ```bash
   cd /workspaces/AllVibesDemo
   chmod +x ./scripts/setup_paraview.sh
   ./scripts/setup_paraview.sh
   ```

4. **Run Conversion Scripts & Integration Tests Against Sample Data**:
   ```bash
   # Source the environment variables
   source /workspaces/AllVibesDemo/scripts/setup_env.sh

   # Run automated integration test suite
   # Note: Integration tests internally use mpiexec.mpich -np 4 ./paraview_v610/bin/pvbatch --sym
   # The conversion scripts now automatically loop through and extract ALL timesteps from the input datasets.
   python3 -m pytest scripts/tests/
   ```

5. **Generate Screenshots**:
   ```bash
   # Source the environment variables
   source /workspaces/AllVibesDemo/scripts/setup_env.sh
   
   # Use pvbatch to load a .dpvtk file and generate a screenshot (requires --mesa for off-screen rendering)
   # Includes optional --viewdirection argument
   ./paraview_v610/bin/pvbatch --mesa scripts/dpvtkscreenshot.py output_can_ex.dpvtk screenshot_output.png --viewdirection "[0, 0, -1]"
   ```

6. **Inspect Archive Metadata**:
   ```bash
   # Source the environment variables
   source /workspaces/AllVibesDemo/scripts/setup_env.sh
   
   # Use standard python3 to rapidly inspect the metadata of a .dpvtk file without loading bulk data
   python3 scripts/dpvtkinfo.py output_can_ex.dpvtk
   ```

> **Critical Note on `pvbatch` and Deadlocks**: When running a Python script via `pvbatch` in parallel that executes collective MPI operations (like our `dpvz.write(comm)`), you **MUST** pass the `--sym` flag to `pvbatch` (Symmetric Mode). Without `--sym`, ParaView defaults to asymmetric client-server mode, meaning the Python script only executes on Rank 0, and Ranks 1+ sit idle in a C++ event loop. Rank 0 will hit the `archive.write()` barrier and deadlock forever waiting for the other ranks.

> **Critical Note on Data Distribution during Read**: When writing utilities that read from `.dpvtk` archives (`dpvz.Archive.read_timestep()`), it is absolutely crucial to use a round-robin distribution to map written partitions to the currently available reading ranks. If you only read `step_toc[rank]`, you will fail to load all data blocks when reading an N-rank dataset on M-ranks (where `M < N`). Always loop via `for w_rank in range(rank, entry.ranks, size):` and append each loaded dataset partition to the local `vtkPartitionedDataSetCollection` using a monotonically incrementing local partition index.

### Phase 21: Add Spack YAML Snippet Output to `dpvtkmpiinfo.py` [COMPLETED]
- [x] **Task 21.1**: Open `scripts/dpvtkmpiinfo.py` and locate the end of the `get_mpi_info()` function, just after it prints the MPI Environment Inspector summary.
- [x] **Task 21.2**: Determine the appropriate Spack package name based on the detected `flavor`. E.g.:
  - `MPICH` -> `mpich`
  - `OpenMPI` -> `openmpi`
  - `Intel MPI` -> `intel-mpi`
  - Otherwise, default to `mpi`.
- [x] **Task 21.3**: Add print statements to output a YAML snippet formatted for a `spack.yaml` `packages:` section. The snippet must include `buildable: false`, `externals:`, and map the `spec` to the Spack package name and the `prefix` to the `prefix_path` already detected by the script. Example output to print:
  ```yaml
  --- Spack External Package Snippet ---
    packages:
      mpich:
        buildable: false
        externals:
        - spec: mpich
          prefix: /path/to/mpi
  --------------------------------------
  ```
- [x] **Task 21.4**: Run `python3 scripts/dpvtkmpiinfo.py ./paraview_v610/bin/pvbatch` to test that the snippet prints correctly and incorporates the detected paths.

### Phase 22: Create Custom Spack Repository for `py-dpvz` [COMPLETED]
- [x] **Task 22.1**: Create the custom Spack repository directory structure: `spack-repo/packages/py-dpvz`.
- [x] **Task 22.2**: Create `spack-repo/repo.yaml` with the following content to initialize the repository:
  ```yaml
  repo:
    namespace: custom_pydpvz
  ```
- [x] **Task 22.3**: Create `spack-repo/packages/py-dpvz/package.py` and implement the `PyDpvz` class inheriting from `PythonPackage`.
  - Include the standard Spack import (`from spack.package import *`).
  - Set `homepage` and a default `git` URL pointing to the remote repository (e.g., `git = "https://github.com/sandialabs/pydpvz.git"`).
  - Add a clearly documented fallback to support local installation for iterative development (e.g., `# git = f"file://{os.path.abspath(os.path.dirname(__file__))}/../../../"`).
  - Define `version('main', branch='main')`.
  - Define the required dependencies:
    - `depends_on("python@3.8:", type=("build", "run"))`
    - `depends_on("py-setuptools", type="build")`
    - `depends_on("py-pybind11", type=("build", "link", "run"))`
    - `depends_on("cmake", type="build")`
    - `depends_on("mpi")`
- [x] **Task 22.4**: Create a documentation file `spack-repo/README.md` detailing the two target workflows:
  - **Workflow A (External MPI)**: Explain how to run `dpvtkmpiinfo.py`, paste the snippet into `spack.yaml` under `packages:`, run `spack repo add ./spack-repo`, and execute `spack install py-dpvz`.
  - **Workflow B (Existing ParaView Env)**: Explain how to run `spack repo add ./spack-repo` inside an existing Spack environment containing ParaView, and then execute `spack install py-dpvz`.
  - **Local Development**: Explain how to swap the `git` URL in `package.py` to the `file://` URL for local iterative testing.

### Phase 23: Create ParaView Python Algorithm Writer Plugin [COMPLETED]
- [x] **Task 23.1**: Create `scripts/dpvtk_writer_plugin.py` integrating with `paraview.util.vtkAlgorithm`.
  - Define a class inheriting from `VTKPythonAlgorithmBase`.
  - Decorate the class with `@smproxy.writer(name="DPvtkWriter", extensions="dpvtk", file_description="DPvtk Archive", support_reload=False)`.
  - Decorate the input method with `@smproperty.input(name="Input")` and `@smdomain.datatype(dataTypes=["vtkPartitionedDataSetCollection", "vtkMultiBlockDataSet"])`.
  - Decorate a method to accept a string for the `FileName` property.
- [x] **Task 23.2**: Implement the `RequestData` pipeline method in the plugin to handle the MPI write:
  - Fetch the local `vtkDataObject` from the pipeline.
  - Determine the current timestep from the pipeline executive (`outInfo.Get(vtkDataObject.DATA_TIME_STEP())`). Keep track of an internal step counter (`self._cycle`) or deduce it.
  - Instantiate `comm = mpi4py.MPI.COMM_WORLD`.
  - Serialize the geometry using `pydpvz.vtk_serializer`.
  - Use `pydpvz.DPvzVtk` to execute the collective MPI write operation. *Note: Ensure the file is created (`DPvzReplace`) on the first timestep of the pipeline execution, and appended (`DPvzReadWrite`) for subsequent timesteps in the loop.*
- [x] **Task 23.3**: Create an integration test script `scripts/convert_with_plugin.py` to replace legacy scripts:
  - Load the newly created plugin using `paraview.servermanager.LoadPlugin()`.
  - Use `glob` and `OpenDataFile(file_list)` to automatically handle `.vtpc` file series.
  - Invoke `SaveData("output.dpvtk", proxy=reader, WriteAllTimeSteps=1)` to automatically drive the time loop, completely replacing the old manual orchestration.
- [x] **Task 23.4**: Document execution instructions within `convert_with_plugin.py`:
  - Explicitly document that the script should be run via `mpiexec -np 4 pvbatch --sym scripts/convert_with_plugin.py` to ensure symmetric MPI orchestration still functions seamlessly.

### Phase 24: Unified Converter Cleanup [COMPLETED]
- [x] **Task 24.1**: Rename and Polish `dpvtkconvert.py`.
  - Rename `scripts/convert_with_plugin.py` to `scripts/dpvtkconvert.py`.
  - Introduce `argparse` to handle `--input` (allowing glob patterns) and `--output`.
  - Keep the explicit proxy instantiation (`DPvtkWriter`) and manual time loop, but add user-friendly logging inside the loop (e.g., `[Rank 0] Processing timestep X...`).
- [x] **Task 24.2**: Remove Legacy Scripts.
  - Delete `scripts/convertvtpcscript1.py` and `scripts/converttpcsscript1.py`.
  - Delete any legacy dependencies in those scripts if they are no longer used anywhere else.
- [x] **Task 24.3**: Update Documentation.
  - Scan the repository (including `PLAN.md`) for references to the legacy convert scripts and replace them with `dpvtkconvert.py`.

### Phase 25: Codebase Documentation [COMPLETED]
- [x] **Task 25.1**: Add comprehensive docstrings to the `scripts/` folder.
  - Update all ParaView utility scripts (`dpvtkconvert.py`, `dpvtkscreenshot.py`, `dpvtkanimate.py`, `dpvtkextract.py`, etc.) with module-level, class-level, and function-level docstrings.
  - Ensure docstrings explain the required MPI execution context (e.g., symmetric mode requirements) and VTK pipeline integration.
- [x] **Task 25.2**: Add comprehensive docstrings to the `pydpvz/` folder.
  - Update the Python wrapper files (`vtk_serializer.py`, etc.) with detailed docstrings explaining the serialization logic, MPI rank chunking, and PyBind11 C++ integration.

### Phase 26: Sphinx / Read the Docs Website Implementation [COMPLETED]
- [x] **Task 26.1**: Initialize Sphinx documentation in a new `docs/` folder. Configure `conf.py` to use `sphinx_rtd_theme` (for the classic look) and `myst-parser` (for Markdown support).
- [x] **Task 26.2**: Configure Sphinx `autodoc` by ensuring the compiled `pydpvz` module is in the Sphinx Python path. Add any necessary MPI mocking/stubbing if Sphinx builds the docs in an environment without ParaView/MPI.
- [x] **Task 26.3**: Write the Core API documentation pages. Create `api.md` that uses `autodoc` directives to automatically extract and format the C++ docstrings from Pybind11 (e.g., `DPvzFile`, `DPvzVtk`, `DPvzMode`).
- [x] **Task 26.4**: Write Utility and Examples documentation. Integrate existing script usage guides (e.g., `dpvtkscreenshot.py`), CMake, and Spack instructions into structured Markdown pages.
- [x] **Task 26.5**: Create a GitHub Actions workflow `.github/workflows/docs.yml` that automatically installs dependencies, builds the Sphinx HTML, and deploys it to the `gh-pages` branch whenever code is pushed to `main`.

### Phase 27: Parallel Extent Partitioning & Dataset Hierarchy Preservation [COMPLETED]
- [x] **Task 27.1**: Fix parallel redundant dataset writing in `DPvtkWriter` plugin by implementing `RequestUpdateExtent` (`UPDATE_PIECE_NUMBER` and `UPDATE_NUMBER_OF_PIECES`) so each MPI rank only writes its local domain piece.
- [x] **Task 27.2**: Preserve dataset hierarchy and block metadata in `pydpvz.vtk_serializer` via `extract_hierarchy_and_blocks()`, embedding a `<FILE NAME='hierarchy.json'>` metadata record in the archive stream to maintain structure without storing empty partition grids.
- [x] **Task 27.3**: Update `pydpvz.vtk_deserializer` and all ParaView reading utilities to reconstruct block indices, block names, and non-empty geometries into native `vtkPartitionedDataSetCollection` objects during read operations.

### Phase 28: vtkDataAssembly Hierarchy Preservation & Environment ABI Inspection [COMPLETED]
- [x] **Task 28.1**: Expand `pydpvz.vtk_serializer` and `pydpvz.vtk_deserializer` (`populate_pdc_from_buffer`) to capture and restore the full XML representation of any external `vtkDataAssembly` tree attached to composite datasets.
- [x] **Task 28.2**: Modernize all reading utilities (`dpvtkextract.py`, `dpvtkscreenshot.py`, etc.) to invoke `populate_pdc_from_buffer`, guaranteeing unified hierarchy and assembly recovery without manual loop indexing errors.
- [x] **Task 28.3**: Expand `scripts/dpvtkmpiinfo.py` to inspect `pvbatch` binaries and linked shared libraries to determine both the MPI runtime flavor and the exact Python major/minor ABI version embedded within ParaView.

### Phase 29: Create ParaView Python Algorithm Reader Plugin [COMPLETED]
- [x] **Task 29.1**: Create `scripts/dpvtk_reader_plugin.py` using `paraview.util.vtkAlgorithm`.
  - Implement a `VTKPythonAlgorithmBase` reader subclass decorated with `@smproxy.reader` to bind to ParaView's **File -> Open** filechooser dialog for `.dpvtk` archives.
  - Implement `RequestInformation` to query archive time map vectors and populate ParaView's streaming pipeline executive (`TIME_STEPS` and `TIME_RANGE`) to activate interactive GUI time sliders.
  - Implement `RequestData` to execute collective round-robin data extraction across all MPI ranks using `populate_pdc_from_buffer`, restoring partitioned simulation geometry and `vtkDataAssembly` component trees natively in memory.
- [x] **Task 29.2**: Add parallel automated verification testing (`test_reader_plugin`) to `scripts/tests/test_utilities.py` to ensure robust CI validation.
- [x] **Task 29.3**: Document GUI & Remote Client-Server execution workflows across `AGENTS.md`, `README.md`, and `docs/utilities.md`, ensuring HPC users know to load the reader plugin under **Remote Plugins** when connecting local desktops to remote `pvserver` cluster sessions.
