#!/usr/bin/env python3

from aicsimageio import AICSImage
import tifffile
import os

base_folder = "/home/david/david/orion-images/"
ome_tiff_path = '/home/david/david/orion-images/Q129_S004_A107_CosMxTMA1__2024-03-22-05-23_EM001_000495.ome.tiff'

image = AICSImage(ome_tiff_path)
n_channels = image.shape[1]

# Iterate over each channel and save it as an individual TIFF file
for channel in range(n_channels):
    # Extract the channel data
    channel_data = image.get_image_data("YX", C=channel)
    
    # Save the channel data as a TIFF file
    output_file_name = f'{base_folder}/channel_{channel}.tiff'
    tifffile.imwrite(output_file_name, channel_data)

# Iterate over the channels and convert to DZI
for channel in range(n_channels):
    # Generate the channel-specific command
    command = f'vips dzsave {base_folder}/channel_{channel}.tiff {base_folder}/channel_{channel} --suffix .tiff'
    
    # Execute the command
    os.system(command)

