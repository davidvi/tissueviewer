"""``--validate`` mode: check that configured files can be opened."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List

import tifffile

from .config import Config
from .discovery import _is_ome_tiff, build_location_map


logger = logging.getLogger(__name__)


def _collect_files(config: Config) -> List[Path]:
    if config.single_file is not None:
        return [config.single_file]

    files: List[Path] = []
    assert config.data_dir is not None
    if config.recursive:
        for dirpath, _dirs, filenames in os.walk(config.data_dir):
            for name in filenames:
                if _is_ome_tiff(name):
                    files.append(Path(dirpath) / name)
    else:
        for dirpath, _dirs, filenames in os.walk(config.data_dir):
            for name in filenames:
                if _is_ome_tiff(name):
                    files.append(Path(dirpath) / name)
            # Only one level deep like the runtime discovery.
            break
        for sub in config.data_dir.iterdir() if config.data_dir.is_dir() else []:
            if sub.is_dir():
                try:
                    for entry in os.scandir(sub):
                        if entry.is_file() and _is_ome_tiff(entry.name):
                            files.append(Path(entry.path))
                except OSError:
                    continue
    # Deduplicate while preserving order.
    seen = set()
    unique: List[Path] = []
    for p in files:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def run_validation(config: Config) -> int:
    """Return a process exit code: 0 on success, non-zero on any failure."""
    # Let config errors surface clearly.
    config.validate()

    files = _collect_files(config)
    if not files:
        print("No OME-TIFF files found.")
        return 1

    failed = 0
    for path in files:
        try:
            with tifffile.TiffFile(str(path)) as tif:
                series = tif.series[0]
                axes = series.axes
                shape = series.shape
                dtype = series.dtype
            channel_count = shape[axes.index("C")] if "C" in axes else 1
            print(
                f"OK   {path}  axes={axes} shape={tuple(shape)} "
                f"dtype={dtype} channels={channel_count}"
            )
        except Exception as exc:
            failed += 1
            print(f"FAIL {path}  {exc}")

    total = len(files)
    print(f"\n{total - failed}/{total} files OK, {failed} failed.")
    return 0 if failed == 0 else 1


__all__ = ["run_validation"]
