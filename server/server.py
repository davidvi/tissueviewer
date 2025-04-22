import pathlib
from io import BytesIO
import os
import json
import cv2
from pydantic_settings import BaseSettings
from pydantic import BaseModel
import subprocess
import glob

from OmeZarrConnector.connector.connect import OmeZarrConnector

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
    SLIDE_DIR: str = "/tv-store"
    IMPORT_DIR: str = "/tv-import"
    TMP_DIR: str = "/tmp"
    DU_LOC: str = "/usr/bin/du"
    RM_LOC: str = "/bin/rm"
    SAVE: bool = False
    COLORS: list = ["red", "green", "blue", "yellow", "magenta", "cyan", "white"]
    ALLOWED_EXTENSIONS: list = ['.1sc', '.2', '.3', '.4', '.afm', '.afi', '.aim', '.al3d', '.am', '.amiramesh',
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
                                '.vws', '.wat', '.wlz', '.xdce', '.xml', '.xqs', '.xv', '.zfp', '.zfr', '.zip', '.zvi']

    class Config:
        env_prefix = "TV_"

settings = Settings()

def main(host="127.0.0.1", port=8000, reload=True):
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

def find_zarr_datasets(base_dir) -> list:
    """
    Finds all Zarr datasets in base_dir at depth 1
    :param base_dir: base directory to search in
    :return: list of dictionaries containing Zarr dataset information
    """
    zarr_datasets = []

    # Get immediate subdirectories
    with os.scandir(base_dir) as entries:
        for entry in entries:
            try:
              if entry.is_dir() and entry.name.endswith('.zarr'):

                  print("entry path: ", entry.path)
                  
                  ome_connection = OmeZarrConnector(entry.path)

                  dataset_info = {
                      'name': entry.name[:-5],  # Remove '.zarr' from the name
                      'details': {},
                      'metadata': ome_connection.metadata
                  }

                  # Try to load sample.json if it exists
                  sample_json_path = os.path.join(entry.path, 'sample.json')
                  if os.path.exists(sample_json_path):
                      with open(sample_json_path, 'r') as f:
                          dataset_info['details'] = json.load(f)

                  zarr_datasets.append(dataset_info)
            except:
              pass

    return zarr_datasets

@app.get('/samples.json')
async def samples(location: str = Query('public', description="Location to search for samples")):
    print("getting samples.json")
    print("location: ", location)
    # Determine the directory to search based on the location parameter
    search_dir = os.path.join(settings.SLIDE_DIR, location)

    print("looking in ", os.path.abspath(search_dir))
    
    file_json = find_zarr_datasets(os.path.abspath(search_dir))

    buf = {
        "samples": file_json,
        "save": settings.SAVE,
        "colors": settings.COLORS
    }

    print("bu samples: ", buf)

    return JSONResponse(content=buf, status_code=200)

@app.get("/{location}/{chs}/{rgb}/{colors}/{gains}/{file}.dzi")
async def get_dzi(
    location: str,
    chs: str, 
    rgb: bool,
    colors: str,
    gains: str,
    file: str
):
    """
    Get the DZI file
    """
    path_to_zarr = os.path.join(settings.SLIDE_DIR, location, file + ".zarr")
    print("path to zarr: ", path_to_zarr)
    ome_connection = OmeZarrConnector(path_to_zarr)

    dzi_content = ome_connection.generate_dzi(0)

    return Response(content=dzi_content, media_type="application/xml", status_code=200)

@app.get("/{location}/{chs}/{rgb}/{colors}/{gains}/{file}_files/{level}/{loc_x}_{loc_y}.jpeg")
async def get_tile(
    location: str,
    chs: str, 
    rgb: bool, 
    colors: str, 
    gains: str,
    file: str,
    level: int,
    loc_x: int,
    loc_y: int
):
    """
    Get a tile from the slide
    """

    path_to_zarr = os.path.join(settings.SLIDE_DIR, location, file + ".zarr")
    ome_connection = OmeZarrConnector(path_to_zarr)

    channels = chs.split(';')
    channels = [int(x) for x in channels]
    colors = colors.split(';')
    gains = gains.split(';')
    gains = [float(x) for x in gains]


    tile = ome_connection.get_combined_image( 
                         image_id = 0, 
                         dzi_zoom_level = level, 
                         channels = channels, 
                         intensities=gains, 
                         colors=colors, 
                         is_rgb = rgb, 
                         tile_x = loc_x, 
                         tile_y = loc_y)
    
    tile_rgb = cv2.cvtColor(tile, cv2.COLOR_BGR2RGB)
    img_bytes = cv2.imencode('.jpeg', tile_rgb)[1].tobytes()
    img_io = BytesIO(img_bytes)

    return Response(content=img_io.getvalue(), media_type='image/jpeg')

@app.post("/save/{location}/{file}", response_class=PlainTextResponse)
async def save_slide_settings(location: str, file: str, request: Request):
    """
    Save the slide settings
    """
    if settings.SAVE:
        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")
        
        file_name = file + ".zarr"
        file_path = slide_dir / location / file_name / 'sample.json'

        with open(file_path, 'w') as f:
            json.dump(data, f)

        return "OK"
    else:
        return PlainTextResponse("SAVE BLOCKED", status_code=status.HTTP_403_FORBIDDEN)
    
@app.post("/uploadSample")
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
    if not any(name.lower().endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed extensions are: {', '.join(settings.ALLOWED_EXTENSIONS)}")
    
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
    sample_name = delete_request.sample[:-5] if delete_request.sample.lower().endswith('.zarr') else delete_request.sample

    files_path_storage = os.path.join(settings.SLIDE_DIR, "public", sample_name + '.zarr')
    file_path_import_pattern = os.path.join(settings.IMPORT_DIR, "public", sample_name + ".*")

    storage_exists = os.path.exists(files_path_storage)
    import_files = glob.glob(file_path_import_pattern)

    if not storage_exists and not import_files:
        return JSONResponse(
            {"message": "Sample not found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    if storage_exists:
        subprocess.run([settings.RM_LOC, '-rf', files_path_storage], capture_output=True, text=True)
    
    for file_path in import_files:
        subprocess.run([settings.RM_LOC, '-f', file_path], capture_output=True, text=True)

    return JSONResponse(
        {"message": "Sample deleted from storage and import directories"},
        status_code=status.HTTP_200_OK,
    )