"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile


def _write_tiny_ome_tiff(path: Path, *, channels: int = 2, size: int = 64) -> Path:
    """Write a tiny multi-channel OME-TIFF to ``path``."""
    rng = np.random.default_rng(seed=hash(str(path)) & 0xFFFFFFFF)
    data = rng.integers(0, 255, size=(channels, size, size), dtype=np.uint8)
    # tifffile understands axes="CYX" when emitting OME-TIFF.
    tifffile.imwrite(
        str(path),
        data,
        photometric="minisblack",
        metadata={"axes": "CYX"},
        ome=True,
    )
    return path


@pytest.fixture
def tiny_ome_tiff(tmp_path: Path) -> Path:
    return _write_tiny_ome_tiff(tmp_path / "sample.ome.tiff")


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """A directory containing a root slide and two sub-location slides."""
    root = tmp_path / "data"
    root.mkdir()
    _write_tiny_ome_tiff(root / "root_slide.ome.tiff")

    sub_a = root / "batch_a"
    sub_a.mkdir()
    _write_tiny_ome_tiff(sub_a / "a_slide.ome.tiff")

    sub_b = root / "batch_b"
    sub_b.mkdir()
    _write_tiny_ome_tiff(sub_b / "b_slide.ome.tif")

    # A nested file two levels deep — picked up only by --recursive.
    nested = sub_a / "nested"
    nested.mkdir()
    _write_tiny_ome_tiff(nested / "deep_slide.ome.tiff")

    return root
