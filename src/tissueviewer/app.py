"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import make_basic_auth_middleware
from .config import Config
from .discovery import AppState, build_location_map
from .formats.ome_tiff import TiffCache
from .routes import register_routes


logger = logging.getLogger(__name__)


def build_state(config: Config) -> AppState:
    config.validate()
    location_map, file_overrides, single_file = build_location_map(config)
    cache = TiffCache(max_items=config.tile_cache_size)
    state = AppState(
        config=config,
        tile_cache=cache,
        location_map=location_map,
        file_overrides=file_overrides,
        single_file_path=single_file,
    )
    logger.info(
        "Discovered %d location(s): %s",
        len(location_map),
        ", ".join(sorted(location_map.keys())),
    )
    return state


def create_app(config: Config) -> FastAPI:
    """Build a FastAPI app for the given configuration.

    Suitable for programmatic use with any ASGI server.
    """
    from . import __version__  # local import avoids circular

    state = build_state(config)
    app = FastAPI(title="TissueViewer", version=__version__)
    app.state.tv = state

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if config.auth_enabled:
        # Registering through the decorator API runs auth before any route
        # is dispatched, so static assets, tiles, and APIs are all gated.
        assert config.auth_username is not None and config.auth_password is not None
        app.middleware("http")(
            make_basic_auth_middleware(config.auth_username, config.auth_password)
        )
        logger.info("HTTP Basic auth enabled (user=%r)", config.auth_username)

    register_routes(app, state)
    return app


__all__ = ["create_app", "build_state"]
