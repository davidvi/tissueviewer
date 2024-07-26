#!/usr/bin/env python3

from aicsimageio import AICSImage
import tifffile
import os
# import pyvips
import json

DRY_RUN = False

def process_tiff(input_tiff_file, output_folder, vips):
    """
    Process a folder with tiff files, saving each channel as an individual TIFF file
    and converting them to Deep Zoom Image (DZI) format.
    
    Args:
    - ome_tiff_path (str): Path to the folder.
    - base_folder (str): Base folder to save the output files.
    """

    file_name = os.path.splitext(os.path.basename(input_tiff_file))[0]
    base_folder = os.path.join(output_folder, os.path.basename(os.path.dirname(input_tiff_file)), file_name)

    print(f"Processing file {input_tiff_file} to {base_folder}")

    # see if directory exists
    if DRY_RUN == False:
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)

    command = f'{vips} dzsave {input_tiff_file} {base_folder}/{file_name} --suffix .jpg'
    print(command)
    if DRY_RUN == False:
        os.system(command)

    # Dump json with slide info
    print(f"Creating JSON file for slide info")
    # try open json 
    try:
        with open(f'{base_folder}/sample.json', 'r') as f:
            data = json.load(f)
    except:
        data = {
            "ch": {},
            "gain": {},
            "ch_stain": {},
            "description": "",
            "overlays": []
        }
    
    # add new data
    colors = ["blue", "green", "green", "yellow", "cyan"]
    filler_gain_value = 6

    length = len(data["ch"])
    if length < len(colors):
        data["ch"][file_name + "_files"] = colors[length]
    else:
        data["ch"][file_name + "_files"] = "empty"
    
    data["gain"][file_name + "_files"] = filler_gain_value
    data["ch_stain"][file_name + "_files"] = file_name

    if DRY_RUN == False:
        with open(f'{base_folder}/sample.json', 'w') as f:
            json.dump(data, f)


if __name__ == "__main__":
    # Example usage
    input_tiff_file = '/Volumes/DATA/iv-import/Q129_S005_A107_CosMxTMA2__2024-03-14-06-18_EM001_000491.ome.tiff'
    output_folder = "/Volumes/DATA/iv-store"
    vips = '/opt/homebrew/bin/vips'
    process_tiff(input_tiff_file, output_folder, vips)