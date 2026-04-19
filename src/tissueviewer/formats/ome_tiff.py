"""OME-TIFF pyramid reader and LRU cache.

Ported verbatim from the original ``server/ome-server.py`` with minimal
changes: ``print`` → ``logger``, removal of Docker-specific path assumptions,
and an explicit ``tile_size`` argument wired through ``Config``.
"""

from __future__ import annotations

import logging
import math
import os
import threading
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import tifffile
import zarr
from fastapi import HTTPException, status


logger = logging.getLogger(__name__)


# BGR tuples used by the compositor. Despite the naming, the original code
# treats these as RGB at mix time (see `_compose_rgb` comments). Do not
# "clean up" without visual verification — the tile output depends on it.
COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
    "red": (0, 0, 255),
    "green": (0, 255, 0),
    "blue": (255, 0, 0),
    "yellow": (0, 255, 255),
    "magenta": (255, 0, 255),
    "cyan": (255, 255, 0),
    "white": (255, 255, 255),
}


OME_NS = {"ome": "http://www.openmicroscopy.org/Schemas/OME/2016-06"}


def get_color(name: str) -> Tuple[int, int, int]:
    return COLOR_MAP.get(name.lower(), COLOR_MAP["white"])


def extract_channel_info(tiff_file: tifffile.TiffFile, channel_count: int):
    """Return ``[{channel_name, channel_number}, ...]`` from OME-XML.

    Falls back to generic names if metadata is absent or malformed.
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

        if not channels:
            channels = [
                {"channel_name": f"Channel {i}", "channel_number": i}
                for i in range(channel_count)
            ]

        return channels
    except Exception:
        return [
            {"channel_name": f"Channel {i}", "channel_number": i}
            for i in range(channel_count)
        ]


class OmeTiffPyramid:
    """Lazy reader for OME-TIFF using tifffile + zarr for DZI tile service."""

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
                if hasattr(root, "members"):
                    for item in root.members():
                        if isinstance(item, tuple):
                            _, array = item
                            if isinstance(array, zarr.Array):
                                arrays.append(array)
                        elif isinstance(item, zarr.Array):
                            arrays.append(item)
                # Zarr 2.x: use .items()
                elif hasattr(root, "items"):
                    for _, v in root.items():
                        if isinstance(v, zarr.Array):
                            arrays.append(v)
                else:
                    # Fallback: try direct iteration over keys
                    keys = list(root.keys()) if hasattr(root, "keys") else root
                    for key in keys:
                        item = root[key]
                        if isinstance(item, zarr.Array):
                            arrays.append(item)
            except Exception as exc:
                raise ValueError(
                    f"Failed to extract arrays from Zarr group in "
                    f"{os.path.basename(path)}: {exc}"
                )

            # Sort by resolution (largest first based on width dimension).
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
        self.dtype_max = (
            float(np.iinfo(self.dtype).max)
            if np.issubdtype(self.dtype, np.integer)
            else 1.0
        )
        self.max_level = math.ceil(math.log2(max(self.width, self.height)))

    # ------------------------------------------------------------------
    def close(self) -> None:
        try:
            self.tiff.close()
        except Exception:  # pragma: no cover - best-effort close
            logger.debug("Error closing TIFF %s", self.path, exc_info=True)

    def dzi_xml(self) -> str:
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Image TileSize="{self.tile_size}" Overlap="0" Format="jpeg" '
            f'xmlns="http://schemas.microsoft.com/deepzoom/2008">'
            f'<Size Width="{self.width}" Height="{self.height}"/></Image>'
        )

    # ------------------------------------------------------------------
    def _slice_for_region(
        self, channel: int, y0: int, y1: int, x0: int, x1: int
    ):
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

    def _normalize(
        self, patch: np.ndarray, min_val: float = 0.0, max_val: float = 1.0
    ) -> np.ndarray:
        patch = patch.astype(np.float32)
        if self.dtype_max > 0:
            patch = patch / self.dtype_max
        span = max_val - min_val
        if span > 0:
            patch = (patch - min_val) / span
        patch = np.clip(patch, 0.0, 1.0)
        return patch

    def _compose_rgb(
        self,
        patches: List[np.ndarray],
        colors: List[str],
        gains: List[float],
        is_rgb: bool,
        mins: Optional[List[float]] = None,
        maxs: Optional[List[float]] = None,
    ) -> np.ndarray:
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
            for patch, color_name, gain, min_val, max_val in zip(
                patches, colors, gains, mins, maxs
            ):
                patch_norm = self._normalize(patch, min_val, max_val)
                b, g, r = get_color(color_name)
                # Swap R and B because COLOR_MAP is actually RGB despite comment.
                rgb[:, :, 0] += patch_norm * (r / 255.0) * gain  # R value -> B channel
                rgb[:, :, 1] += patch_norm * (g / 255.0) * gain
                rgb[:, :, 2] += patch_norm * (b / 255.0) * gain  # B value -> R channel

        rgb = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
        return rgb

    # ------------------------------------------------------------------
    def get_tile(
        self,
        level: int,
        tile_x: int,
        tile_y: int,
        channels: List[int],
        colors: List[str],
        gains: List[float],
        is_rgb: bool,
        mins: Optional[List[float]] = None,
        maxs: Optional[List[float]] = None,
    ) -> np.ndarray:
        if level < 0 or level > self.max_level:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid level"
            )

        # Select the appropriate pyramid level.
        level_downscale = self.max_level - level
        pyramid_level_idx = min(level_downscale // 1, len(self.levels) - 1)
        level_arr = self.levels[pyramid_level_idx]

        pyramid_scale = 2 ** pyramid_level_idx
        scale = 2 ** (self.max_level - level)
        x0 = tile_x * self.tile_size * scale // pyramid_scale
        y0 = tile_y * self.tile_size * scale // pyramid_scale
        x1 = min(
            level_arr.shape[self.x_axis],
            x0 + (self.tile_size * scale // pyramid_scale),
        )
        y1 = min(
            level_arr.shape[self.y_axis],
            y0 + (self.tile_size * scale // pyramid_scale),
        )

        if (
            x0 >= level_arr.shape[self.x_axis]
            or y0 >= level_arr.shape[self.y_axis]
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tile out of bounds"
            )

        with self._lock:
            patches: List[np.ndarray] = []
            if self.channel_axis is None:
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No channels selected",
            )

        # Pad color/gain/min/max lists if shorter than patches.
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
    """Small LRU cache for open OME-TIFF pyramids.

    Thread-safe. Automatically evicts and re-opens when the underlying
    file's mtime changes, so `--watch` works without explicit invalidation.
    """

    def __init__(self, max_items: int = 4, tile_size: int = 256):
        self.max_items = max_items
        self.tile_size = tile_size
        self.cache: Dict[str, OmeTiffPyramid] = {}
        self.order: List[str] = []
        self._mtimes: Dict[str, float] = {}
        self._lock = threading.Lock()

    def get(self, path: str) -> OmeTiffPyramid:
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = 0.0

        with self._lock:
            if path in self.cache and self._mtimes.get(path) == mtime:
                # refresh order (most-recently-used last)
                self.order = [p for p in self.order if p != path]
                self.order.append(path)
                return self.cache[path]

            # Evict stale entry in place if mtime changed.
            if path in self.cache:
                stale = self.cache.pop(path)
                try:
                    stale.close()
                except Exception:
                    pass
                self.order = [p for p in self.order if p != path]
                self._mtimes.pop(path, None)

            pyramid = OmeTiffPyramid(path, tile_size=self.tile_size)
            self.cache[path] = pyramid
            self._mtimes[path] = mtime
            self.order.append(path)

            while len(self.order) > self.max_items:
                evict_path = self.order.pop(0)
                evicted = self.cache.pop(evict_path, None)
                self._mtimes.pop(evict_path, None)
                if evicted is not None:
                    try:
                        evicted.close()
                    except Exception:
                        pass

            return pyramid

    def invalidate(self, path: str) -> None:
        """Drop a cached pyramid (e.g. when the underlying file changed)."""
        with self._lock:
            pyramid = self.cache.pop(path, None)
            self._mtimes.pop(path, None)
            self.order = [p for p in self.order if p != path]
        if pyramid is not None:
            try:
                pyramid.close()
            except Exception:
                pass

    def clear(self) -> None:
        with self._lock:
            pyramids = list(self.cache.values())
            self.cache.clear()
            self.order.clear()
            self._mtimes.clear()
        for pyramid in pyramids:
            try:
                pyramid.close()
            except Exception:
                pass


__all__ = [
    "OmeTiffPyramid",
    "TiffCache",
    "extract_channel_info",
    "get_color",
    "COLOR_MAP",
]
