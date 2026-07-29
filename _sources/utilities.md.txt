# Utility Scripts

The `pydpvz` repository includes several Python utility scripts designed to be run within ParaView's `pvbatch` environment. 

## 1. Converter Utility (`dpvtkconvert.py`)
Converts standard ParaView formats (`.vtpc`, `.ex2`, `.vtm`) into highly compressed, parallel `.dpvtk` archives.

**Usage:**
```bash
mpiexec -np 4 pvbatch --sym scripts/dpvtkconvert.py --input sample_data/can.ex2 --output output.dpvtk
```
*Note: Must be run with `--sym` (Symmetric Mode) to avoid MPI deadlocks.*

## 2. Screenshot Utility (`dpvtkscreenshot.py`)
Loads a `.dpvtk` file, applies a view direction, and renders a `.png` screenshot.

**Usage:**
```bash
./paraview_v610/bin/pvbatch --mesa scripts/dpvtkscreenshot.py output.dpvtk screenshot.png --viewdirection "[0, 0, -1]" --timestep 0
```

## 3. Animation Utility (`dpvtkanimate.py`)
Generates an image sequence for all timesteps in a `.dpvtk` archive.

**Usage:**
```bash
./paraview_v610/bin/pvbatch --mesa scripts/dpvtkanimate.py output.dpvtk frame_base --timesteprange "[0, 10]"
```

## 4. Metadata Inspector (`dpvtkinfo.py`)
Inspects a `.dpvtk` archive and prints its TOC metadata extremely quickly without loading the bulk data.

**Usage:**
```bash
python3 scripts/dpvtkinfo.py output.dpvtk
```
