export IV_SLIDE_DIR=/Users/vanijzen/Desktop/iv-store
# export IV_SLIDE_DIR=/Volumes/DATA/iv-store
export IV_IMPORT_DIR=/Users/vanijzen/Desktop/iv-import
export IV_TMP_DIR=/tmp
export IV_COMPLETED_DIR=/Users/vanijzen/Desktop/iv-completed
export vips=/opt/homebrew/bin/vips

python watch_folder.py $IV_IMPORT_DIR $IV_SLIDE_DIR $IV_COMPLETED_DIR $vips