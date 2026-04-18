"""FastAPI route registration.

Order matters: windowed (mins/maxs) tile + DZI endpoints must be registered
before the non-windowed variants, otherwise FastAPI's path matcher routes
windowed requests into the shorter handlers.
"""

from __future__ import annotations

from fastapi import FastAPI

from ..discovery import AppState
from . import client, histogram, samples, save, tiles


def register_routes(app: FastAPI, state: AppState) -> None:
    # Client static assets first so "/" catches before anything else.
    client.register(app, state)

    # JSON APIs.
    samples.register(app, state)
    histogram.register(app, state)
    save.register(app, state)

    # Tiles + DZI last because their path patterns are the most permissive.
    # Windowed variants must be registered first inside ``tiles.register``.
    tiles.register(app, state)


__all__ = ["register_routes"]
