"""Lightweight filesystem mtime poller for ``--watch`` mode.

Deliberately stdlib-only (no ``watchdog``) to keep the wheel slim. On every
poll it rebuilds the location map; if any OME-TIFF file that is currently
cached has a new mtime, its cached pyramid is invalidated.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Iterable

from .discovery import AppState, _is_ome_tiff, build_location_map


logger = logging.getLogger(__name__)


def _iter_ome_files(map_paths: Iterable[Path], recursive: bool) -> Iterable[Path]:
    for base in map_paths:
        try:
            if recursive:
                for dirpath, _dirs, filenames in os.walk(base):
                    for name in filenames:
                        if _is_ome_tiff(name):
                            yield Path(dirpath) / name
            else:
                for entry in os.scandir(base):
                    if entry.is_file() and _is_ome_tiff(entry.name):
                        yield Path(entry.path)
        except OSError as exc:
            logger.warning("Watcher cannot scan %s: %s", base, exc)


def start_watcher(state: AppState, interval: float = 2.0) -> threading.Thread:
    """Start a daemon thread that polls for filesystem changes."""
    stop_event = threading.Event()

    mtimes: dict[str, float] = {}
    # Seed initial mtimes so we don't fire invalidations on first loop.
    for path in _iter_ome_files(state.location_map.values(), state.config.recursive):
        try:
            mtimes[str(path)] = path.stat().st_mtime
        except OSError:
            continue

    def run() -> None:
        while not stop_event.is_set():
            try:
                new_map, new_overrides, new_single = build_location_map(state.config)
                state.location_map = new_map
                state.file_overrides = new_overrides
                state.single_file_path = new_single

                seen: set[str] = set()
                for path in _iter_ome_files(new_map.values(), state.config.recursive):
                    key = str(path)
                    seen.add(key)
                    try:
                        mtime = path.stat().st_mtime
                    except OSError:
                        continue
                    prev = mtimes.get(key)
                    if prev is not None and prev != mtime:
                        logger.info("File changed, invalidating cache: %s", path)
                        state.tile_cache.invalidate(key)
                    mtimes[key] = mtime

                for stale in list(mtimes.keys()):
                    if stale not in seen:
                        mtimes.pop(stale, None)
                        state.tile_cache.invalidate(stale)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Watcher iteration failed: %s", exc)

            stop_event.wait(interval)

    thread = threading.Thread(target=run, name="tv-watcher", daemon=True)
    thread.start()
    # Expose the stop event so tests / future shutdown hooks can stop it.
    thread._stop_event = stop_event  # type: ignore[attr-defined]
    return thread


__all__ = ["start_watcher"]
