import os
import time
import sys
import argparse
from pathlib import Path
from threading import Thread

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from helpers.process_ome_tiff import process_ome_tiff
from helpers.process_tiff import process_tiff

class Handler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.last_modified = {}

    def on_any_event(self, event):
        if event.is_directory:
            return None
        elif event.event_type == 'created':
            print("Watchdog received created event - % s." % event.src_path)
        elif event.event_type == 'modified':
            print("Watchdog received modified event - % s." % event.src_path)

        self.last_modified[event.src_path] = time.time()

def check_files(handler, import_dir, storage_dir, vips):
    '''
    Check the last modified time of files and process them if they haven't been modified for 10 seconds.
    This is done to ensure the file is done uploading before processing.
    '''
    while True:
        current_time = time.time()
        for file_path, last_modified_time in handler.last_modified.items():
            if current_time - last_modified_time > 10:
                print(f"File {file_path} hasn't been modified for 10 seconds.")
                # process ome-tiff files
                if file_path.endswith('.ome.tiff') or file_path.endswith('.ome.tif'):
                    process_ome_tiff(file_path, storage_dir, vips)
                  
                # process tiff files

                if file_path.endswith('.tiff') or file_path.endswith('.tif'):
                  relative_path = os.path.relpath(file_path, import_dir)

                  if os.path.sep in relative_path:
                    print(f"File {file_path} is in a subfolder.")
                    # process the file in the subfolder
                    process_tiff(file_path, storage_dir, vips)

                handler.last_modified.pop(file_path)
                break
        time.sleep(10)

def main():
    print("Starting ImmunoViewer watch folder")
    parser = argparse.ArgumentParser(description="Watch folder and process new files as they are added")
    parser.add_argument('import_dir', nargs='?', help='The data directory to watch for new files (default: %(default)s)', default='/iv-import')
    parser.add_argument('storage_dir', nargs='?', help='The output directory for the processed files (default: %(default)s)', default='/iv-store')
    parser.add_argument('vips', nargs='?', help='Path to the VIPS executable (default: %(default)s)', default='vips')
    parser.add_argument('-t', '--num_cores', type=int, default=4, help='Number of cores to use (default: %(default)s)')
    args = parser.parse_args()

    if not args.import_dir or not args.storage_dir:
        print("Usage: process_folder.py [-t num_cores] import_dir storage_dir vips")
        sys.exit(1)
    
    num_cores = args.num_cores if args.num_cores else 4
    import_dir = Path(args.import_dir)
    storage_dir = Path(args.storage_dir)
    vips = args.vips

    print(f"Watching folder {import_dir} for new files, output to {storage_dir}, and vips location is {vips}")

    handler = Handler()

    observer = Observer()
    observer.schedule(handler, import_dir, recursive=True)
    observer.start()

    # Start the thread for periodic file checking
    file_check_thread = Thread(target=check_files, args=(handler, import_dir, storage_dir, vips))
    file_check_thread.daemon = True
    file_check_thread.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()

    observer.join()

if __name__ == "__main__":
    main()
