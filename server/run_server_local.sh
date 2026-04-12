export TV_SLIDE_DIR=/Volumes/solid-data2/iv-store3
export TV_IMPORT_DIR=/Volumes/solid-data2/iv-import2
export TV_TMP_DIR=/tmp

# python server.py --reload
gunicorn --workers 10 --threads 10 -b :8000 -k uvicorn.workers.UvicornWorker --reload ome-server:app