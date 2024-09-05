import os
import time
import sys
import argparse
import subprocess
from pathlib import Path

ALLOWED_EXTENSIONS = ('.tiff', '.svs', '.tif', '.qptiff')

def main():
    print("Starting TissueViewer watch folder")
    parser = argparse.ArgumentParser(description="Watch folder and process new files as they are added")
    parser.add_argument('import_dir', nargs='?', help='The data directory to watch for new files (default: %(default)s)', default='/tv-import')
    parser.add_argument('storage_dir', nargs='?', help='The output directory for the processed files (default: %(default)s)', default='/tv-store')
    parser.add_argument('bioformats2raw', nargs='?', help='Path to the Bioformats2raw executable (default: %(default)s)', default='bioformats2raw')
    args = parser.parse_args()

    if not args.import_dir or not args.storage_dir:
        print("Usage: watch_folder.py import_dir storage_dir [bioformats2raw]")
        sys.exit(1)
    
    import_dir = Path(args.import_dir)
    storage_dir = Path(args.storage_dir)
    bf = args.bioformats2raw

    print(f"Watching folder {import_dir} for new files, output to {storage_dir}, and bioformats2raw executable location is {bf}")

    while True: 
        for file in import_dir.rglob('*'):
            if file.is_file() and file.suffix.lower() in ALLOWED_EXTENSIONS:
                process_file(file, import_dir, storage_dir, bf)
                
        time.sleep(30)

def process_file(file, import_dir, storage_dir, bf):
    file_path = str(file)
    relative_path = file.relative_to(import_dir)
    output_zarr = storage_dir / relative_path.with_suffix('.zarr')

    if not output_zarr.exists():
        os.makedirs(output_zarr.parent, exist_ok=True)
        
        # Attempt conversion
        try:
            subprocess.run([bf, file_path, str(output_zarr)], check=True)
            print(f"Successfully converted {file_path} to {output_zarr}")
        except subprocess.CalledProcessError:
            print(f"Failed to convert {file_path}")
        
        # Create .zarr folder even if conversion fails
        output_zarr.mkdir(exist_ok=True)
    else:
        print(f"Zarr folder already exists for {file_path}")

if __name__ == "__main__":
    main()