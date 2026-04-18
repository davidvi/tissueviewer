"""OME-TIFF file discovery + virtual location layout.

The client always addresses slides via a ``location`` string (default
``public``). This module builds the mapping from ``location`` to an actual
directory or a specific file on disk, for each of three modes:

* **single file**: exactly one slide; ``location="public"``.
* **directory, non-recursive**: the root maps to ``public``; each immediate
  subdirectory becomes its own location named after the subdir.
* **directory, recursive**: walks the full tree. Files at the root go to
  ``public``; files in subdirs go to the slash-joined relative path of the
  parent (e.g. ``2024/batch_A``). The client URL-encodes this safely.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from .config import Config
from .metadata import get_metadata_for_file

if TYPE_CHECKING:
    from .formats.ome_tiff import TiffCache


logger = logging.getLogger(__name__)


PUBLIC = "public"


def _is_ome_tiff(name: str) -> bool:
    low = name.lower()
    return low.endswith(".ome.tif") or low.endswith(".ome.tiff")


def _strip_ome_suffix(name: str) -> str:
    # Matches original server behaviour: rsplit(".ome", 1)[0]
    return name.rsplit(".ome", 1)[0]


@dataclass
class AppState:
    """Shared runtime state held on ``app.state.tv``."""

    config: Config
    tile_cache: "TiffCache"  # forward ref, populated in app.py
    location_map: Dict[str, Path] = field(default_factory=dict)
    # Map of "{location}/{stem}" → explicit file path. Used in single-file
    # mode where the file may not share the location's directory structure,
    # or when we want to override directory resolution.
    file_overrides: Dict[str, Path] = field(default_factory=dict)
    single_file_path: Optional[Path] = None
    # Bumped by the watcher on relevant filesystem changes so that cached
    # directory listings are discarded lazily on the next request.
    generation: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def resolve_file(self, location: str, stem: str) -> Optional[Path]:
        """Resolve a (location, file-stem) pair to an absolute file path.

        Returns ``None`` if nothing matches.
        """
        # Single-file mode: always serve the one file, regardless of inputs.
        if self.single_file_path is not None:
            return self.single_file_path

        override = self.file_overrides.get(f"{location}/{stem}")
        if override is not None and override.exists():
            return override

        base = self.location_map.get(location)
        if base is None:
            return None

        # Try .ome.tiff first, then .ome.tif (matches legacy server).
        for suffix in (".ome.tiff", ".ome.tif"):
            candidate = base / f"{stem}{suffix}"
            if candidate.exists():
                return candidate
        return None

    def list_locations(self) -> List[str]:
        return list(self.location_map.keys())

    def refresh(self) -> None:
        """Rebuild location map from config; bump generation counter."""
        loc_map, overrides, single = build_location_map(self.config)
        with self._lock:
            self.location_map = loc_map
            self.file_overrides = overrides
            self.single_file_path = single
            self.generation += 1


def build_location_map(config: Config) -> tuple[Dict[str, Path], Dict[str, Path], Optional[Path]]:
    """Build ``(location_map, file_overrides, single_file_path)`` for a config.

    ``location_map`` maps location names to directories that contain slides.
    ``file_overrides`` map ``"{location}/{stem}"`` to a specific file path
    (used in single-file mode).
    """
    location_map: Dict[str, Path] = {}
    file_overrides: Dict[str, Path] = {}
    single_file: Optional[Path] = None

    if config.single_file is not None:
        single_file = config.single_file.resolve()
        location_map[PUBLIC] = single_file.parent
        stem = _strip_ome_suffix(single_file.name)
        file_overrides[f"{PUBLIC}/{stem}"] = single_file
        return location_map, file_overrides, single_file

    assert config.data_dir is not None, "Config.validate() should have caught this"
    root = config.data_dir.resolve()
    location_map[PUBLIC] = root

    if config.recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            # Stable traversal order.
            dirnames.sort()
            if not any(_is_ome_tiff(f) for f in filenames):
                continue
            rel = Path(dirpath).relative_to(root)
            if rel == Path("."):
                continue  # already mapped as PUBLIC
            location = rel.as_posix()  # forward slashes, safe for URLs
            location_map[location] = Path(dirpath)
    else:
        try:
            for entry in os.scandir(root):
                if entry.is_dir():
                    location_map[entry.name] = Path(entry.path)
        except OSError as exc:
            logger.warning("Could not scan %s: %s", root, exc)

    return location_map, file_overrides, single_file


def _process_single_file(path: Path, base_dir: Path) -> Optional[dict]:
    """Build the per-slide dict used in ``/samples.json`` responses."""
    try:
        metadata = get_metadata_for_file(str(path), use_cache=True)

        name = _strip_ome_suffix(path.name)
        dataset_info = {
            "name": name,
            "details": {},
            "metadata": [metadata],
        }

        sample_json_path = base_dir / f"{name}.sample.json"
        if sample_json_path.exists():
            try:
                with open(sample_json_path, "r", encoding="utf-8") as fh:
                    dataset_info["details"] = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Bad sample.json for %s: %s", path, exc)

        return dataset_info
    except Exception as exc:
        logger.warning("Error loading %s: %s", path, exc)
        return None


def list_samples(state: AppState, location: str) -> List[dict]:
    """Return the list of slides for a given location."""
    # Single-file override wins.
    if state.single_file_path is not None and location == PUBLIC:
        result = _process_single_file(
            state.single_file_path, state.single_file_path.parent
        )
        return [result] if result else []

    base_dir = state.location_map.get(location)
    if base_dir is None or not base_dir.exists():
        return []

    entries: List[Path] = []
    try:
        with os.scandir(base_dir) as it:
            for entry in it:
                if entry.is_file() and _is_ome_tiff(entry.name):
                    entries.append(Path(entry.path))
    except OSError as exc:
        logger.warning("Could not scan %s: %s", base_dir, exc)
        return []

    results: List[dict] = []
    if not entries:
        return results

    with ThreadPoolExecutor(max_workers=None) as executor:
        futures = {
            executor.submit(_process_single_file, path, base_dir): path
            for path in entries
        }
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)

    # Stable alphabetical order for deterministic UI.
    results.sort(key=lambda d: d["name"].lower())
    return results


__all__ = [
    "AppState",
    "PUBLIC",
    "build_location_map",
    "list_samples",
]
