"""Deep-zoom tile + DZI endpoints (windowed and non-windowed variants).

The four variants kept for byte-for-byte compatibility with the pre-built
Vue client:

* ``GET /{location}/{chs}/{rgb}/{colors}/{gains}/{mins}/{maxs}/{file}.dzi``
* ``GET /{location}/{chs}/{rgb}/{colors}/{gains}/{mins}/{maxs}/{file}_files/{level}/{x}_{y}.jpeg``
* ``GET /{location}/{chs}/{rgb}/{colors}/{gains}/{file}.dzi``
* ``GET /{location}/{chs}/{rgb}/{colors}/{gains}/{file}_files/{level}/{x}_{y}.jpeg``

Registration order matters — the windowed variants must come first.
"""

from __future__ import annotations

import logging
from io import BytesIO

import cv2
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import Response

from ..discovery import AppState


logger = logging.getLogger(__name__)


def _split_floats(raw: str) -> list[float]:
    return [float(x) for x in raw.split(";") if x != ""]


def _split_ints(raw: str) -> list[int]:
    return [int(x) for x in raw.split(";") if x != ""]


def _split_strs(raw: str) -> list[str]:
    return [c for c in raw.split(";") if c != ""]


def register(app: FastAPI, state: AppState) -> None:
    # ------------------------------------------------------------------
    # Windowed variants (mins/maxs present) — REGISTER FIRST.
    # ------------------------------------------------------------------
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
        return await _dzi(state, location, file)

    @app.get(
        "/{location}/{chs}/{rgb}/{colors}/{gains}/{mins}/{maxs}/{file}_files/"
        "{level}/{loc_x}_{loc_y}.jpeg"
    )
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
        return await _tile(
            state,
            location=location,
            chs=chs,
            rgb=rgb,
            colors=colors,
            gains=gains,
            file=file,
            level=level,
            loc_x=loc_x,
            loc_y=loc_y,
            mins=_split_floats(mins),
            maxs=_split_floats(maxs),
        )

    # ------------------------------------------------------------------
    # Non-windowed variants.
    # ------------------------------------------------------------------
    @app.get("/{location}/{chs}/{rgb}/{colors}/{gains}/{file}.dzi")
    async def get_dzi(
        location: str,
        chs: str,
        rgb: str,
        colors: str,
        gains: str,
        file: str,
    ):
        return await _dzi(state, location, file)

    @app.get(
        "/{location}/{chs}/{rgb}/{colors}/{gains}/{file}_files/"
        "{level}/{loc_x}_{loc_y}.jpeg"
    )
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
        return await _tile(
            state,
            location=location,
            chs=chs,
            rgb=rgb,
            colors=colors,
            gains=gains,
            file=file,
            level=level,
            loc_x=loc_x,
            loc_y=loc_y,
            mins=None,
            maxs=None,
        )


# ----------------------------------------------------------------------
# Shared handler bodies.
# ----------------------------------------------------------------------
async def _dzi(state: AppState, location: str, file: str) -> Response:
    path = state.resolve_file(location, file)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OME-TIFF not found"
        )

    pyramid = state.tile_cache.get(str(path))
    dzi_content = pyramid.dzi_xml()
    return Response(
        content=dzi_content, media_type="application/xml", status_code=200
    )


async def _tile(
    state: AppState,
    *,
    location: str,
    chs: str,
    rgb: bool,
    colors: str,
    gains: str,
    file: str,
    level: int,
    loc_x: int,
    loc_y: int,
    mins,
    maxs,
) -> Response:
    path = state.resolve_file(location, file)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OME-TIFF not found"
        )

    pyramid = state.tile_cache.get(str(path))

    channels = _split_ints(chs)
    colors_list = _split_strs(colors)
    gains_list = _split_floats(gains)

    tile = pyramid.get_tile(
        level,
        loc_x,
        loc_y,
        channels,
        colors_list,
        gains_list,
        rgb,
        mins,
        maxs,
    )

    tile_rgb = cv2.cvtColor(tile, cv2.COLOR_BGR2RGB)
    img_bytes = cv2.imencode(".jpeg", tile_rgb)[1].tobytes()
    img_io = BytesIO(img_bytes)
    return Response(content=img_io.getvalue(), media_type="image/jpeg")


__all__ = ["register"]
