import os
import time
import sys
import argparse
from pathlib import Path

from helpers.process_ome_tiff import process_ome_tiff
from helpers.process_tiff import process_tiff
from helpers.move_to_completed import move_to_completed

def main():
    print("Starting TissueViewer watch folder")
    parser = argparse.ArgumentParser(description="Watch folder and process new files as they are added")
    parser.add_argument('import_dir', nargs='?', help='The data directory to watch for new files (default: %(default)s)', default='/iv-import')
    parser.add_argument('storage_dir', nargs='?', help='The output directory for the processed files (default: %(default)s)', default='/iv-store')
    parser.add_argument('completed_dir', nargs='?', help='The directory to move completed files to (default: %(default)s)', default='/iv-completed')
    parser.add_argument('vips', nargs='?', help='Path to the VIPS executable (default: %(default)s)', default='vips')
    args = parser.parse_args()

    if not args.import_dir or not args.storage_dir:
        print("Usage: process_folder.py [-t num_cores] import_dir storage_dir vips")
        sys.exit(1)
    
    import_dir = Path(args.import_dir)
    storage_dir = Path(args.storage_dir)
    completed_dir = Path(args.completed_dir)
    vips = args.vips

    print(f"Watching folder {import_dir} for new files, output to {storage_dir}, and vips location is {vips}")

    while True: 
        for file in import_dir.rglob('*.tif'):
            process_file(file, storage_dir, vips, completed_dir)
        for file in import_dir.rglob('*.tiff'):
            process_file(file, storage_dir, vips, completed_dir)
        for file in import_dir.rglob('*.svs'):
            process_file(file, storage_dir, vips, completed_dir)
                
        time.sleep(30)

def process_file(file, storage_dir, vips, completed_dir):
    file_name = os.path.splitext(os.path.basename(file))[0]
    base_folder = os.path.join(storage_dir, os.path.basename(os.path.dirname(file)), file_name)
    print("checking if exsists: ", base_folder)
    
    if not os.path.exists(base_folder):
        # if file has not been modified for 10 seconds, run export
        if time.time() - os.path.getmtime(file) > 10:
            file_path = str(file)
            file_name = os.path.basename(file_path)
            if file_name.endswith('.ome.tiff') or file_name.endswith('.ome.tif'):
                process_ome_tiff(file_path, storage_dir, vips)
            elif file_name.endswith('.tif') or file_name.endswith('.tiff') or file_name.endswith('.svs'):
                process_tiff(file_path, storage_dir, vips)
            
            move_to_completed(file_path, completed_dir)

if __name__ == "__main__":
    main()
