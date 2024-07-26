export IV_SLIDE_DIR=/Users/vanijzen/Desktop/iv-store
# export IV_SLIDE_DIR=/Volumes/DATA/iv-store
export IV_IMPORT_DIR=/Users/vanijzen/Desktop/iv-import
export IV_TMP_DIR=/tmp

# python server.py --reload
gunicorn --workers 10 --threads 10 -b :9000 -k uvicorn.workers.UvicornWorker --reload server:app