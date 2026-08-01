"""
ParaView Python Algorithm Plugin for writing .dpvtk archives natively.

This module defines a `VTKPythonAlgorithmBase` subclass decorated with ServerManager 
proxies (`@smproxy.writer`) to seamlessly integrate with ParaView's pipeline and `SaveData` operations.
It intercepts VTK composite datasets (`vtkPartitionedDataSetCollection` or `vtkMultiBlockDataSet`),
delegates the XML serialization to `pydpvz.vtk_serializer`, and executes a collective MPI write 
using `pydpvz.DPvzVtk`.

Execution Context:
Must be executed in ParaView Symmetric MPI mode (`pvbatch --sym`) for true parallel I/O.
"""

from paraview.util.vtkAlgorithm import *
import vtk

print("--- DPvtkWriter Plugin is being parsed by ParaView! ---")

@smproxy.writer(name="DPvtkWriter", extensions="dpvtk", file_description="DPvtk Archive", support_reload=False)
@smproperty.input(name="Input", port_index=0)
@smdomain.datatype(dataTypes=["vtkPartitionedDataSetCollection", "vtkMultiBlockDataSet", "vtkDataSet"], composite_data_supported=True)
class DPvtkWriter(VTKPythonAlgorithmBase):
    """
    A ParaView writer plugin that serializes distributed VTK pipelines into .dpvtk archives.
    Registers itself as the 'DPvtkWriter' proxy for the '.dpvtk' extension.
    """
    def __init__(self):
        super().__init__(nInputPorts=1, nOutputPorts=0, inputType="vtkDataObject")
        self._filename = None
        self._write_all_time_steps = 0
        self._cycle = 0
        self._time = None

    @smproperty.doublevector(name="Time", default_values=-1e30)
    def SetTime(self, time):
        if self._time != time:
            self._time = time
            self.Modified()

    @smproperty.intvector(name="WriteAllTimeSteps", default_values=0)
    @smdomain.xml('<BooleanDomain name="bool" />')
    def SetWriteAllTimeSteps(self, write_all):
        self._write_all_time_steps = write_all
        self.Modified()

    def Write(self):
        """
        Triggers the execution of the pipeline, which in turn calls RequestData.
        This is required for compatibility with ParaView's vtkAlgorithm execution flow.
        """
        self.Modified()
        self.Update()

    @smproperty.stringvector(name="FileName", panel_visibility="never")
    @smdomain.filelist()
    def SetFileName(self, filename):
        if self._filename != filename:
            self._filename = filename
            self.Modified()

    def RequestUpdateExtent(self, request, inInfo, outInfo):
        from mpi4py import MPI
        comm = MPI.COMM_WORLD
        rank = comm.Get_rank()
        size = comm.Get_size()
        info = inInfo[0].GetInformationObject(0)
        info.Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_PIECE_NUMBER(), rank)
        info.Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_NUMBER_OF_PIECES(), size)
        info.Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_NUMBER_OF_GHOST_LEVELS(), 0)
        if self._time is not None and self._time != -1e30:
            info.Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(), self._time)
        return 1

    def RequestData(self, request, inInfo, outInfo):
        """
        The core pipeline execution method invoked per timestep.
        Extracts the VTK data object, determines the current time/cycle, and delegates 
        to `pydpvz` to execute the MPI-coordinated serialization and file writing.
        """
        from mpi4py import MPI
        import pydpvz
        from pydpvz.vtk_serializer import serialize_partitioned_dataset_collection, serialize_multiblock_dataset

        input_data = self.GetInputData(inInfo, 0, 0)
        
        # Determine the current timestep from pipeline information or explicit property
        time = 0.0
        if self._time is not None and self._time != -1e30:
            time = self._time
        else:
            info = inInfo[0].GetInformationObject(0)
            if info.Has(vtk.vtkDataObject.DATA_TIME_STEP()):
                time = info.Get(vtk.vtkDataObject.DATA_TIME_STEP())
            elif input_data.GetInformation().Has(vtk.vtkDataObject.DATA_TIME_STEP()):
                time = input_data.GetInformation().Get(vtk.vtkDataObject.DATA_TIME_STEP())

        comm = MPI.COMM_WORLD
        rank = comm.Get_rank()

        if not self._filename:
            if rank == 0:
                print("Error: DPvtkWriter FileName not set")
            return 0

        # Replace on the first cycle, append thereafter
        mode = pydpvz.DPvzMode.DPvzReplace if self._cycle == 0 else pydpvz.DPvzMode.DPvzReadWrite
        
        # Initialize archive and execute the collective write
        archive = pydpvz.DPvzVtk(self._filename, mode, comm, False)

        if rank == 0:
            print(f"[{rank}] DPvtkWriter: Processing cycle {self._cycle} (time={time}) to {self._filename}...")

        xml_string = ""
        if input_data.IsA("vtkPartitionedDataSetCollection"):
            xml_string = serialize_partitioned_dataset_collection(input_data, rank, self._cycle, time)
        elif input_data.IsA("vtkMultiBlockDataSet"):
            xml_string = serialize_multiblock_dataset(input_data, rank, self._cycle, time)
        elif input_data.IsA("vtkDataSet"):
            # Wrap standard datasets (like vtkImageData from Wavelet) in a PDC for the serializer
            temp_pdc = vtk.vtkPartitionedDataSetCollection()
            temp_pdc.SetPartition(0, 0, input_data)
            xml_string = serialize_partitioned_dataset_collection(temp_pdc, rank, self._cycle, time)
        else:
            if rank == 0:
                print(f"Error: Unsupported data type {input_data.GetClassName()}")
            return 0

        archive.write(self._cycle, time, xml_string)
        
        self._cycle += 1
        return 1
