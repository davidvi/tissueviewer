"""Tests for the ``--validate`` code path."""

from __future__ import annotations

from pathlib import Path

from tissueviewer.config import Config
from tissueviewer.validation import run_validation


def test_validate_passes_on_good_files(data_dir: Path, capsys):
    config = Config(data_dir=data_dir, recursive=True)
    rc = run_validation(config)
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out
    assert "files OK" in out


def test_validate_fails_on_corrupt_file(tmp_path: Path, capsys):
    bad = tmp_path / "broken.ome.tiff"
    bad.write_bytes(b"not a tiff")
    config = Config(data_dir=tmp_path)
    rc = run_validation(config)
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAIL" in out


def test_validate_empty_dir(tmp_path: Path, capsys):
    config = Config(data_dir=tmp_path)
    rc = run_validation(config)
    out = capsys.readouterr().out
    assert rc == 1
    assert "No OME-TIFF" in out
