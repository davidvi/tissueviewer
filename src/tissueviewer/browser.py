"""Helpers for opening a browser once the server is ready."""

from __future__ import annotations

import logging
import socket
import time
import webbrowser


logger = logging.getLogger(__name__)


def open_when_ready(url: str, host: str, port: int, max_wait: float = 10.0) -> None:
    """Poll ``(host, port)`` until it accepts a TCP connection, then open ``url``."""
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.25):
                break
        except OSError:
            time.sleep(0.1)
    else:
        logger.warning("Server did not come up within %.1fs; not opening browser.", max_wait)
        return

    try:
        webbrowser.open(url)
    except Exception as exc:  # pragma: no cover - depends on env
        logger.warning("Failed to open browser: %s", exc)


__all__ = ["open_when_ready"]
