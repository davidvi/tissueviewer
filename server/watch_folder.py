import os
import time
import sys
import argparse
import subprocess
from pathlib import Path

ALLOWED_EXTENSIONS = (
'.1sc', '.2', '.3', '.4', '.afm', '.afi', '.aim', '.al3d', '.am', '.amiramesh',
'.arf', '.avi', '.bmp', '.btf', '.c01', '.ch5', '.cif', '.cr2', '.crw', '.csv',
'.cxd', '.czi', '.dat', '.dcm', '.dib', '.dicom', '.dm2', '.dm3', '.dm4', '.dti',
'.dv', '.eps', '.epsi', '.exp', '.fdf', '.fff', '.fits', '.flex', '.fli', '.frm',
'.gel', '.gif', '.grey', '.hdf', '.hdp', '.hdr', '.hed', '.his', '.htd', '.html',
'.hx', '.i2i', '.ics', '.ids', '.im3', '.img', '.ims', '.inr', '.ipl', '.ipm',
'.ipw', '.jp2', '.jpg', '.jpk', '.jpx', '.l2d', '.labels', '.lei', '.lif', '.lim',
'.lms', '.lsm', '.mdb', '.mea', '.mnc', '.mng', '.mov', '.mrc', '.mrw', '.msr',
'.mtb', '.mvd2', '.naf', '.nd', '.nd2', '.nef', '.nhdr', '.nii', '.nrrd', '.obf',
'.oib', '.oif', '.oir', '.ome', '.ome.btf', '.ome.tf2', '.ome.tf8', '.ome.tif',
'.ome.tiff', '.ome.xml', '.par', '.pbm', '.pco.raw', '.pcoraw', '.pcx', '.pds',
'.pgm', '.pic', '.pict', '.png', '.ppm', '.pr3', '.ps', '.psd', '.qptiff', '.r3d',
'.raw', '.rec', '.res', '.scn', '.sdt', '.seq', '.sif', '.sld', '.sm2', '.sm3',
'.spc', '.spe', '.spi', '.stp', '.stk', '.svs', '.sxm', '.tf2', '.tf8', '.tff',
'.tfr', '.tga', '.tif', '.tiff', '.tnb', '.top', '.txt', '.v', '.vms', '.vsi',
'.vws', '.wat', '.wlz', '.xdce', '.xml', '.xqs', '.xv', '.zfp', '.zfr', '.zip', '.zvi'
)

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