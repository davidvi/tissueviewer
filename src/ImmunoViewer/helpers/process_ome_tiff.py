#!/usr/bin/env python3

from aicsimageio import AICSImage
import tifffile
import os
# import pyvips
import json

def process_ome_tiff(ome_tiff_path, output_folder, vips):
    """
    Process an OME-TIFF file, saving each channel as an individual TIFF file
    and converting them to Deep Zoom Image (DZI) format.
    
    Args:
    - ome_tiff_path (str): Path to the OME-TIFF file.
    - base_folder (str): Base folder to save the output files.
    """
    
    base_folder = os.path.join(output_folder, os.path.splitext(os.path.basename(ome_tiff_path))[0])

    image = AICSImage(ome_tiff_path)
    n_channels = image.shape[1]

    # see if directory exists
    if not os.path.exists(base_folder):
        os.makedirs(base_folder)

    # Iterate over each channel and save it as an individual TIFF file
    print(f"Processing {n_channels} channels")

    for channel in range(n_channels):
        print(f"Processing channel {channel}")
        # Extract the channel data
        channel_data = image.get_image_data("YX", C=channel)
        
        # Save the channel data as a TIFF file
        output_file_name = f'{base_folder}/channel_{channel}.tiff'
        tifffile.imwrite(output_file_name, channel_data)

    # Inside the loop where you convert TIFF files to DZI
    print(f"Converting {n_channels} channels to DZI")
    for channel in range(n_channels):
        print(f"Converting channel {channel} to DZI")
        command = f'{vips} dzsave {base_folder}/channel_{channel}.tiff {base_folder}/channel_{channel} --suffix .tiff'
        print(command)
        os.system(command)

    # Dump json with slide info 
    print(f"Creating JSON file for slide info")
    channel_details = image.metadata.images[0].pixels.channels
    colors = ["blue", "green", "green", "yellow", "cyan"]
    image_meta = {
        "ch": {},
        "gain": {},
        "ch_stain": {},
        "description": "",
        "overlays": []
    }
    filler_gain_value = 6

    for i, channel in enumerate(channel_details):
        if i < len(colors):
            image_meta["ch"]["channel_" + str(i) + "_files"] = colors[i]
        else:
            image_meta["ch"]["channel_" + str(i) + "_files"] = "empty"

        image_meta["gain"]["channel_" + str(i) + "_files"] = filler_gain_value
        image_meta["ch_stain"]["channel_" + str(i) + "_files"] = channel.name

    image_meta_json = json.dumps(image_meta)

    with open(base_folder + "/sample.json", 'w') as file:
        file.write(image_meta_json)


if __name__ == "__main__":
    # Example usage
    ome_tiff_path = '/Volumes/DATA/iv-import/Q129_S005_A107_CosMxTMA2__2024-03-14-06-18_EM001_000491.ome.tiff'
    output_folder = "/Volumes/DATA/iv-store"
    vips = '/opt/homebrew/bin/vips'
    process_ome_tiff(ome_tiff_path, output_folder, vips)