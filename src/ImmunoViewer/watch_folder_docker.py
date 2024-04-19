import os
import time
import sys
import argparse
from pathlib import Path

from helpers.process_ome_tiff import process_ome_tiff
from helpers.process_tiff import process_tiff

def main():
    print("Starting ImmunoViewer watch folder")
    parser = argparse.ArgumentParser(description="Watch folder and process new files as they are added")
    parser.add_argument('import_dir', nargs='?', help='The data directory to watch for new files (default: %(default)s)', default='/iv-import')
    parser.add_argument('storage_dir', nargs='?', help='The output directory for the processed files (default: %(default)s)', default='/iv-store')
    parser.add_argument('vips', nargs='?', help='Path to the VIPS executable (default: %(default)s)', default='vips')
    args = parser.parse_args()

    if not args.import_dir or not args.storage_dir:
        print("Usage: process_folder.py [-t num_cores] import_dir storage_dir vips")
        sys.exit(1)
    
    import_dir = Path(args.import_dir)
    storage_dir = Path(args.storage_dir)
    vips = args.vips

    print(f"Watching folder {import_dir} for new files, output to {storage_dir}, and vips location is {vips}")

    while True: 
        # iterate .ome.tiff files in import_dir
        for file in import_dir.glob('*.ome.tiff'):
            # if no folder with same name as ome.tiff file (without .tiff) is found in storage_dir, run export
            if not os.path.exists(storage_dir / file.stem):
                # if .ome.tiff file has not been modified for 10 seconds, run export
                if time.time() - os.path.getmtime(file) > 10:
                    process_ome_tiff(file, storage_dir, vips)
        
        # iterate all folders in import_dir
        for folder in import_dir.iterdir():
            # iterate .tiff or .tif files in folder
            for file in folder.glob('*.tif*'):
                # if no folder with same name as tiff file (without .tiff) is found in storage_dir, run export
                relative_folder_path = folder.relative_to(import_dir)
                target_dir = storage_dir / relative_folder_path / f'{file.stem}_files'
                # print("checking for: ", target_dir)
                if not os.path.exists(target_dir):
                    # if tiff file has not been modified for 10 seconds, run export
                    if time.time() - os.path.getmtime(file) > 60:
                        process_tiff(file, storage_dir, vips)
                        # print("processing..", file, storage_dir, vips)
                
        time.sleep(30)

if __name__ == "__main__":
    main()
