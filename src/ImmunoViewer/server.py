import pathlib
from io import BytesIO
import os
import json
import cv2
import numpy as np
from pydantic_settings import BaseSettings

from helpers.server_helpers import *

from fastapi import FastAPI, Request, HTTPException, Path, status
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
client_dir = os.path.join(current_folder, "client")
slide_dir = pathlib.Path(settings.SLIDE_DIR)

app.mount("/assets", StaticFiles(directory=os.path.join(client_dir, "assets")), name="assets")
app.mount("/images", StaticFiles(directory=os.path.join(client_dir, "images")), name="images")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join(client_dir, 'favicon.ico'))

@app.get("/", include_in_schema=False)
async def read_root():
    # Serve index.html for the root
    return FileResponse(os.path.join(client_dir, 'index.html'))

@app.get('/samples.json')
async def samples():
    print("looking in ", os.path.abspath(settings.SLIDE_DIR))
    try:
        file_json = find_directories_with_files_folders(os.path.abspath(settings.SLIDE_DIR))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    buf = {
        "samples": file_json,
        "save": settings.SAVE,
        "colors": list(settings.COLORS.keys())
    }

    return JSONResponse(content=buf, status_code=200)

@app.get("/{files}/{chs}/{gains}/{file}.dzi")
async def get_dzi(files: str, chs: str, gains: str, file: str):
    """
    Get the DZI file
    """
    files = files.split(';')
    path_to_dzi = os.path.join(os.path.abspath(settings.SLIDE_DIR), file, f"{files[0].replace('_files', '')}.dzi")
    
    try:
        dzi_content = modify_dzi_format(path_to_dzi)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(content=dzi_content, media_type="application/xml", status_code=200)

@app.get("/{files}/{chs}/{gains}/{file}_files/{level}/{loc}")
async def get_tile(
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
        file_path = slide_dir / file / f'{files[0]}' / str(level) / loc
        merged_image = cv2.imread(str(file_path))
    else:
        merge_images = []
        merge_chs = []
        merge_gains = []



        for i, ch in enumerate(chs):
            if ch != 'empty':

                file_path = slide_dir / file / f'{files[i]}' / str(level) / loc
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