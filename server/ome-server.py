import pathlib
import os
import json
import math
from io import BytesIO
from typing import Dict, List, Tuple
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2
import numpy as np
import tifffile
import zarr

from fastapi import FastAPI, Request, HTTPException, Path, status, Query, UploadFile, Form, File, Body
from fastapi.responses import FileResponse, JSONResponse, Response, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import uvicorn
import argparse
import xml.etree.ElementTree as ET


class Settings:
    SLIDE_DIR: str = os.getenv("TV_SLIDE_DIR", "/tv-store")
    TMP_DIR: str = "/tmp"
    SAVE: bool = os.getenv("TV_SAVE", "True").lower() in ("true", "1", "yes")
    COLORS: list = ["red", "green", "blue", "yellow", "magenta", "cyan", "white"]
    HOST: str = os.getenv("TV_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("TV_PORT", "8000"))


settings = Settings()


# Simple color map for channel compositing (BGR order for OpenCV)
COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
    "red": (0, 0, 255),
    "green": (0, 255, 0),
    "blue": (255, 0, 0),
    "yellow": (0, 255, 255),
    "magenta": (255, 0, 255),
    "cyan": (255, 255, 0),
    "white": (255, 255, 255),
}


def get_color(name: str) -> Tuple[int, int, int]:
    return COLOR_MAP.get(name.lower(), COLOR_MAP["white"])


OME_NS = {"ome": "http://www.openmicroscopy.org/Schemas/OME/2016-06"}


def extract_channel_info(tiff_file: tifffile.TiffFile, channel_count: int):
    """
    Return list of {channel_name, channel_number} using OME-XML metadata.
    Falls back to generic names if metadata is missing or incomplete.
    """
    try:
        ome_xml = tiff_file.ome_metadata
        if not ome_xml:
            raise ValueError("No OME metadata")

        root = ET.fromstring(ome_xml)
        channels = []
        for idx, ch in enumerate(root.findall(".//ome:Channel", OME_NS)):
            name = ch.get("Name") or ch.get("ID") or f"Channel {idx}"
            channels.append({"channel_name": name, "channel_number": idx})

        # If XML exists but no channels found, synthesize based on count
        if not channels:
            channels = [{"channel_name": f"Channel {i}", "channel_number": i} for i in range(channel_count)]

        return channels
    except Exception:
        # Robust fallback when parsing fails
        return [{"channel_name": f"Channel {i}", "channel_number": i} for i in range(channel_count)]


