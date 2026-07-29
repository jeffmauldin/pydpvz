"""
VTK Serialization module for converting ParaView/VTK memory objects into string payloads.

This module provides utilities to traverse distributed ParaView pipelines (which often 
surface as composite datasets like `vtkPartitionedDataSetCollection` or `vtkMultiBlockDataSet`),
flatten them into a single `vtkUnstructuredGrid`, and serialize them into memory via 
`vtkXMLUnstructuredGridWriter`. 
The serialized strings are wrapped in custom `<FILE NAME=...>` XML tags for aggregation 
by the `pydpvz` C++ backend.
"""

import vtk

def convert_pdc_to_multiblock(pdc):
    """
    Converts a vtkPartitionedDataSetCollection to a vtkMultiBlockDataSet.
    
    This is often required because many legacy VTK filters or older serialization 
    pathways do not fully support the newer PDC format natively.
    """
    converter = vtk.vtkConvertToMultiBlockDataSet()
    converter.SetInputData(pdc)
    converter.Update()
    return converter.GetOutput()

def convert_to_unstructured_grid(dataset):
    """
    Flattens a VTK composite dataset (e.g., vtkMultiBlockDataSet) into a single vtkUnstructuredGrid.
    
    In parallel environments, a rank's local partition might consist of many small blocks. 
    Appending them into a single grid allows us to write exactly one continuous byte stream 
    per rank to the DPvz archive.
    """
    append = vtk.vtkAppendFilter()
    if dataset.IsA("vtkCompositeDataSet"):
        it = dataset.NewIterator()
        it.InitTraversal()
        while not it.IsDoneWithTraversal():
            ds = it.GetCurrentDataObject()
            if ds and ds.IsA("vtkDataSet"):
                append.AddInputData(ds)
            it.GoToNextItem()
    elif dataset.IsA("vtkDataSet"):
        append.AddInputData(dataset)
    
    append.Update()
    return append.GetOutput()

def serialize_multiblock_dataset(mb, rank=0, cycle=0, time=0.0):
    """
    Serializes a vtkMultiBlockDataSet to an XML string payload.
    
    The payload is compressed in-memory using ZLib and wrapped in custom `<FILE NAME=...>` tags 
    that the DPvz C++ reader expects when parsing the archive.
    
    Args:
        mb (vtkMultiBlockDataSet): The dataset to serialize.
        rank (int): The current MPI rank processing the data.
        cycle (int): The current timestep index.
        time (float): The current simulation time.
        
    Returns:
        bytes: The serialized, compressed XML payload.
    """
    grid = convert_to_unstructured_grid(mb)
    writer = vtk.vtkXMLUnstructuredGridWriter()
    writer.SetInputData(grid)
    writer.SetDataModeToAppended()
    writer.EncodeAppendedDataOn()
    writer.SetCompressorTypeToZLib()
    writer.SetWriteToOutputString(1)
    writer.Update()
    out = writer.GetOutputString()
    filename = f"multiblock_cycle_{cycle}_rank_{rank}.vtu"
    if isinstance(out, str):
        return f"<FILE NAME='{filename}'>\n{out}\n</FILE NAME='{filename}'>\n".encode('utf-8')
    else:
        return f"<FILE NAME='{filename}'>\n".encode('utf-8') + out + f"\n</FILE NAME='{filename}'>\n".encode('utf-8')


def serialize_partitioned_dataset_collection(pdc, rank=0, cycle=0, time=0.0):
    """
    Serializes a vtkPartitionedDataSetCollection to an XML string payload.
    
    Args:
        pdc (vtkPartitionedDataSetCollection): The dataset to serialize.
        rank (int): The current MPI rank processing the data.
        cycle (int): The current timestep index.
        time (float): The current simulation time.
        
    Returns:
        bytes: The serialized, compressed XML payload.
    """
    mb = convert_pdc_to_multiblock(pdc)
    return serialize_multiblock_dataset(mb, rank, cycle, time)
