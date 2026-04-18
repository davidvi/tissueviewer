"""`POST /save/{location}/{file}` — persist per-slide settings sidecar."""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

from ..discovery import AppState


logger = logging.getLogger(__name__)


def register(app: FastAPI, state: AppState) -> None:
    @app.post("/save/{location}/{file}", response_class=PlainTextResponse)
    async def save_slide_settings(location: str, file: str, request: Request):
        if not state.config.save_enabled:
            return PlainTextResponse(
                "SAVE BLOCKED", status_code=status.HTTP_403_FORBIDDEN
            )

        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON"
            )

        base_dir = state.location_map.get(location)
        if base_dir is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Unknown location"
            )

        file_path = base_dir / f"{file}.sample.json"
        try:
            with open(file_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
        except OSError as exc:
            logger.error("Cannot write %s: %s", file_path, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cannot persist settings",
            )

        return "OK"


__all__ = ["register"]
