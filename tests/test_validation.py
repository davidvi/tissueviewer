"""Tests for the ``--validate`` code path."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import tifffile

from tissueviewer import codecs
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


def _write_compressed(path: Path, compression: str) -> Path:
    tifffile.imwrite(
        str(path),
        np.zeros((2, 64, 64), dtype=np.uint8),
        photometric="minisblack",
        compression=compression,
        metadata={"axes": "CYX"},
        ome=True,
    )
    return path


def test_validate_flags_file_whose_codec_is_unavailable(
    tmp_path: Path, monkeypatch, capsys
):
    """An undecodable slide must be reported, not silently passed.

    Reading the header succeeds without touching pixel data, so without an
    explicit check this file is reported OK and then fails on every tile
    request.
    """
    _write_compressed(tmp_path / "compressed.ome.tiff", "lzw")

    codecs.imagecodecs_available.cache_clear()
    monkeypatch.setattr(
        codecs,
        "_decoder_unavailable_reason",
        lambda c: "<COMPRESSION.LZW: 5> requires the 'imagecodecs' package",
    )

    config = Config(data_dir=tmp_path)
    rc = run_validation(config)
    out = capsys.readouterr().out

    assert rc == 1
    assert "FAIL" in out
    assert "imagecodecs" in out


def test_validate_passes_lzw_when_codecs_present(tmp_path: Path, capsys):
    _write_compressed(tmp_path / "compressed.ome.tiff", "lzw")
    codecs.imagecodecs_available.cache_clear()

    config = Config(data_dir=tmp_path)
    rc = run_validation(config)
    out = capsys.readouterr().out

    assert rc == 0
    assert "OK" in out


def test_validate_passes_deflate_without_imagecodecs(
    tmp_path: Path, monkeypatch, capsys
):
    """Deflate is decoded by tifffile itself via zlib.

    Such files must pass even where imagecodecs is absent — flagging them
    would report a perfectly readable slide as broken.
    """
    _write_compressed(tmp_path / "deflated.ome.tiff", "deflate")

    codecs.imagecodecs_available.cache_clear()
    monkeypatch.setattr(codecs, "imagecodecs_available", lambda: False)

    config = Config(data_dir=tmp_path)
    rc = run_validation(config)
    out = capsys.readouterr().out

    assert rc == 0
    assert "OK" in out


def test_validate_empty_dir(tmp_path: Path, capsys):
    config = Config(data_dir=tmp_path)
    rc = run_validation(config)
    out = capsys.readouterr().out
    assert rc == 1
    assert "No OME-TIFF" in out
