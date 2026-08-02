"""Tests for the imagecodecs availability guard."""

from __future__ import annotations

import logging

import pytest

from tissueviewer import codecs


@pytest.fixture(autouse=True)
def _clear_codec_cache():
    """``imagecodecs_available`` is cached; reset it around each test."""
    codecs.imagecodecs_available.cache_clear()
    yield
    codecs.imagecodecs_available.cache_clear()


def _pretend_missing(monkeypatch):
    monkeypatch.setattr(codecs, "imagecodecs_available", lambda: False)


def test_imagecodecs_is_installed():
    """It is a declared dependency, so a correct install always has it."""
    assert codecs.imagecodecs_available() is True


def test_check_codec_support_silent_when_available(caplog):
    with caplog.at_level(logging.WARNING, logger=codecs.__name__):
        assert codecs.check_codec_support() is True
    assert caplog.records == []


def test_check_codec_support_warns_when_missing(monkeypatch, caplog):
    _pretend_missing(monkeypatch)
    with caplog.at_level(logging.WARNING, logger=codecs.__name__):
        assert codecs.check_codec_support() is False
    assert "imagecodecs" in caplog.text
    assert "pip install imagecodecs" in caplog.text


def test_check_codec_support_never_raises(monkeypatch):
    """A library of uncompressed slides must still be able to start."""
    _pretend_missing(monkeypatch)
    codecs.check_codec_support()


def test_no_reason_for_uncompressed_even_without_codecs(monkeypatch):
    _pretend_missing(monkeypatch)
    assert codecs.missing_codec_reason(codecs.COMPRESSION_NONE) is None


def test_reason_reported_for_compressed_without_codecs(monkeypatch):
    _pretend_missing(monkeypatch)
    reason = codecs.missing_codec_reason(5)  # 5 == LZW
    assert reason is not None
    assert "imagecodecs" in reason


def test_no_reason_when_codecs_present():
    assert codecs.missing_codec_reason(5) is None
