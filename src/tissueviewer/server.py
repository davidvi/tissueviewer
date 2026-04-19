"""Uvicorn runner wrapper."""

from __future__ import annotations

import logging
import threading

import uvicorn

from .app import create_app
from .browser import open_when_ready
from .config import Config
from .watcher import start_watcher


logger = logging.getLogger(__name__)


def run_server(config: Config) -> None:
    app = create_app(config)
    state = app.state.tv  # type: ignore[attr-defined]

    url = f"http://{config.host}:{config.port}/"
    print(f"TissueViewer listening on {url}")

    if config.open_browser:
        threading.Thread(
            target=open_when_ready,
            args=(url, config.host, config.port),
            name="tv-browser",
            daemon=True,
        ).start()

    if config.watch:
        start_watcher(state)

    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
    )


__all__ = ["run_server"]
