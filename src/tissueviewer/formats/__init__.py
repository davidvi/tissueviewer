"""Image format handlers.

Currently only OME-TIFF is supported; this module exists so that adding
additional handlers later (plain TIFF, OME-Zarr, etc.) is a matter of
dropping another module and registering it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .ome_tiff import OmeTiffPyramid, TiffCache

Handler = Callable[[str], OmeTiffPyramid]


def is_supported(path: Path) -> bool:
    """Return True if *path* is in a format TissueViewer can open."""
    name = path.name.lower()
    return name.endswith(".ome.tif") or name.endswith(".ome.tiff")


def get_handler(path: Path) -> Handler:
    """Return a callable that opens the given image path.

    Raises ``ValueError`` for unsupported file types.
    """
    if is_supported(path):
        return OmeTiffPyramid  # type: ignore[return-value]
    raise ValueError(f"Unsupported image format: {path}")


__all__ = ["OmeTiffPyramid", "TiffCache", "get_handler", "is_supported"]
