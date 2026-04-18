"""Discovery and location-map tests."""

from __future__ import annotations

from pathlib import Path

from tissueviewer.config import Config
from tissueviewer.discovery import (
    AppState,
    PUBLIC,
    build_location_map,
    list_samples,
)
from tissueviewer.formats.ome_tiff import TiffCache


def _state_from_config(config: Config) -> AppState:
    config.validate()
    location_map, file_overrides, single_file = build_location_map(config)
    return AppState(
        config=config,
        tile_cache=TiffCache(max_items=2),
        location_map=location_map,
        file_overrides=file_overrides,
        single_file_path=single_file,
    )


def test_single_file_mode(tiny_ome_tiff: Path):
    config = Config(single_file=tiny_ome_tiff, data_dir=tiny_ome_tiff.parent)
    state = _state_from_config(config)
    assert state.single_file_path == tiny_ome_tiff
    assert PUBLIC in state.location_map
    samples = list_samples(state, PUBLIC)
    assert len(samples) == 1
    assert samples[0]["name"] == "sample"


def test_directory_non_recursive(data_dir: Path):
    config = Config(data_dir=data_dir)
    state = _state_from_config(config)

    assert PUBLIC in state.location_map
    assert "batch_a" in state.location_map
    assert "batch_b" in state.location_map
    # Nested dir 'batch_a/nested' must NOT appear in non-recursive mode.
    assert "batch_a/nested" not in state.location_map

    root_samples = list_samples(state, PUBLIC)
    assert {s["name"] for s in root_samples} == {"root_slide"}

    a_samples = list_samples(state, "batch_a")
    assert {s["name"] for s in a_samples} == {"a_slide"}

    b_samples = list_samples(state, "batch_b")
    assert {s["name"] for s in b_samples} == {"b_slide"}


def test_directory_recursive(data_dir: Path):
    config = Config(data_dir=data_dir, recursive=True)
    state = _state_from_config(config)

    assert "batch_a/nested" in state.location_map
    nested = list_samples(state, "batch_a/nested")
    assert {s["name"] for s in nested} == {"deep_slide"}


def test_resolve_file_single_file(tiny_ome_tiff: Path):
    """In single-file mode, any (location, stem) resolves to the one file.

    This matches the plan's intent: the bundled client only ever requests
    the stripped name of the configured file, so returning it unconditionally
    keeps tile requests working even for edge cases.
    """
    config = Config(single_file=tiny_ome_tiff, data_dir=tiny_ome_tiff.parent)
    state = _state_from_config(config)

    assert state.resolve_file(PUBLIC, "sample") == tiny_ome_tiff
    # Intentional: single-file mode short-circuits.
    assert state.resolve_file(PUBLIC, "does-not-exist") == tiny_ome_tiff


def test_resolve_file_directory_missing(data_dir: Path):
    config = Config(data_dir=data_dir)
    state = _state_from_config(config)

    resolved = state.resolve_file(PUBLIC, "root_slide")
    assert resolved == data_dir / "root_slide.ome.tiff"

    assert state.resolve_file(PUBLIC, "does-not-exist") is None
    assert state.resolve_file("unknown-location", "root_slide") is None
