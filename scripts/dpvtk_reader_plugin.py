"""
ParaView Python Algorithm Plugin for reading .dpvtk archives natively.

This module defines a `VTKPythonAlgorithmBase` subclass decorated with ServerManager 
proxies (`@smproxy.reader`) to integrate seamlessly into ParaView's File -> Open dialogs,
pipeline execution, and interactive time sliders.

It intercepts read requests, advertises available simulation timestamps via `RequestInformation`,
and executes a parallel round-robin chunk distribution loop in `RequestData` using `pydpvz.DPvzVtk`
and `pydpvz.vtk_deserializer.populate_pdc_from_buffer`, restoring both distributed geometry blocks 
and any associated `vtkDataAssembly` hierarchical structures.

Execution Context:
Designed to operate inside ParaView GUI sessions (via `pvserver`) or batch pipelines (`pvbatch --sym`).
"""

import os
from paraview.util.vtkAlgorithm import *
import vtk

print("--- DPvtkReader Plugin is being parsed by ParaView! ---")

@smproxy.reader(name="DPvtkReader", label="DPVZ Archive Reader", extensions="dpvtk", file_description="DPVZ Parallel Archives")
class DPvtkReader(VTKPythonAlgorithmBase):
    """
    A ParaView reader plugin that deserializes parallel .dpvtk archives directly into a
    vtkPartitionedDataSetCollection, preserving block names and vtkDataAssembly hierarchies.
    """
    def __init__(self):
        super().__init__(nInputPorts=0, nOutputPorts=1, outputType="vtkPartitionedDataSetCollection")
        self._filename = ""
        self._timesteps = None
        self._time_map = None

    @smproperty.stringvector(name="FileName", label="File Name", default_values="", panel_visibility="never")
    @smdomain.filelist()
    @smhint.filechooser(extensions="dpvtk", file_description="DPVZ Parallel Archives")
    def SetFileName(self, filename):
        if self._filename != filename:
            self._filename = filename
            self._timesteps = None
            self._time_map = None
            self.Modified()

    def _inspect_archive(self):
        """
        Opens the archive to read time step metadata if not already populated.
        """
        if self._timesteps is not None:
            return

        if not self._filename or not os.path.exists(self._filename):
            self._timesteps = [0.0]
            return

        try:
            from mpi4py import MPI
            import pydpvz
            comm = MPI.COMM_WORLD
            archive = pydpvz.DPvzVtk(self._filename, pydpvz.DPvzMode.DPvzReadOnly, comm, False)
            steps = archive.get_steps()
            if steps > 0:
                map_vec = archive.get_map()
                self._timesteps = [float(entry.time) for entry in map_vec]
                # Ensure monotonic unique timesteps if timestamps happen to be flat
                if len(set(self._timesteps)) != len(self._timesteps):
                    self._timesteps = [float(i) for i in range(steps)]
            else:
                self._timesteps = [0.0]
        except Exception as e:
            print(f"DPvtkReader check failed on {self._filename}: {e}")
            self._timesteps = [0.0]

    @smproperty.doublevector(name="TimestepValues", information_only="1", si_class="vtkSITimeStepsProperty")
    def GetTimestepValues(self):
        self._inspect_archive()
        return self._timesteps if self._timesteps else [0.0]

    def RequestInformation(self, request, inInfo, outInfo):
        """
        Advertises the available simulation timestamps and time range to ParaView's pipeline executive.
        """
        self._inspect_archive()
        info = outInfo.GetInformationObject(0)
        
        info.Remove(vtk.vtkStreamingDemandDrivenPipeline.TIME_STEPS())
        for t in self._timesteps:
            info.Append(vtk.vtkStreamingDemandDrivenPipeline.TIME_STEPS(), t)
            
        if self._timesteps and len(self._timesteps) > 0:
            info.Set(vtk.vtkStreamingDemandDrivenPipeline.TIME_RANGE(), [self._timesteps[0], self._timesteps[-1]], 2)
            
        return 1

    def RequestData(self, request, inInfo, outInfo):
        """
        Executes parallel reading and round-robin distribution of archive partitions for the requested timestamp.
        """
        output = vtk.vtkPartitionedDataSetCollection.GetData(outInfo)
        info = outInfo.GetInformationObject(0)

        if not self._filename or not os.path.exists(self._filename):
            return 1

        req_time = self._timesteps[0] if self._timesteps else 0.0
        if info.Has(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP()):
            req_time = info.Get(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP())

        # Match req_time to closest available timestep index
        timestep_idx = 0
        if self._timesteps and len(self._timesteps) > 1:
            timestep_idx = min(range(len(self._timesteps)), key=lambda i: abs(self._timesteps[i] - req_time))

        from mpi4py import MPI
        import pydpvz
        from pydpvz.vtk_deserializer import populate_pdc_from_buffer

        comm = MPI.COMM_WORLD
        rank = comm.Get_rank()
        size = comm.Get_size()

        archive = pydpvz.DPvzVtk(self._filename, pydpvz.DPvzMode.DPvzReadOnly, comm, False)
        steps = archive.get_steps()
        if timestep_idx >= steps:
            timestep_idx = steps - 1

        map_vec = archive.get_map()
        entry = map_vec[timestep_idx]
        step_toc = archive.get_step_toc(entry)

        # Round-robin partition extraction and vtkDataAssembly reconstruction
        part_counters = {}
        for w_rank in range(rank, entry.ranks, size):
            rank_entry = step_toc[w_rank]
            buffer_bytes = archive.get_data(rank_entry)
            populate_pdc_from_buffer(output, buffer_bytes, part_counters)

        return 1
