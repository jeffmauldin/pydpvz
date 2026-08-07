# DPVTK Examples

This directory contains examples for how to use the various `dpvtk` tools in this repository.

These scripts assume that you have access to the sample `can` datasets, specifically:
- 4-process VTPC dataset (`../sample_data/can_data/can_data_4_process_vtpc/can_vtpc_*.vtpc`)
- 4-process Exodus dataset (`../sample_data/can_data/can_data_4_process_exodus/can.ex2.4*`)

*Note: Sample datasets are not included in the repository at this time.*

## Scripts

### 1. `run_convert_vtpc.sh`
Demonstrates how to run the `dpvtkconvert.py` utility to convert a set of partitioned VTK (.vtpc) files into a single `.dpvtk` archive. It uses MPI symmetric mode (`pvbatch --sym`) across 4 processes.

### 2. `run_convert_exodus.sh`
Demonstrates how to run the `dpvtkconvert.py` utility to convert a partitioned Exodus dataset into a `.dpvtk` archive.

### 3. `run_extract.sh`
Demonstrates how to run the `dpvtkextract.py` utility to extract the `.dpvtk` archives back into standard `.vtpc` files.

### 4. `run_info.sh`
Demonstrates how to run the `dpvtkinfo.py` utility. This utility inspects the metadata and table of contents of a `.dpvtk` archive (such as timesteps, bytes sizes) without loading the bulk payload data. It executes serially and is nearly instantaneous.

### 5. `run_probe.sh`
Demonstrates how to run the `dpvtkprobe.py` utility in MPI symmetric mode. It opens the `.dpvtk` archive and inspects actual geometry payloads, printing the cell and point array names and per-rank data limits.

### 6. `run_pvserver.sh`
Demonstrates how to launch a 4-process `pvserver` utilizing Mesa for off-screen rendering. You can run this script to host the datasets, and then connect to `localhost:11111` from an external ParaView GUI to visualize the datasets directly.

### 7. `run_convert_vtpc_2ranks.sh`
Demonstrates how to convert the 4-partition VTPC dataset into a `.dpvtk` archive using only 2 MPI ranks. This shows that the number of MPI ranks during write does not need to match the number of partitions in the dataset.

### 8. `run_convert_vtpc_1rank.sh`
Demonstrates how to convert the 4-partition VTPC dataset into a `.dpvtk` archive using a single serial process (no MPI, just `pvbatch`). This further illustrates that one process can aggregate and write all partitions into the archive.

## Usage
Run any script from this directory:
```bash
./run_convert_vtpc.sh
```
