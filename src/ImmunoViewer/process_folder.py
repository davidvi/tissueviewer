#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
from pathlib import Path

from ImmunoViewer.tile import DeepZoomStaticTiler

def find_files(path, min_depth, max_depth):
    for root, dirs, files in os.walk(str(path)):
        depth = root.count(os.path.sep) - str(path).count(os.path.sep)
        if min_depth <= depth <= max_depth:
            for file in files:
                if file.endswith('.tif'):
                    yield Path(root) / file

def main():
    parser = argparse.ArgumentParser(description="Process TIF files in a directory")
    parser.add_argument('data_dir', help='The data directory containing the TIF files')
    parser.add_argument('-t', '--num_cores', type=int, default=4, help='Number of cores to use (default: 4)')
    args = parser.parse_args()

    script_dir = Path(__file__).parent.resolve()
    python_tile = script_dir / "src/ImmunoViewer/tile.py"

    if not args.data_dir:
        print("Usage: process_folder.py [-t num_cores] data_dir")
        sys.exit(1)

    num_cores = args.num_cores if args.num_cores else 4

    data_dir = Path(args.data_dir)
    all_files = list(find_files(data_dir, 1, 2))

    for file in all_files:
        print(f"Processing {file}")
        sample_name = file.stem
        tif_name = file.name
        folder = file.parent

        print(f"check if {folder / (sample_name + '_files')} exists")
        if not (folder / f"{sample_name}_files").is_dir():
            print("folder does not exist, running python script")

            basename = os.path.join(folder, os.path.splitext(os.path.basename(file))[0])

            print(f"running for {file} basename is {basename}")

            DeepZoomStaticTiler(
                file,
                basename,
                "jpeg",
                254,
                1,
                True,
                100,
                num_cores,
                False,
            ).run()


if __name__ == "__main__":
    main()
