"""Centralized logging configuration for TissueViewer."""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger once.

    Safe to call multiple times; subsequent calls only adjust the level.
    """
    global _CONFIGURED

    level_val = getattr(logging, level.upper(), logging.INFO)

    if _CONFIGURED:
        logging.getLogger().setLevel(level_val)
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level_val)

    # Quieten uvicorn's duplicate access logger a bit but keep errors.
    logging.getLogger("uvicorn.access").setLevel(max(level_val, logging.INFO))

    _CONFIGURED = True
