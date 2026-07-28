import vtk

def convert_pdc_to_multiblock(pdc):
    """
    Converts a vtkPartitionedDataSetCollection to a vtkMultiBlockDataSet.
    """
    converter = vtk.vtkConvertToMultiBlockDataSet()
    converter.SetInputData(pdc)
    converter.Update()
    return converter.GetOutput()

def convert_to_unstructured_grid(dataset):
    """
    Flattens a VTK composite dataset (e.g. vtkMultiBlockDataSet) into a single vtkUnstructuredGrid.
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
    Serializes a vtkMultiBlockDataSet to an XML string.
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
    Serializes a vtkPartitionedDataSetCollection to an XML string.
    """
    mb = convert_pdc_to_multiblock(pdc)
    return serialize_multiblock_dataset(mb, rank, cycle, time)
