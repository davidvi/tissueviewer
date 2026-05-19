"""`/histogram/{location}/{channel}/{file}` endpoint."""

from __future__ import annotations

import asyncio
import logging

import numpy as np
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from ..discovery import AppState


logger = logging.getLogger(__name__)


def _compute_histogram(pyramid, channel: int) -> list[int]:
    """Synchronous histogram computation. Runs in a worker thread."""
    level_arr = pyramid.levels[-1]

    with pyramid._lock:
        if pyramid.channel_axis is not None:
            patch = level_arr[
                pyramid._slice_for_region(
                    channel,
                    0,
                    level_arr.shape[pyramid.y_axis],
                    0,
                    level_arr.shape[pyramid.x_axis],
                )
            ]
        else:
            patch = level_arr[:]

    arr = np.asarray(patch, dtype=np.float32)
    flat = arr.flatten() / pyramid.dtype_max
    counts, _ = np.histogram(flat, bins=64, range=(0.0, 1.0))
    return counts.tolist()


def register(app: FastAPI, state: AppState) -> None:
    @app.get("/histogram/{location}/{channel}/{file}")
    async def get_histogram(location: str, channel: int, file: str):
        """Return a 64-bin normalized-intensity histogram for one channel.

        Response shape: ``{"bins": [count0, ..., count63]}``.
        Uses the lowest-resolution pyramid level for speed.
        """
        path = state.resolve_file(location, file)
        if path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OME-TIFF not found",
            )

        pyramid = await asyncio.to_thread(state.tile_cache.get, str(path))
        bins = await asyncio.to_thread(_compute_histogram, pyramid, channel)
        return JSONResponse(content={"bins": bins})


__all__ = ["register"]