class OmeTiffPyramid:
    """
    Lazy loader for OME-TIFF using tifffile + zarr with basic pyramid math for DZI tiles.
    """

    def __init__(self, path: str, tile_size: int = 256):
        self.path = path
        self.tile_size = tile_size
        self._lock = threading.Lock()

        self.tiff = tifffile.TiffFile(path)
        self.series = self.tiff.series[0]
        self.axes = self.series.axes  # e.g., "CYX"

        store = self.series.aszarr()
        root = zarr.open(store, mode="r")

        if isinstance(root, zarr.Array):
            self.levels = [root]
        else:
            # Handle both Zarr 2.x and 3.x Group objects
            arrays = []
            try:
                # Zarr 3.x: .members() returns (name, item) tuples
                if hasattr(root, 'members'):
                    for item in root.members():
                        # members() returns tuples of (name, array)
                        if isinstance(item, tuple):
                            _, array = item
                            if isinstance(array, zarr.Array):
                                arrays.append(array)
                        # In case it returns just the item directly
                        elif isinstance(item, zarr.Array):
                            arrays.append(item)
                # Zarr 2.x: use .items()
                elif hasattr(root, 'items'):
                    for _, v in root.items():
                        if isinstance(v, zarr.Array):
                            arrays.append(v)
                else:
                    # Fallback: try direct iteration over keys
                    for key in list(root.keys()) if hasattr(root, 'keys') else root:
                        item = root[key]
                        if isinstance(item, zarr.Array):
                            arrays.append(item)
            except Exception as e:
                raise ValueError(f"Failed to extract arrays from Zarr group in {os.path.basename(path)}: {e}")
            
            # Sort by resolution (largest first based on width dimension)
            arrays.sort(key=lambda a: a.shape[-1], reverse=True)
            self.levels = arrays

        if not self.levels:
            raise ValueError(f"No arrays found in OME-TIFF {path}")

        self.channel_axis = self.axes.index("C") if "C" in self.axes else None
        self.y_axis = self.axes.index("Y")
        self.x_axis = self.axes.index("X")

        base_shape = self.levels[0].shape
        self.height = base_shape[self.y_axis]
        self.width = base_shape[self.x_axis]
        self.dtype = self.levels[0].dtype
        self.dtype_max = float(np.iinfo(self.dtype).max) if np.issubdtype(self.dtype, np.integer) else 1.0
        self.max_level = math.ceil(math.log2(max(self.width, self.height)))

    def close(self):
        self.tiff.close()

    def dzi_xml(self) -> str:
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Image TileSize="{self.tile_size}" Overlap="0" Format="jpeg" xmlns="http://schemas.microsoft.com/deepzoom/2008">'
            f'<Size Width="{self.width}" Height="{self.height}"/></Image>'
        )

    def _slice_for_region(self, channel: int, y0: int, y1: int, x0: int, x1: int):
        slices = []
        for ax in self.axes:
            if ax == "C":
                slices.append(channel)
            elif ax == "Y":
                slices.append(slice(y0, y1))
            elif ax == "X":
                slices.append(slice(x0, x1))
            else:
                slices.append(0)
        return tuple(slices)

    def _read_patch(self, level_arr, channel: int, y0: int, y1: int, x0: int, x1: int):
        patch = level_arr[self._slice_for_region(channel, y0, y1, x0, x1)]
        return np.asarray(patch)

    def _downscale_to_tile(self, patch: np.ndarray) -> np.ndarray:
        target = (self.tile_size, self.tile_size)
        if patch.shape[-2:] == target:
            return patch
        return cv2.resize(patch, target, interpolation=cv2.INTER_AREA)

    def _normalize(self, patch: np.ndarray, min_val: float = 0.0, max_val: float = 1.0) -> np.ndarray:
        patch = patch.astype(np.float32)
        if self.dtype_max > 0:
            patch = patch / self.dtype_max
        span = max_val - min_val
        if span > 0:
            patch = (patch - min_val) / span
        patch = np.clip(patch, 0.0, 1.0)
        return patch

    def _compose_rgb(self, patches: List[np.ndarray], colors: List[str], gains: List[float], is_rgb: bool, mins: List[float] = None, maxs: List[float] = None) -> np.ndarray:
        h, w = patches[0].shape[-2:]
        rgb = np.zeros((h, w, 3), dtype=np.float32)
        if mins is None:
            mins = [0.0] * len(patches)
        if maxs is None:
            maxs = [1.0] * len(patches)

        if is_rgb and len(patches) >= 3:
            # Treat first three channels as RGB (order: R, G, B)
            for i, channel_patch in enumerate(patches[:3]):
                patch = self._normalize(channel_patch, mins[i], maxs[i])
                rgb[:, :, 2 - i] += patch * gains[i]  # convert RGB -> BGR order
        else:
            for patch, color_name, gain, min_val, max_val in zip(patches, colors, gains, mins, maxs):
                patch_norm = self._normalize(patch, min_val, max_val)
                b, g, r = get_color(color_name)
                # Swap R and B because COLOR_MAP is actually RGB despite comment
                rgb[:, :, 0] += patch_norm * (r / 255.0) * gain  # R value -> B channel
                rgb[:, :, 1] += patch_norm * (g / 255.0) * gain
                rgb[:, :, 2] += patch_norm * (b / 255.0) * gain  # B value -> R channel

        rgb = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
        return rgb

    def get_tile(self, level: int, tile_x: int, tile_y: int, channels: List[int], colors: List[str], gains: List[float], is_rgb: bool, mins: List[float] = None, maxs: List[float] = None) -> np.ndarray:
        if level < 0 or level > self.max_level:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid level")

        # Select the appropriate pyramid level
        # Calculate how many levels down we need to go
        level_downscale = self.max_level - level
        
        # Find the best matching pyramid level
        # Each pyramid level is typically 2x smaller than the previous
        pyramid_level_idx = min(level_downscale // 1, len(self.levels) - 1)
        level_arr = self.levels[pyramid_level_idx]
        
        # Calculate the actual scale factor for this pyramid level
        # If we have multiple pyramid levels, each is typically 2x smaller
        pyramid_scale = 2 ** pyramid_level_idx
        
        # Adjust coordinates for the selected pyramid level
        scale = 2 ** (self.max_level - level)
        x0 = tile_x * self.tile_size * scale // pyramid_scale
        y0 = tile_y * self.tile_size * scale // pyramid_scale
        x1 = min(level_arr.shape[self.x_axis], x0 + (self.tile_size * scale // pyramid_scale))
        y1 = min(level_arr.shape[self.y_axis], y0 + (self.tile_size * scale // pyramid_scale))

        if x0 >= level_arr.shape[self.x_axis] or y0 >= level_arr.shape[self.y_axis]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tile out of bounds")

        with self._lock:
            patches = []
            if self.channel_axis is None:
                # Grayscale data
                patch = level_arr[self._slice_for_region(0, y0, y1, x0, x1)]
                patch = self._downscale_to_tile(np.asarray(patch))
                patches.append(patch)
                colors = colors or ["white"]
                gains = gains or [1.0]
            else:
                for ch in channels:
                    patch = self._read_patch(level_arr, ch, y0, y1, x0, x1)
                    patch = np.squeeze(patch)
                    patch = self._downscale_to_tile(patch)
                    patches.append(patch)

        if not patches:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No channels selected")

        # Extend color/gain/min/max lists if they are shorter than channels
        if len(colors) < len(patches):
            colors = (colors + ["white"] * len(patches))[: len(patches)]
        if len(gains) < len(patches):
            gains = (gains + [1.0] * len(patches))[: len(patches)]
        if mins is None:
            mins = [0.0] * len(patches)
        if maxs is None:
            maxs = [1.0] * len(patches)
        if len(mins) < len(patches):
            mins = (mins + [0.0] * len(patches))[: len(patches)]
        if len(maxs) < len(patches):
            maxs = (maxs + [1.0] * len(patches))[: len(patches)]

        return self._compose_rgb(patches, colors, gains, is_rgb, mins, maxs)


class TiffCache:
    """
    Small LRU cache for open OME-TIFF pyramids to avoid reloading per request.
    """

    def __init__(self, max_items: int = 4):
        self.max_items = max_items
        self.cache: Dict[str, OmeTiffPyramid] = {}
        self.order: List[str] = []
        self._lock = threading.Lock()

    def get(self, path: str) -> OmeTiffPyramid:
        with self._lock:
            if path in self.cache:
                # refresh order
                self.order = [p for p in self.order if p != path]
                self.order.append(path)
                return self.cache[path]

            pyramid = OmeTiffPyramid(path)
            self.cache[path] = pyramid
            self.order.append(path)

            if len(self.order) > self.max_items:
                evict_path = self.order.pop(0)
                evicted = self.cache.pop(evict_path, None)
                if evicted:
                    evicted.close()

            return pyramid

    def clear(self):
        with self._lock:
            for pyramid in self.cache.values():
                pyramid.close()
            self.cache.clear()
            self.order.clear()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_folder = pathlib.Path(__file__).parent.resolve()
client_dir = os.path.join(current_folder, "..", "client", "dist")
slide_dir = pathlib.Path(settings.SLIDE_DIR)
tile_cache = TiffCache(max_items=4)


@app.get("/")
async def root():
    return FileResponse(os.path.join(client_dir, "index.html"))


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(os.path.join(client_dir, "favicon.ico"))


app.mount("/assets", StaticFiles(directory=os.path.join(client_dir, "assets")), name="assets")
app.mount("/images", StaticFiles(directory=os.path.join(client_dir, "images")), name="images")


def get_metadata_json_path(tiff_path: str) -> str:
    """
    Get the path to the metadata.json file for a given OME-TIFF file.
    Follows the same pattern as .sample.json files.
    """
    # Get the directory and base filename
    dir_path = os.path.dirname(tiff_path)
    filename = os.path.basename(tiff_path)
    
    # Remove .ome.tif or .ome.tiff extension to get base name
    if filename.lower().endswith('.ome.tiff'):
        base_name = filename[:-9]  # Remove '.ome.tiff'
    elif filename.lower().endswith('.ome.tif'):
        base_name = filename[:-8]  # Remove '.ome.tif'
    else:
        base_name = filename
    
    # Return path following same pattern as .sample.json
    return os.path.join(dir_path, f"{base_name}.metadata.json")


def load_metadata_from_cache(tiff_path: str) -> dict:
    """
    Load metadata from .metadata.json cache file if it exists.
    Returns None if cache doesn't exist or is invalid.
    """
    metadata_path = get_metadata_json_path(tiff_path)
    if not os.path.exists(metadata_path):
        return None
    
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        # Verify the cache is for the same file by checking file modification time
        tiff_mtime = os.path.getmtime(tiff_path)
        if 'file_mtime' in metadata and metadata['file_mtime'] == tiff_mtime:
            return metadata.get('metadata', metadata)  # Support both formats
        else:
            # Cache is stale, return None to regenerate
            return None
    except (json.JSONDecodeError, IOError, OSError) as e:
        print(f"Error reading metadata cache {metadata_path}: {e}")
        return None


def save_metadata_to_cache(tiff_path: str, metadata: dict):
    """
    Save metadata to .metadata.json cache file.
    Follows the same pattern as .sample.json files.
    """
    metadata_path = get_metadata_json_path(tiff_path)
    try:
        # Include file modification time for cache validation
        cache_data = {
            'file_mtime': os.path.getmtime(tiff_path),
            'metadata': metadata
        }
        with open(metadata_path, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except (IOError, OSError) as e:
        print(f"Error saving metadata cache {metadata_path}: {e}")


def extract_metadata_lightweight(path: str) -> dict:
    """
    Extract minimal metadata from OME-TIFF without loading full pyramid.
    Much faster than creating OmeTiffPyramid for file listing.
    """
    try:
        with tifffile.TiffFile(path) as tiff:
            series = tiff.series[0]
            axes = series.axes
            
            # Get shape from series (doesn't load data)
            shape = series.shape
            axes_list = list(axes)
            
            # Determine axis indices
            channel_axis = axes_list.index("C") if "C" in axes_list else None
            y_axis = axes_list.index("Y")
            x_axis = axes_list.index("X")
            
            # Extract dimensions
            height = shape[y_axis]
            width = shape[x_axis]
            channel_count = shape[channel_axis] if channel_axis is not None else 1
            dtype = series.dtype
            
            # Extract channel info from OME-XML
            channel_info = extract_channel_info(tiff, channel_count)
            
            return {
                "axes": axes,
                "shape": [height, width],
                "dtype": str(dtype),
                "channels": channel_count,
                "channel_info": channel_info,
            }
    except Exception as e:
        raise ValueError(f"Failed to read metadata from {os.path.basename(path)}: {e}")


def get_metadata_for_file(tiff_path: str, use_cache: bool = True) -> dict:
    """
    Get metadata for an OME-TIFF file, using cache if available.
    
    Args:
        tiff_path: Path to the OME-TIFF file
        use_cache: If True, use cached metadata if available and valid
    
    Returns:
        Dictionary containing metadata
    """
    # Try to load from cache first
    if use_cache:
        cached_metadata = load_metadata_from_cache(tiff_path)
        if cached_metadata is not None:
            return cached_metadata
    
    # Generate metadata from file
    metadata = extract_metadata_lightweight(tiff_path)
    
    # Save to cache
    if use_cache:
        save_metadata_to_cache(tiff_path, metadata)
    
    return metadata


def generate_metadata_for_new_file(tiff_path: str):
    """
    Generate and save metadata.json for a newly added OME-TIFF file.
    This can be called when a new file is detected.
    Creates {name}.metadata.json next to the OME-TIFF file.
    """
    if not os.path.exists(tiff_path):
        raise FileNotFoundError(f"File not found: {tiff_path}")
    
    if not (tiff_path.lower().endswith('.ome.tif') or tiff_path.lower().endswith('.ome.tiff')):
        raise ValueError(f"File is not an OME-TIFF: {tiff_path}")
    
    try:
        metadata = extract_metadata_lightweight(tiff_path)
        save_metadata_to_cache(tiff_path, metadata)
        print(f"Generated metadata cache for {os.path.basename(tiff_path)}")
    except Exception as e:
        print(f"Failed to generate metadata for {tiff_path}: {e}")
        raise


def _process_single_file(entry: os.DirEntry, base_dir: str) -> dict:
    """
    Process a single OME-TIFF file and return dataset info.
    Used as a worker function for parallel processing.
    """
    try:
        # Use cached metadata if available
        metadata = get_metadata_for_file(entry.path, use_cache=True)
        
        dataset_info = {
            "name": entry.name.rsplit(".ome", 1)[0],
            "details": {},
            "metadata": [metadata],
        }
        
        # Load .sample.json if it exists (same pattern as metadata.json)
        sample_json_path = os.path.join(base_dir, f"{dataset_info['name']}.sample.json")
        if os.path.exists(sample_json_path):
            with open(sample_json_path, "r") as f:
                dataset_info["details"] = json.load(f)
        
        return dataset_info
    except Exception as e:
        print(f"Error loading {entry.path}: {e}")
        return None


def find_ome_tiffs(base_dir: str) -> list:
    """
    Finds all OME-TIFF files in base_dir at depth 1.
    Uses lightweight metadata extraction with parallel processing and caching.
    Metadata is cached in {name}.metadata.json files, same pattern as .sample.json
    """
    ome_files = []

    if not os.path.exists(base_dir):
        return []

    # Collect all OME-TIFF files first
    entries = []
    with os.scandir(base_dir) as dir_entries:
        for entry in dir_entries:
            if entry.is_file() and (entry.name.lower().endswith(".ome.tif") or entry.name.lower().endswith(".ome.tiff")):
                entries.append(entry)
    
    # Process files in parallel
    # Use max_workers=None to use min(32, num_files) workers
    with ThreadPoolExecutor(max_workers=None) as executor:
        # Submit all tasks
        future_to_entry = {
            executor.submit(_process_single_file, entry, base_dir): entry 
            for entry in entries
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_entry):
            result = future.result()
            if result is not None:
                ome_files.append(result)

    return ome_files


@app.get("/histogram/{location}/{channel}/{file}")
async def get_histogram(location: str, channel: int, file: str):
    """
    Return a 64-bin histogram of normalized pixel values for a single channel
    across the full image. Uses the lowest-resolution pyramid level for fast
    full-image coverage.
    Response: { "bins": [count0, ..., count63] }
    """
    path_to_tiff = os.path.join(settings.SLIDE_DIR, location, f"{file}.ome.tiff")
    if not os.path.exists(path_to_tiff):
        path_to_tiff = os.path.join(settings.SLIDE_DIR, location, f"{file}.ome.tif")
    if not os.path.exists(path_to_tiff):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OME-TIFF not found")

    pyramid = tile_cache.get(path_to_tiff)

    # Use the smallest (lowest-resolution) pyramid level for full coverage
    level_arr = pyramid.levels[-1]

    with pyramid._lock:
        if pyramid.channel_axis is not None:
            patch = level_arr[pyramid._slice_for_region(channel, 0, level_arr.shape[pyramid.y_axis], 0, level_arr.shape[pyramid.x_axis])]
        else:
            patch = level_arr[:]

    arr = np.asarray(patch, dtype=np.float32)
    flat = arr.flatten() / pyramid.dtype_max
    counts, _ = np.histogram(flat, bins=64, range=(0.0, 1.0))
    return JSONResponse(content={"bins": counts.tolist()})


@app.get("/samples.json")
async def samples(location: str = Query("public", description="Location to search for samples")):
    search_dir = os.path.join(settings.SLIDE_DIR, location)
    print(f"Searching for samples in {search_dir}")
    file_json = find_ome_tiffs(os.path.abspath(search_dir))

    buf = {"samples": file_json, "save": settings.SAVE, "colors": settings.COLORS}
    return JSONResponse(content=buf, status_code=200)


@app.get("/{location}/{chs}/{rgb}/{colors}/{gains}/{mins}/{maxs}/{file}.dzi")
async def get_dzi_windowed(
    location: str,
    chs: str,
    rgb: str,
    colors: str,
    gains: str,
    mins: str,
    maxs: str,
    file: str,
):
    return await get_dzi(location, chs, rgb, colors, gains, file)


@app.get("/{location}/{chs}/{rgb}/{colors}/{gains}/{mins}/{maxs}/{file}_files/{level}/{loc_x}_{loc_y}.jpeg")
async def get_tile_windowed(
    location: str,
    chs: str,
    rgb: bool,
    colors: str,
    gains: str,
    mins: str,
    maxs: str,
    file: str,
    level: int,
    loc_x: int,
    loc_y: int,
):
    path_to_tiff = os.path.join(settings.SLIDE_DIR, location, f"{file}.ome.tiff")
    if not os.path.exists(path_to_tiff):
        path_to_tiff = os.path.join(settings.SLIDE_DIR, location, f"{file}.ome.tif")
    if not os.path.exists(path_to_tiff):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OME-TIFF not found")

    pyramid = tile_cache.get(path_to_tiff)

    channels = [int(x) for x in chs.split(";") if x != ""]
    colors_list = [c for c in colors.split(";") if c != ""]
    gains_list = [float(x) for x in gains.split(";") if x != ""]
    mins_list = [float(x) for x in mins.split(";") if x != ""]
    maxs_list = [float(x) for x in maxs.split(";") if x != ""]

    tile = pyramid.get_tile(level, loc_x, loc_y, channels, colors_list, gains_list, rgb, mins_list, maxs_list)

    tile_rgb = cv2.cvtColor(tile, cv2.COLOR_BGR2RGB)
    img_bytes = cv2.imencode(".jpeg", tile_rgb)[1].tobytes()
    img_io = BytesIO(img_bytes)

    return Response(content=img_io.getvalue(), media_type="image/jpeg")


@app.get("/{location}/{chs}/{rgb}/{colors}/{gains}/{file}.dzi")
async def get_dzi(
    location: str,
    chs: str,
    rgb: str,  # Change to str
    colors: str,
    gains: str,
    file: str,
):
    path_to_tiff = os.path.join(settings.SLIDE_DIR, location, f"{file}.ome.tiff")
    if not os.path.exists(path_to_tiff):
        path_to_tiff = os.path.join(settings.SLIDE_DIR, location, f"{file}.ome.tif")
    if not os.path.exists(path_to_tiff):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OME-TIFF not found")

    # print('start loading tile_cache')
    pyramid = tile_cache.get(path_to_tiff)
    # print('done loading tile_cache')
    # print('start getting content')
    dzi_content = pyramid.dzi_xml()
    # print('done getting content for dzi')
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
    loc_y: int,
):
    path_to_tiff = os.path.join(settings.SLIDE_DIR, location, f"{file}.ome.tiff")
    if not os.path.exists(path_to_tiff):
        path_to_tiff = os.path.join(settings.SLIDE_DIR, location, f"{file}.ome.tif")
    if not os.path.exists(path_to_tiff):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OME-TIFF not found")
    
    # print('start loading tile_cache')
    pyramid = tile_cache.get(path_to_tiff)
    # print('done loading tile_cache')

    channels = [int(x) for x in chs.split(";") if x != ""]
    colors_list = [c for c in colors.split(";") if c != ""]
    gains_list = [float(x) for x in gains.split(";") if x != ""]

    # start_time = time.time()
    # print('start getting tile')
    tile = pyramid.get_tile(level, loc_x, loc_y, channels, colors_list, gains_list, rgb)
    # print('done getting tile')
    # end_time = time.time()
    # print(f'time taken: {end_time - start_time} seconds')

    # print('convert tile')
    tile_rgb = cv2.cvtColor(tile, cv2.COLOR_BGR2RGB)
    img_bytes = cv2.imencode(".jpeg", tile_rgb)[1].tobytes()
    img_io = BytesIO(img_bytes)
    # print('done converting tile')

    return Response(content=img_io.getvalue(), media_type="image/jpeg")


@app.post("/save/{location}/{file}", response_class=PlainTextResponse)
async def save_slide_settings(location: str, file: str, request: Request):
    """
    Save the slide settings alongside the OME-TIFF.
    """
    if not settings.SAVE:
        return PlainTextResponse("SAVE BLOCKED", status_code=status.HTTP_403_FORBIDDEN)

    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    file_path = slide_dir / location / f"{file}.sample.json"

    with open(file_path, "w") as f:
        json.dump(data, f)

    return "OK"


def main(host: str = "127.0.0.1", port: int = 8000, reload: bool = True):
    """Run the OME-TIFF API server with Uvicorn."""
    print(f"Starting OME-TIFF server at http://{host}:{port}")
    print(f"Slide_dir: {settings.SLIDE_DIR}")
    print(f"Save: {settings.SAVE}")
    uvicorn.run("ome-server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main(host=settings.HOST, port=settings.PORT, reload=True)

