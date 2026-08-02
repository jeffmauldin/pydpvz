# Utility Scripts

The `pydpvz` repository includes an expansive suite of Python utility scripts designed to be run within ParaView's parallel `pvbatch` environment. 

## 1. Universal Converter (`dpvtkconvert.py`)
Converts standard ParaView file series and simulation datasets (`.vtpc`, `.ex2`, `.vtm`, and `.vtu`) into highly compressed, parallel `.dpvtk` archives.
- **Parallel Piece Extents**: Actively synchronizes with upstream VTK pipeline readers (`RequestUpdateExtent`), ensuring each MPI rank requests and serializes only its unique spatial slice of the domain without redundant duplication.
- **Hierarchy Preservation**: Retains complete multi-block dataset structures and component names by embedding a lightweight `hierarchy.json` record into the archive stream.

**Usage:**
```bash
mpiexec -np 4 ./paraview_v610/bin/pvbatch --sym scripts/dpvtkconvert.py --input sample_data/can.ex2 --output output.dpvtk
```
*Note: Must be run with `--sym` (Symmetric Mode) to ensure collective MPI operations do not deadlock.*

## 2. Array & Geometry Probe Inspector (`dpvtkprobe.py`)
Interrogates point, cell, and field data arrays across all timesteps and MPI partitions in a `.dpvtk` archive, performing a collective MPI set union to report global data variables. It also analyzes overall dataset structure, gathering explicit cell and point geometry counts across each writing rank to identify workload distributions.

**Usage:**
```bash
mpiexec -np 4 ./paraview_v610/bin/pvbatch --sym scripts/dpvtkprobe.py output.dpvtk 0 [--verbose]
```

## 3. Screenshot Utility (`dpvtkscreenshot.py`)
Loads a `.dpvtk` file, reconstructs multi-block component hierarchies into a `vtkPartitionedDataSetCollection`, applies a camera look vector, and composites a high-resolution `.png` screenshot using parallel rendering.

**Usage:**
```bash
mpiexec -np 4 ./paraview_v610/bin/pvbatch --sym scripts/dpvtkscreenshot.py output.dpvtk screenshot.png --viewdirection "[0, 0, -1]" --timestep 0
```

## 4. Animation Utility (`dpvtkanimate.py`)
Generates an image sequence for all or specified timesteps in a `.dpvtk` archive, writing raw `.png` frames across the cluster.

**Usage:**
```bash
mpiexec -np 4 ./paraview_v610/bin/pvbatch --sym scripts/dpvtkanimate.py output.dpvtk frame_base --timesteprange "[0, 10]"
```

## 5. Video Generator (`dpvtkvideo.py`)
Wraps `dpvtkanimate.py` to produce frames in parallel, then seamlessly pipes them into **FFmpeg** on Rank 0 to output a final `.mp4` video file.

## 6. Parallel Pipeline Filter (`dpvtkfilter.py`)
Applies in-memory ParaView filter algorithms (such as `Slice` or `Contour`) across a distributed `.dpvtk` archive and streams the resulting modified geometries directly into a new compressed `.dpvtk` archive without intermediate files.

## 7. Dataset Extractor (`dpvtkextract.py`)
Unwraps a `.dpvtk` archive back into standard ParaView partitioned dataset collection files (`.vtpc` plus data pieces) for interoperability with external software.

## 8. Metadata Inspector (`dpvtkinfo.py`)
Reads an archive Table of Contents (TOC), step counts, and rank chunk byte-sizes almost instantaneously without loading bulk mesh data.

**Usage:**
```bash
PYTHONPATH=pydpvz python3 scripts/dpvtkinfo.py output.dpvtk
```

## 9. Environment ABI Inspector (`dpvtkmpiinfo.py`)
Dynamically queries a target `pvbatch` executable and its linked shared objects to deduce its exact **MPI runtime flavor** and **Python major/minor ABI version**. Outputs Spack YAML packages snippets to enforce exact external dependency matching when compiling `pydpvz` on strict HPC clusters.

**Usage:**
```bash
python3 scripts/dpvtkmpiinfo.py paraview_v610/bin/pvbatch
```
