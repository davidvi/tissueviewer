"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .codecs import check_codec_support
from .config import Config
from .discovery import AppState, build_location_map
from .formats.ome_tiff import TiffCache
from .logging_setup import configure_logging
from .routes import register_routes


logger = logging.getLogger(__name__)


def build_state(config: Config) -> AppState:
    config.validate()
    check_codec_support()
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


def _install_threadpool(app: FastAPI) -> None:
    """Replace the default asyncio executor with a larger, named pool.

    The size is controlled by the ``TV_THREADPOOL_SIZE`` env var. Defaults to
    ``min(32, (os.cpu_count() or 1) * 4)`` which is appropriate for the
    mixed I/O + CPU work that tile rendering does (zlib/JPEG release the GIL).
    """
    default_size = min(32, (os.cpu_count() or 1) * 4)
    try:
        size = int(os.environ.get("TV_THREADPOOL_SIZE", default_size))
    except ValueError:
        size = default_size
    size = max(1, size)

    executor = ThreadPoolExecutor(
        max_workers=size, thread_name_prefix="tv-worker"
    )

    @app.on_event("startup")
    async def _set_executor() -> None:  # pragma: no cover - runtime wiring
        loop = asyncio.get_running_loop()
        loop.set_default_executor(executor)
        logger.info("TissueViewer threadpool size: %d", size)

    @app.on_event("shutdown")
    async def _shutdown_executor() -> None:  # pragma: no cover
        executor.shutdown(wait=False, cancel_futures=True)


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

    _install_threadpool(app)
    register_routes(app, state)
    return app


def create_app_from_env() -> FastAPI:
    """ASGI factory used by gunicorn/uvicorn ``--workers``.

    Reads ``TV_SLIDE_DIR`` (and optionally ``TV_CONFIG`` for a YAML file)
    instead of CLI arguments. Each worker process calls this once on boot.

    Examples
    --------
    gunicorn -k uvicorn.workers.UvicornWorker -w 4 \\
        'tissueviewer.app:create_app_from_env()'

    uvicorn --factory tissueviewer.app:create_app_from_env --workers 4
    """
    config_path_str = os.environ.get("TV_CONFIG")
    config_path = Path(config_path_str) if config_path_str else None
    config = Config.from_sources(
        cli_args=None,
        config_path=config_path,
        target=None,
    )
    configure_logging(config.log_level)
    config.validate()
    return create_app(config)


__all__ = ["create_app", "create_app_from_env", "build_state"]
