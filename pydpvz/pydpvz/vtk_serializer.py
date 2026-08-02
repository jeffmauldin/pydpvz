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
import json

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
    count = 0
    if dataset.IsA("vtkCompositeDataSet"):
        it = dataset.NewIterator()
        it.InitTraversal()
        while not it.IsDoneWithTraversal():
            ds = it.GetCurrentDataObject()
            if ds and ds.IsA("vtkDataSet"):
                if ds.GetNumberOfPoints() > 0 or ds.GetNumberOfCells() > 0 or ds.IsA("vtkImageData") or ds.IsA("vtkStructuredGrid"):
                    append.AddInputData(ds)
                    count += 1
            it.GoToNextItem()
    elif dataset.IsA("vtkDataSet"):
        if dataset.GetNumberOfPoints() > 0 or dataset.GetNumberOfCells() > 0 or dataset.IsA("vtkImageData") or dataset.IsA("vtkStructuredGrid"):
            append.AddInputData(dataset)
            count += 1
            
    if count == 0:
        return None
        
    append.Update()
    return append.GetOutput()

def extract_hierarchy_and_blocks(dataset):
    """
    Traverses a VTK dataset (PDC, MultiBlock, or standard DataSet) and extracts 
    its top-level block hierarchy and leaf datasets without merging disjoint blocks.
    
    Returns:
        list of dict: Each dict contains 'index', 'name', and 'dataset'.
    """
    blocks = []
    if dataset.IsA("vtkPartitionedDataSetCollection"):
        num_blocks = dataset.GetNumberOfPartitionedDataSets()
        for i in range(num_blocks):
            meta = dataset.GetMetaData(i)
            name = ""
            if meta and meta.Has(vtk.vtkCompositeDataSet.NAME()):
                name = meta.Get(vtk.vtkCompositeDataSet.NAME())
            elif meta and meta.Has(dataset.NAME()):
                name = meta.Get(dataset.NAME())
            else:
                name = f"block_{i}"
            
            num_parts = dataset.GetNumberOfPartitions(i)
            valid_parts = []
            for j in range(num_parts):
                ds = dataset.GetPartition(i, j)
                if ds and (ds.GetNumberOfPoints() > 0 or ds.GetNumberOfCells() > 0 or ds.IsA("vtkImageData") or ds.IsA("vtkStructuredGrid")):
                    valid_parts.append(ds)
            
            merged_ds = None
            if len(valid_parts) == 1:
                merged_ds = valid_parts[0]
            elif len(valid_parts) > 1:
                append = vtk.vtkAppendFilter()
                for part in valid_parts:
                    append.AddInputData(part)
                append.Update()
                merged_ds = append.GetOutput()
                
            blocks.append({"index": i, "name": name, "dataset": merged_ds})
            
    elif dataset.IsA("vtkMultiBlockDataSet"):
        num_blocks = dataset.GetNumberOfBlocks()
        for i in range(num_blocks):
            meta = dataset.GetMetaData(i)
            name = ""
            if meta and meta.Has(vtk.vtkCompositeDataSet.NAME()):
                name = meta.Get(vtk.vtkCompositeDataSet.NAME())
            elif meta and meta.Has(dataset.NAME()):
                name = meta.Get(dataset.NAME())
            else:
                name = f"block_{i}"
                
            blk = dataset.GetBlock(i)
            merged_ds = None
            if blk:
                if blk.IsA("vtkCompositeDataSet"):
                    merged_ds = convert_to_unstructured_grid(blk)
                    if merged_ds and merged_ds.GetNumberOfPoints() == 0 and merged_ds.GetNumberOfCells() == 0 and not merged_ds.IsA("vtkImageData") and not merged_ds.IsA("vtkStructuredGrid"):
                        merged_ds = None
                elif blk.IsA("vtkDataSet"):
                    if blk.GetNumberOfPoints() > 0 or blk.GetNumberOfCells() > 0 or blk.IsA("vtkImageData") or blk.IsA("vtkStructuredGrid"):
                        merged_ds = blk
            blocks.append({"index": i, "name": name, "dataset": merged_ds})
            
    elif dataset.IsA("vtkDataSet"):
        blocks.append({"index": 0, "name": "block_0", "dataset": dataset})
    else:
        merged_ds = convert_to_unstructured_grid(dataset)
        blocks.append({"index": 0, "name": "block_0", "dataset": merged_ds})
        
    return blocks

def serialize_dataset_with_hierarchy(dataset, rank=0, cycle=0, time=0.0):
    """
    Serializes a VTK dataset (composite or single) while preserving block hierarchy.
    Generates a hierarchy JSON summary block along with XML string payloads for non-empty blocks.
    """
    blocks = extract_hierarchy_and_blocks(dataset)
    
    hierarchy_info = {"blocks": []}
    
    if dataset.IsA("vtkPartitionedDataSetCollection"):
        asm = dataset.GetDataAssembly()
        if asm:
            hierarchy_info["data_assembly_xml"] = asm.SerializeToXML(vtk.vtkIndent())
            
    data_payloads = []
    
    for blk in blocks:
        idx = blk["index"]
        name = blk["name"]
        ds = blk["dataset"]
        
        filename = None
        if ds is not None:
            grid = ds if ds.IsA("vtkUnstructuredGrid") else convert_to_unstructured_grid(ds)
            writer = vtk.vtkXMLUnstructuredGridWriter()
            writer.SetInputData(grid)
            writer.SetDataModeToAppended()
            writer.EncodeAppendedDataOn()
            writer.SetCompressorTypeToZLib()
            writer.SetWriteToOutputString(1)
            writer.Update()
            out = writer.GetOutputString()
            
            filename = f"block_{idx}_cycle_{cycle}_rank_{rank}.vtu"
            if isinstance(out, str):
                payload_bytes = f"<FILE NAME='{filename}'>\n{out}\n</FILE NAME='{filename}'>\n".encode('utf-8')
            else:
                payload_bytes = f"<FILE NAME='{filename}'>\n".encode('utf-8') + out + f"\n</FILE NAME='{filename}'>\n".encode('utf-8')
            data_payloads.append(payload_bytes)
            
        hierarchy_info["blocks"].append({
            "index": idx,
            "name": name,
            "filename": filename
        })
        
    json_bytes = f"<FILE NAME='hierarchy.json'>\n{json.dumps(hierarchy_info, indent=2)}\n</FILE NAME='hierarchy.json'>\n".encode('utf-8')
    
    return json_bytes + b"".join(data_payloads)

def serialize_multiblock_dataset(mb, rank=0, cycle=0, time=0.0):
    """
    Serializes a vtkMultiBlockDataSet to an XML string payload while preserving hierarchy.
    
    Args:
        mb (vtkMultiBlockDataSet): The dataset to serialize.
        rank (int): The current MPI rank processing the data.
        cycle (int): The current timestep index.
        time (float): The current simulation time.
        
    Returns:
        bytes: The serialized, compressed XML payload with hierarchy metadata.
    """
    return serialize_dataset_with_hierarchy(mb, rank, cycle, time)


def serialize_partitioned_dataset_collection(pdc, rank=0, cycle=0, time=0.0):
    """
    Serializes a vtkPartitionedDataSetCollection to an XML string payload while preserving hierarchy.
    
    Args:
        pdc (vtkPartitionedDataSetCollection): The dataset to serialize.
        rank (int): The current MPI rank processing the data.
        cycle (int): The current timestep index.
        time (float): The current simulation time.
        
    Returns:
        bytes: The serialized, compressed XML payload with hierarchy metadata.
    """
    return serialize_dataset_with_hierarchy(pdc, rank, cycle, time)
