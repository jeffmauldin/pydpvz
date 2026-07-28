# 🌊 pydpvz: Parallel VTK I/O Utilities

`pydpvz` provides a set of highly efficient, incredibly lightweight Python bindings and utilities for Sandia National Laboratories' [**dpvz**](https://github.com/sandialabs/dpvz) parallel I/O C++ library. 

It is designed to bridge the gap between `dpvz` and **ParaView**, allowing you to serialize and deserialize massive partitioned VTK datasets (`.vtpc`, `.vtm`, `.ex2`) directly to and from single-file compressed `.dpvtk` archives in parallel, without overwhelming your parallel file system metadata servers (MDTs/OSTs).

---

## 🧰 The ParaView Utility Suite

This repository includes a suite of battle-tested Python scripts located in the `scripts/` directory. They are designed to be run in a parallel `pvbatch` environment, and they leverage a robust round-robin mapping architecture so that an archive written by 1,000 ranks can be effortlessly read, filtered, or rendered on just 16 ranks (or vice versa).

| Utility | Description |
|---|---|
| **`dpvtkinfo.py`** | Extremely fast metadata reporter. Instantly reads archive Table of Contents (TOC), step counts, and rank chunk byte-sizes without touching bulk geometry data. |
| **`dpvtkscreenshot.py`** | A parallel renderer that loads a specific timestep from a `.dpvtk` archive, configures the camera, and composites a high-resolution `.png` image using IceT. |
| **`dpvtkanimate.py`** | Loads a range of timesteps and parallel-renders a sequence of raw `.png` frames. |
| **`dpvtkvideo.py`** | A wrapper for `dpvtkanimate.py` that seamlessly pipes the generated frames into **FFmpeg** to output a high-quality `.mp4` video file. |
| **`dpvtkfilter.py`** | In-memory parallel pipeline. Applies ParaView algorithms (like `Slice` or `Contour`) to a dataset and streams the filtered geometry directly into a *new* compressed `.dpvtk` archive. |
| **`dpvtkextract.py`** | Parallel extractor that unwraps a `.dpvtk` archive back into raw, standard `.vtpc` and piece files for external tooling. |
| **`dpvtksplice.py`** | Ultra-fast binary concatenator. Splices multiple `.dpvtk` chunks into a single unified archive purely through raw byte-copying (bypassing VTK entirely). |
| **`dpvtkdiff.py`** | Performs a metadata and compressed-byte-size rank-by-rank comparison of two `.dpvtk` archives to verify integrity. |

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

---

## 🤖 For AI Agents & Core Developers

If you are an AI coding assistant (or a human developer) invoked to extend or debug this project, **STOP** and read the following documents before writing any code:

1. [**`AGENTS.md`**](./AGENTS.md): The critical context sheet. It explains the catastrophic `pvbatch --sym` deadlock trap, the round-robin chunk mapping constraints, and pipeline architecture requirements.
2. [**`PLAN.md`**](./PLAN.md): The master architectural diary and execution plan. It tracks the history of all design decisions and contains rigorous step-by-step instructions.

---
## 📄 License
[MIT](./LICENSE) © 2026 Wyatt Horne.