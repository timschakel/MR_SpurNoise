#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 14 08:11:06 2023

@author: tschakel

runfile('/smb/user/tschakel/BLD_RT_RESEARCH_DATA/USER/tschakel/projects/wadqc/QAtests/MR_SpurNoise/MR_SpurNoise/MR_SpurNoise_wadwrapper.py', args='-r results.json -c config/spurnoise_config.json -d /smb/user/tschakel/BLD_RT_RESEARCH_DATA/USER/tschakel/projects/wadqc/QAtests/MR_SpurNoise/MR_SpurNoise/data/data1', wdir='/smb/user/tschakel/BLD_RT_RESEARCH_DATA/USER/tschakel/projects/wadqc/QAtests/MR_SpurNoise/MR_SpurNoise/')

"""

from wad_qc.module import pyWADinput
from wad_qc.modulelibs import wadwrapper_lib
import pydicom
import matplotlib.pyplot as plt
import numpy as np

### Helper functions
def getValue(ds, label):
    """Return the value of a pydicom DataElement in Dataset identified by label.

    ds: pydicom Dataset
    label: dicom identifier, in either pydicom Tag object, string or tuple form.
    """
    if isinstance(label, str):
        try:
            # Assume form "0x0008,0x1030"
            tag = pydicom.tag.Tag(label.split(','))
        except ValueError:
            try:
                # Assume form "SeriesDescription"
                tag = ds.data_element(label).tag
            except (AttributeError, KeyError):
                # `label` string doesn't represent an element of the DataSet
                return None
    else:
        # Assume label is of form (0x0008,0x1030) or is a pydicom Tag object.
        tag = pydicom.tag.Tag(label)

    try:
        return str(ds[tag].value)
    except KeyError:
        # Tag doesn't exist in the DataSet
        return None
    
def isFiltered(ds, filters):
    """Return True if the Dataset `ds` complies to the `filters`,
    otherwise return False.
    """
    for tag, value in filters.items():
        if not str(getValue(ds, tag)) == str(value):
            # Convert both values to string before comparison. Reason is that
            # pydicom can return 'str', 'int' or 'dicom.valuerep' types of data.
            # Similarly, the user (or XML) supplied value can be of any type.
            return False
    return True

def applyFilters(series_filelist, filters):
    """Apply `filters` to the `series_filelist` and return the filtered list.

    First, convert `filters` from an ElementTree Element to a dictionary
    Next, create a new list in the same shape as `series_filelist`, but only
    include filenames for which isFiltered returns True.
    Only include sublists (i.e., series) which are non empty.
    """
    # Turn ElementTree element attributes and text into filters
    #filter_dict = {element.attrib["name"]: element.text for element in filters}
    filter_dict = filters

    filtered_series_filelist = []
    # For each series in the series_filelist (or, study):
    for instance_filelist in series_filelist:
        # Filter filenames within each series
        filtered_instance_filelist = [fn for fn in instance_filelist
                                      if isFiltered(
                pydicom.read_file(fn, stop_before_pixels=True), filter_dict)]
        # Only add the series which are not empty
        if filtered_instance_filelist:
            filtered_series_filelist.append(filtered_instance_filelist)

    return filtered_series_filelist


if __name__ == "__main__":
    data, results, config = pyWADinput()
    
    # Log which series are found
    data_series = data.getAllSeries()
    print("The following series are found:")
    for item in data_series:
        print(item[0]["SeriesDescription"].value+" with "+str(len(item))+" instances")
            
    for name,action in config['actions'].items():
        if name == 'acqdatetime':
            filters = action["filters"]
            datetime_series = data.getInstanceByTags(filters["datetime_filter"])
            dt = wadwrapper_lib.acqdatetime_series(datetime_series[0])
            results.addDateTime('AcquisitionDateTime', dt) 
            
        elif name == 'showimages':
            filters = action["filters"]
            params = action["params"]
            
            # number of scans is different for 1.5T vs 3.0T (5 vs 4 scans)
            nscans = params["number_of_scans"]
            freqs = filters.keys()
            images = []
            dcmheaders = []
            
            for f0 in freqs:
                data_f0 = applyFilters(data.series_filelist,filters[f0])
                dcmInfile,pixeldata,dicomMode = wadwrapper_lib.prepareInput(data_f0[0],headers_only=False)
                images.append(pixeldata)
                dcmheaders.append(dcmInfile)
                
            # Create plots
            figtitle = 'Spurious Noise Test: '+str(dcmInfile.PatientName)+' '+dcmInfile.StudyDate+' '+dcmInfile.StudyTime
            fig, axs = plt.subplots(1,nscans,figsize=(10,3))
            fig.suptitle(figtitle)
            
            n=0
            for image in images:
                im_max = 4*np.mean(image)
                print(np.mean(image))
                axs[n].imshow(image,cmap='gray',vmin=0,vmax=im_max)
                axs[n].set_title(dcmheaders[n].SeriesDescription)
                axs[n].axis('off')
                n=n+1
            
            filename = 'SpurNoise.png'
            fig.savefig(filename,dpi=300)
            results.addObject("SpurNoise_figure", filename)
            

    results.write()