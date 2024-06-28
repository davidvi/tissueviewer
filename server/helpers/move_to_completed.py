#!/usr/bin/env python3

import os

DRY_RUN = False

def move_to_completed(input_tiff_file, output_folder):
  base_folder = os.path.join(output_folder, os.path.basename(os.path.dirname(input_tiff_file)))
  print(f"Checking if folder exists: {base_folder}")
  if DRY_RUN == False:
    if not os.path.exists(base_folder):
      os.makedirs(base_folder)

  print(f"Moving file {input_tiff_file} to {base_folder}")
  if DRY_RUN == False:
    destination_path = os.path.join(base_folder, os.path.basename(input_tiff_file))
    os.rename(input_tiff_file, destination_path)