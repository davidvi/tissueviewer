"""Serves the pre-built Vue client bundled inside the wheel."""

from __future__ import annotations

import logging
from importlib.resources import as_file, files
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..discovery import AppState


logger = logging.getLogger(__name__)


def _resolve_web_root() -> Path:
    """Return the on-disk path to the bundled web assets.

    Works both from a source checkout (``src/tissueviewer/web``) and from an
    installed wheel. We use ``as_file`` with a context manager whose lifetime
    is tied to the FastAPI application module — acceptable because an ASGI
    app stays alive for the process lifetime.
    """
    resource = files("tissueviewer") / "web"
    # ``as_file`` gives a real filesystem path; for loose installs it's the
    # directory itself, for zipped installs it's a temp extraction.
    ctx = as_file(resource)
    path = ctx.__enter__()  # noqa: SLF001 - intentionally process-lifetime
    # We deliberately do NOT call __exit__; cleanup happens at interpreter
    # shutdown. StaticFiles holds the directory open for the lifetime of the
    # server which matches this process.
    return Path(path)


def register(app: FastAPI, state: AppState) -> None:
    web_root = _resolve_web_root()
    if not web_root.exists():
        logger.error(
            "Bundled web assets not found at %s. Did you run scripts/sync_client.py?",
            web_root,
        )

    index_path = web_root / "index.html"
    favicon_path = web_root / "favicon.ico"
    assets_dir = web_root / "assets"
    images_dir = web_root / "images"

    @app.get("/")
    async def root():
        if not index_path.exists():
            raise HTTPException(status_code=500, detail="Web UI not bundled")
        return FileResponse(str(index_path))

    @app.get("/favicon.ico")
    async def favicon():
        if not favicon_path.exists():
            raise HTTPException(status_code=404, detail="favicon not bundled")
        return FileResponse(str(favicon_path))

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    else:  # pragma: no cover - dev-only branch
        logger.warning("assets directory missing: %s", assets_dir)

    if images_dir.exists():
        app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")
    else:  # pragma: no cover - dev-only branch
        logger.warning("images directory missing: %s", images_dir)


__all__ = ["register"]
