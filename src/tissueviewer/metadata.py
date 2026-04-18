"""Metadata extraction + on-disk ``.metadata.json`` sidecar cache."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import tifffile

from .formats.ome_tiff import extract_channel_info


logger = logging.getLogger(__name__)


def strip_ome_extension(filename: str) -> str:
    """Remove ``.ome.tif`` or ``.ome.tiff`` (case-insensitive)."""
    lower = filename.lower()
    if lower.endswith(".ome.tiff"):
        return filename[:-9]
    if lower.endswith(".ome.tif"):
        return filename[:-8]
    return filename


def get_metadata_json_path(tiff_path: str) -> str:
    """Return path to the ``.metadata.json`` sidecar for an OME-TIFF."""
    dir_path = os.path.dirname(tiff_path)
    filename = os.path.basename(tiff_path)
    base_name = strip_ome_extension(filename)
    return os.path.join(dir_path, f"{base_name}.metadata.json")


def get_sample_json_path(tiff_path: str) -> str:
    """Return path to the user-editable ``.sample.json`` sidecar."""
    dir_path = os.path.dirname(tiff_path)
    filename = os.path.basename(tiff_path)
    base_name = strip_ome_extension(filename)
    return os.path.join(dir_path, f"{base_name}.sample.json")


def load_metadata_from_cache(tiff_path: str) -> Optional[dict]:
    """Load cached metadata if it exists and matches the file mtime."""
    metadata_path = get_metadata_json_path(tiff_path)
    if not os.path.exists(metadata_path):
        return None

    try:
        with open(metadata_path, "r", encoding="utf-8") as fh:
            metadata = json.load(fh)
        tiff_mtime = os.path.getmtime(tiff_path)
        if "file_mtime" in metadata and metadata["file_mtime"] == tiff_mtime:
            return metadata.get("metadata", metadata)  # support both formats
        return None
    except (json.JSONDecodeError, IOError, OSError) as exc:
        logger.warning("Error reading metadata cache %s: %s", metadata_path, exc)
        return None


def save_metadata_to_cache(tiff_path: str, metadata: dict) -> None:
    """Persist metadata next to the OME-TIFF. Logged-and-swallowed on failure."""
    metadata_path = get_metadata_json_path(tiff_path)
    try:
        cache_data = {
            "file_mtime": os.path.getmtime(tiff_path),
            "metadata": metadata,
        }
        with open(metadata_path, "w", encoding="utf-8") as fh:
            json.dump(cache_data, fh, indent=2)
    except (IOError, OSError) as exc:
        logger.warning("Error saving metadata cache %s: %s", metadata_path, exc)


def extract_metadata_lightweight(path: str) -> dict:
    """Read OME-TIFF metadata without opening a full pyramid.

    Much faster than instantiating ``OmeTiffPyramid`` and is used during
    directory scans.
    """
    try:
        with tifffile.TiffFile(path) as tiff:
            series = tiff.series[0]
            axes = series.axes
            shape = series.shape
            axes_list = list(axes)

            channel_axis = axes_list.index("C") if "C" in axes_list else None
            y_axis = axes_list.index("Y")
            x_axis = axes_list.index("X")

            height = shape[y_axis]
            width = shape[x_axis]
            channel_count = shape[channel_axis] if channel_axis is not None else 1
            dtype = series.dtype

            channel_info = extract_channel_info(tiff, channel_count)

            return {
                "axes": axes,
                "shape": [height, width],
                "dtype": str(dtype),
                "channels": channel_count,
                "channel_info": channel_info,
            }
    except Exception as exc:
        raise ValueError(
            f"Failed to read metadata from {os.path.basename(path)}: {exc}"
        ) from exc


def get_metadata_for_file(tiff_path: str, use_cache: bool = True) -> dict:
    """Return metadata for an OME-TIFF, caching on disk when possible."""
    if use_cache:
        cached = load_metadata_from_cache(tiff_path)
        if cached is not None:
            return cached

    metadata = extract_metadata_lightweight(tiff_path)

    if use_cache:
        save_metadata_to_cache(tiff_path, metadata)

    return metadata


def generate_metadata_for_new_file(tiff_path: str) -> None:
    """Force (re)generation of ``.metadata.json`` for a given OME-TIFF."""
    if not os.path.exists(tiff_path):
        raise FileNotFoundError(f"File not found: {tiff_path}")
    name_lower = tiff_path.lower()
    if not (name_lower.endswith(".ome.tif") or name_lower.endswith(".ome.tiff")):
        raise ValueError(f"File is not an OME-TIFF: {tiff_path}")

    metadata = extract_metadata_lightweight(tiff_path)
    save_metadata_to_cache(tiff_path, metadata)
    logger.info("Generated metadata cache for %s", os.path.basename(tiff_path))


__all__ = [
    "get_metadata_json_path",
    "get_sample_json_path",
    "strip_ome_extension",
    "load_metadata_from_cache",
    "save_metadata_to_cache",
    "extract_metadata_lightweight",
    "get_metadata_for_file",
    "generate_metadata_for_new_file",
]
