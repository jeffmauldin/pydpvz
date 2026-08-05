# 🌊 pydpvz: Parallel VTK I/O Utilities

`pydpvz` provides a set of highly efficient, incredibly lightweight Python bindings and utilities for Sandia National Laboratories' [**dpvz**](https://github.com/sandialabs/dpvz) parallel I/O C++ library. 

It is designed to bridge the gap between `dpvz` and **ParaView**, allowing you to serialize and deserialize massive partitioned VTK datasets (`.vtpc`, `.vtm`, `.ex2`) directly to and from single-file compressed `.dpvtk` archives in parallel, without overwhelming your parallel file system metadata servers (MDTs/OSTs).

---

## 🧰 The ParaView Utility Suite

This repository includes a suite of battle-tested Python scripts located in the `scripts/` directory. They are designed to be run in a parallel `pvbatch` environment, and they leverage a robust round-robin mapping architecture so that an archive written by 1,000 ranks can be effortlessly read, filtered, or rendered on just 16 ranks (or vice versa).

| Utility | Description |
|---|---|
| **`dpvtkconvert.py`** | Universal parallel converter. Transforms multi-block (`.vtm`), partitioned dataset collections (`.vtpc`), and Exodus II (`.ex2`) files into compressed `.dpvtk` archives while preserving exact dataset hierarchy and time step values. |
| **`dpvtkinfo.py`** | Extremely fast metadata reporter. Instantly reads archive Table of Contents (TOC), step counts, and rank chunk byte-sizes without touching bulk geometry data. |
| **`dpvtkprobe.py`** | Parallel array inspection tool. Interrogates point, cell, and field data arrays inside a `.dpvtk` archive across all MPI ranks using custom set union reductions. |
| **`dpvtkscreenshot.py`** | A parallel renderer that loads a specific timestep from a `.dpvtk` archive, configures the camera, and composites a high-resolution `.png` image using IceT. |
| **`dpvtkanimate.py`** | Loads a range of timesteps and parallel-renders a sequence of raw `.png` frames. |
| **`dpvtkvideo.py`** | A wrapper for `dpvtkanimate.py` that seamlessly pipes the generated frames into **FFmpeg** to output a high-quality `.mp4` video file. |
| **`dpvtkfilter.py`** | In-memory parallel pipeline. Applies ParaView algorithms (like `Slice` or `Contour`) to a dataset and streams the filtered geometry directly into a *new* compressed `.dpvtk` archive. |
| **`dpvtkextract.py`** | Parallel extractor that unwraps a `.dpvtk` archive back into raw, standard `.vtpc` and piece files for external tooling. |
| **`dpvtksplice.py`** | Ultra-fast binary concatenator. Splices multiple `.dpvtk` chunks into a single unified archive purely through raw byte-copying (bypassing VTK entirely). |
| **`dpvtkdiff.py`** | Performs a metadata and compressed-byte-size rank-by-rank comparison of two `.dpvtk` archives to verify integrity. |
| **`dpvtkmpiinfo.py`** | Environment inspector. Dynamically queries `pvbatch` and its libraries to deduce its exact **MPI flavor** and **Python ABI version** to ensure compilation compatibility. |
| **`dpvtk_reader_plugin.py`** | ParaView Python Reader Plugin. Seamlessly integrates with ParaView GUI's **File -> Open** dialog and pipeline executive to read parallel `.dpvtk` archives, populating interactive time sliders and reconstructing `vtkDataAssembly` trees. |
| **`dpvtk_writer_plugin.py`** | ParaView Python Writer Plugin. Integrates with ParaView pipeline sinks and **Save Data** workflows to compress and write parallel `.dpvtk` archives without redundant data duplication. |

---

## 🏛️ Core Architectural Highlights

