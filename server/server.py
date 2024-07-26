import pathlib
from io import BytesIO
import os
import json
import cv2
import numpy as np
from pydantic_settings import BaseSettings
from pydantic import BaseModel
import shutil
import subprocess

from helpers.server_helpers import *

from fastapi import FastAPI, Request, HTTPException, Path, status, Query, UploadFile, Form, File, Body
from fastapi.responses import FileResponse, JSONResponse, Response, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import uvicorn
import argparse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Settings(BaseSettings):
    SLIDE_DIR: str = "/iv-store"
    IMPORT_DIR: str = "/iv-import"
    TMP_DIR: str = "/tmp"
    DU_LOC: str = "/usr/bin/du"
    RM_LOC: str = "/usr/bin/rm"
    SAVE: bool = False
    COLORS: dict = {
        'green': (0, 255, 0),
        'red': (0, 0, 255),
        'blue': (255, 0, 0),
        'yellow': (0, 255, 255),
        'cyan': (255, 255, 0),
        'magenta': (255, 0, 255),
        'white': (255, 255, 255),
        'black': (0, 0, 0),
    }
    class Config:
        env_prefix = "IV_"

settings = Settings()

def main(host="127.0.0.1", port=8000, reload=False):
    """Run the API server with Uvicorn."""
    uvicorn.run("server:app", host=host, port=port, reload=reload)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ImmunoViewer server.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host for the API server")
    parser.add_argument("--port", type=int, default=8000, help="Port for the API server")
    parser.add_argument("--reload", action="store_true", help="Enable automatic reload")
    parser.add_argument("--save", action="store_true", help="Enable saving of slide settings")
    parser.add_argument("--slide-dir", type=str, help="Directory to store slide files")
    args = parser.parse_args()

    if args.save:
        settings.SAVE = True

    if args.slide_dir:
        settings.SLIDE_DIR = args.slide_dir
        
    main(host=args.host, port=args.port, reload=args.reload)

current_folder = pathlib.Path(__file__).parent.resolve()
client_dir = os.path.join(current_folder, "..", "client", "dist")
slide_dir = pathlib.Path(settings.SLIDE_DIR)

@app.get("/")
async def root():
    return FileResponse(os.path.join(client_dir, "index.html"))

@app.get("/favicon.ico")
async def favicon():
    return FileResponse(os.path.join(client_dir, "favicon.ico"))

app.mount("/assets", StaticFiles(directory=os.path.join(client_dir, "assets")), name="assets")
app.mount("/images", StaticFiles(directory=os.path.join(client_dir, "images")), name="images")

@app.get('/samples.json')
async def samples(location: str = Query('public', description="Location to search for samples")):
    print("getting samples.json")
    print("location: ", location)
    # Determine the directory to search based on the location parameter
    search_dir = os.path.join(settings.SLIDE_DIR, location)

    print("looking in ", os.path.abspath(search_dir))
    
    try:
        file_json = find_directories_with_files_folders(os.path.abspath(search_dir))
    except:
        file_json = []

    buf = {
        "samples": file_json,
        "save": settings.SAVE,
        "colors": list(settings.COLORS.keys())
    }

    return JSONResponse(content=buf, status_code=200)

@app.get("/{location}/{files}/{chs}/{gains}/{file}.dzi")
async def get_dzi(location: str, files: str, chs: str, gains: str, file: str):
    """
    Get the DZI file
    """
    files = files.split(';')
    path_to_dzi = os.path.join(os.path.abspath(settings.SLIDE_DIR), location, file, f"{files[0].replace('_files', '')}.dzi")

    print("path to dzi: ", path_to_dzi)
    
    try:
        dzi_content = modify_dzi_format(path_to_dzi)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(content=dzi_content, media_type="application/xml", status_code=200)

@app.get("/{location}/{files}/{chs}/{gains}/{file}_files/{level}/{loc}")
async def get_tile(
    location: str,
    files: str, 
    chs: str, 
    gains: str, 
    file: str = Path(..., description="The base name of the file without extension"),
    level: int = Path(..., description="The image pyramid level"), 
    loc: str = Path(..., description="Location of the tile with extension")
):
    """
    Get a tile from the slide
    """

    loc = loc.replace('.jpeg', '.tiff')
    files = files.split(';') 
    chs = chs.split(';')
    gains = gains.split(';')
    gains = [int(x) for x in gains]

    if len(files) == 1:
        loc = loc.replace('.tiff', '.jpg')
        file_path = slide_dir / location / file / f'{files[0]}' / str(level) / loc
        merged_image = cv2.imread(str(file_path))
    else:
        merge_images = []
        merge_chs = []
        merge_gains = []



        for i, ch in enumerate(chs):
            if ch != 'empty':

                file_path = slide_dir / location / file / f'{files[i]}' / str(level) / loc
                buf = cv2.imread(str(file_path))

                buf = cv2.cvtColor(buf, cv2.COLOR_BGR2GRAY)
                merge_images.append(buf)
                merge_chs.append(ch)
                merge_gains.append(gains[i])


        if len(merge_images) == 0:
            merged_image = np.zeros((256, 256), dtype=np.uint8)
        else:
            merged_image = mix_channels(merge_images, merge_chs, merge_gains, settings.COLORS)

    img_bytes = cv2.imencode('.jpeg', merged_image)[1].tobytes()
    img_io = BytesIO(img_bytes)

    return Response(content=img_io.getvalue(), media_type='image/jpeg')

