import vtk
import re

def deserialize_vtk_from_buffer(buffer_bytes):
    """
    Parses a DPvzVtkData buffer containing multiple <FILE NAME='...'> blocks.
    Returns a list of vtkDataSets (e.g. vtkUnstructuredGrid).
    """
    # The buffer contains blocks like:
    # <FILE NAME='filename.vtu'>\n ... data ... \n</FILE NAME='filename.vtu'>\n
    
    text = buffer_bytes.decode('utf-8', errors='ignore')
    
    # Find all <FILE NAME='...'> headers
    datasets = []
    
    pattern = r"<FILE NAME='([^']+)'>\n(.*?)\n</FILE NAME='\1'>\n"
    # DOTALL allows dot to match newlines
    matches = re.finditer(pattern, text, re.DOTALL)
    
    for match in matches:
        filename = match.group(1)
        data = match.group(2)
        
        if filename.endswith(".vtu"):
            reader = vtk.vtkXMLUnstructuredGridReader()
        elif filename.endswith(".vtp"):
            reader = vtk.vtkXMLPolyDataReader()
        else:
            reader = vtk.vtkXMLGenericDataObjectReader()
            
        reader.SetReadFromInputString(1)
        reader.SetInputString(data)
        reader.Update()
        
        ds = reader.GetOutput()
        if ds:
            datasets.append(ds)
            
    return datasets