- **True Parallel Domain Partitioning**: Custom writer plugins (`DPvtkWriter`) actively coordinate with ParaView's streaming pipeline executives via `RequestUpdateExtent`. In multi-process MPI executions, each process sets its piece number and total pieces on upstream filters, ensuring every rank serializes only its partitioned slice of the simulation domain with **zero data duplication**.
- **Dataset Hierarchy & DataAssembly Preservation**: Rather than flattening multi-block (`.vtm`) or partitioned dataset collections (`.vtpc`), `pydpvz` extracts top-level block structures and block names, embedding a lightweight `hierarchy.json` record directly into the archive stream. If a `.vtpc` dataset contains an external **`vtkDataAssembly`** DOM tree (e.g. `Vehicle -> Engine -> Cylinder`), it automatically serializes the XML assembly string directly into the metadata stream. When reading an archive, ParaView natively rebuilds the complete `vtkPartitionedDataSetCollection` and structurally re-attaches the DOM assembly tree exactly as it was, even across MPI ranks where specific local blocks contain zero geometry cells.

---

## ⚡ Lightweight by Design

This project prides itself on maintaining an incredibly minimal dependency tree:
- **No** `HDF5`, `PnetCDF`, `ADIOS`, or `NumPy`.
- The core C++ library only requires **MPI** and **zlib**.
- The Python wrappers only require **`mpi4py`**. 
- The utilities run entirely inside standard ParaView.

---

## 🛠️ Quick Start & Installation

To recreate this environment on your own cluster or container, you must build `dpvz` and `pydpvz` against the **exact same MPI library** that your ParaView installation uses (e.g., MPICH vs OpenMPI).

1. **Setup ParaView and Detect MPI**:
   ```bash
   chmod +x ./scripts/setup_paraview.sh
   ./scripts/setup_paraview.sh
   ```
   *At the end of the script, it will scan `pvbatch` and tell you whether to use `mpicxx.mpich` or `mpicxx.openmpi` in the following steps.*

2. **Build the C++ Core (`dpvz`)**:
   ```bash
   git clone https://github.com/sandialabs/dpvz.git dpvz
   cd dpvz/src
   
   # Use the MPI wrapper detected in Step 1 (e.g., mpicxx.mpich)
   mpicxx.mpich -DDPVZ_MPI -Wall -O3 -shared -fPIC -o libDPvzMpi.so *.C -lz
   mpicxx.mpich -DDPVZ_MPI -Wall -O3 -o ../utils/dpvtk-ar-ser ../utils/dpvtk-ar.C -L. -lDPvzMpi -lz
   ```

3. **Install the Python Wrappers (`pydpvz`)**:
   ```bash
   cd ../../pydpvz
   
   # Export the same MPI wrappers
   CC=mpicc.mpich CXX=mpicxx.mpich pip install -e .
   ```

4. **Source the Environment**:
   ```bash
   source scripts/setup_env.sh
   ```
   You are now ready to run `pvbatch --sym scripts/dpvtkscreenshot.py ...`

5. **Using the ParaView Reader Plugin in HPC & Remote Client-Server Setups**:
   To interactively view `.dpvtk` parallel archives inside the ParaView GUI when connecting a local laptop client to a remote HPC container or cluster running `pvserver`:
   - Launch your remote `pvserver` session (with `setup_env.sh` sourced).
   - In your local desktop ParaView GUI, connect to the remote server via **File -> Connect...**.
   - Navigate to **Tools -> Manage Plugins...**.
   - Under **Remote Plugins**, select **Load New...** and choose [`scripts/dpvtk_reader_plugin.py`](./scripts/dpvtk_reader_plugin.py) from the remote cluster filesystem.
   - *Note*: You only need to load the plugin on the **Remote** side! ParaView will automatically push the GUI reader definitions across the network to your local laptop client, allowing you to use **File -> Open** and interactive Time Sliders without needing `pydpvz` built locally on your laptop.

---

## 🤖 For AI Agents & Core Developers

If you are an AI coding assistant (or a human developer) invoked to extend or debug this project, **STOP** and read the following documents before writing any code:

1. [**`AGENTS.md`**](./AGENTS.md): The critical context sheet. It explains the catastrophic `pvbatch --sym` deadlock trap, the round-robin chunk mapping constraints, and pipeline architecture requirements.
2. [**`PLAN.md`**](./PLAN.md): The master architectural diary and execution plan. It tracks the history of all design decisions and contains rigorous step-by-step instructions.

---
## 📄 License
[MIT](./LICENSE) © 2026 Wyatt Horne.