"""Minimal extension point for future image format handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class PyramidLike(Protocol):
    """Minimal interface a pyramid object must expose to the routes."""

    width: int
    height: int
    tile_size: int
    max_level: int

    def dzi_xml(self) -> str: ...

    def close(self) -> None: ...


@runtime_checkable
class ImageHandler(Protocol):
    def __call__(self, path: str) -> PyramidLike: ...


__all__ = ["ImageHandler", "PyramidLike", "Path"]