@app.post("/save/{file:path}", response_class=PlainTextResponse)
async def save_slide_settings(file: str, request: Request):
    """
    Save the slide settings
    """
    if settings.SAVE:
        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

        file_path = slide_dir / file / 'sample.json'

        with open(file_path, 'w') as f:
            json.dump(data, f)

        return "OK"
    else:
        return PlainTextResponse("SAVE BLOCKED", status_code=status.HTTP_403_FORBIDDEN)
    
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),  # File to be uploaded
    name: str = Form(...),  # Name of the file
    chunk_number: int = Form(0),  # Current chunk number
    total_chunks: int = Form(1),  # Total number of chunks
):
    """
    Handles file uploads with chunked transfer
    (if total_chunks > 1) or single-file upload.

    Raises:
        HTTPException: If a validation error occurs
        (e.g., missing data, invalid file size).
    """

    # check if allowed file type
    if not (name.lower().endswith('.svs') or name.lower().endswith('.tiff') or name.lower().endswith('.tif')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .svs, .tiff, and .tif files are allowed.")
    
    isLast = (int(chunk_number) + 1) == int(
        total_chunks
    )  # Check if it's the last chunk

    file_name = f"{name}_{chunk_number}"  # Generate a unique file name for the chunk

    # Write the chunk to a file in the 'chunks' directory
    with open(f"{settings.TMP_DIR}/{file_name}", "wb") as buffer:
        buffer.write(await file.read())
    buffer.close()

    if isLast:  # If it's the last chunk, concatenate all chunks into the final file
        if not os.path.exists(f"{settings.IMPORT_DIR}/public"):
            os.makedirs(f"{settings.IMPORT_DIR}/public")
        with open(f"{settings.IMPORT_DIR}/public/{name}", "wb") as buffer:
            chunk = 0
            while chunk < total_chunks:
                with open(f"{settings.TMP_DIR}/{name}_{chunk}", "rb") as infile:
                    buffer.write(infile.read())  # Write the chunk to the final file
                    infile.close()
                os.remove(f"{settings.TMP_DIR}/{name}_{chunk}")  # Remove the chunk file
                chunk += 1
        buffer.close()
        return JSONResponse(
            {"message": "File Uploaded"}, status_code=status.HTTP_200_OK
        )

    return JSONResponse(
        {"message": "Chunk Uploaded"}, status_code=status.HTTP_200_OK)


@app.post("/sampleStats")
async def sample_stats():
    """
    Get a list of files in the import directory.
    """
    files_path = os.path.join(settings.SLIDE_DIR, "public")

    print("looking in ", files_path)

    if not os.path.exists(files_path):
        return JSONResponse(
            {"samples": [], "dataUsed": 0},
            status_code=status.HTTP_200_OK,
        )

    folders = [f for f in os.listdir(files_path) if os.path.isdir(os.path.join(files_path, f))]

    for folder in folders:
        sample_json_path = os.path.join(files_path, folder, 'sample.json')
        if not os.path.exists(sample_json_path):
            folders.remove(folder)
    
    result = subprocess.run([settings.DU_LOC, '-s', files_path], capture_output=True, text=True)
    data_used = int(result.stdout.split()[0])*512
    data_used_gb = data_used / (1024**3)
    data_used_gb = round(data_used_gb, 2)

    return JSONResponse(
        {"samples": folders, "dataUsed": data_used_gb},
        status_code=status.HTTP_200_OK,
    )

class DeleteRequest(BaseModel):
    sample: str

@app.post("/deleteSample")
async def delete_sample(delete_request: DeleteRequest):
    """
    Delete a sample from the import directory.
    """
    files_path = os.path.join(settings.SLIDE_DIR, delete_request.sample)

    if not os.path.exists(files_path):
        return JSONResponse(
            {"message": "Sample not found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    result = subprocess.run([settings.RM_LOC, '-rf', files_path], capture_output=True, text=True)

    return JSONResponse(
        {"message": "Samples deleted"},
        status_code=status.HTTP_200_OK,
    )