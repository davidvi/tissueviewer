"""`/samples.json` endpoint."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from ..discovery import AppState, list_samples


logger = logging.getLogger(__name__)


def register(app: FastAPI, state: AppState) -> None:
    @app.get("/samples.json")
    async def samples(
        location: str = Query("public", description="Location key (default 'public')"),
    ):
        logger.debug("listing samples for location=%s", location)
        samples_list = list_samples(state, location)
        body = {
            "samples": samples_list,
            "save": state.config.save_enabled,
            "colors": state.config.colors,
        }
        return JSONResponse(content=body, status_code=200)


__all__ = ["register"]
