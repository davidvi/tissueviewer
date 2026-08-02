"""Tests for the codec availability guard."""

from __future__ import annotations

import logging
import subprocess
import sys
import textwrap

import pytest

from tissueviewer import codecs


# Compression tag values used below.
NONE = 1
LZW = 5
JPEG = 7
ADOBE_DEFLATE = 8
PACKBITS = 32773
DEFLATE = 32946

# Handled by tifffile itself, with no help from imagecodecs. Flagging any of
# these would mark a readable slide as broken.
NATIVE = [NONE, ADOBE_DEFLATE, PACKBITS, DEFLATE]


@pytest.fixture(autouse=True)
def _clear_codec_cache():
    codecs.imagecodecs_available.cache_clear()
    yield
    codecs.imagecodecs_available.cache_clear()


def test_imagecodecs_is_installed():
    """It is a declared dependency, so a correct install always has it."""
    assert codecs.imagecodecs_available() is True


def test_check_codec_support_silent_when_available(caplog):
    with caplog.at_level(logging.WARNING, logger=codecs.__name__):
        assert codecs.check_codec_support() is True
    assert caplog.records == []


def test_check_codec_support_warns_when_missing(monkeypatch, caplog):
    monkeypatch.setattr(codecs, "imagecodecs_available", lambda: False)
    with caplog.at_level(logging.WARNING, logger=codecs.__name__):
        assert codecs.check_codec_support() is False
    assert "pip install imagecodecs" in caplog.text


def test_check_codec_support_never_raises(monkeypatch):
    monkeypatch.setattr(codecs, "imagecodecs_available", lambda: False)
    codecs.check_codec_support()


@pytest.mark.parametrize("compression", NATIVE)
def test_natively_decodable_compressions_are_never_flagged(compression):
    assert codecs.missing_codec_reason(compression) is None


@pytest.mark.parametrize("compression", [LZW, JPEG])
def test_supported_compressions_not_flagged_when_codecs_present(compression):
    assert codecs.missing_codec_reason(compression) is None


def test_reason_includes_install_hint(monkeypatch):
    monkeypatch.setattr(
        codecs,
        "_decoder_unavailable_reason",
        lambda c: "<COMPRESSION.LZW: 5> requires the 'imagecodecs' package",
    )
    reason = codecs.missing_codec_reason(LZW)
    assert reason is not None
    assert "pip install imagecodecs" in reason


def test_uncompressed_never_flagged_even_if_probe_complains(monkeypatch):
    monkeypatch.setattr(
        codecs, "_decoder_unavailable_reason", lambda c: "should not be used"
    )
    assert codecs.missing_codec_reason(NONE) is None


def test_undeterminable_support_is_not_flagged(monkeypatch):
    """Never guess: an unanswerable probe must not fail a good slide."""
    monkeypatch.setattr(codecs, "_decoder_unavailable_reason", lambda c: None)
    assert codecs.missing_codec_reason(LZW) is None


def test_real_behaviour_without_imagecodecs():
    """Regression test for the split between native and imagecodecs codecs.

    Runs in a subprocess with the ``imagecodecs`` import blocked, which is
    the situation on a source-checkout deployment. Deflate and friends must
    stay readable; only LZW/JPEG may be reported.
    """
    script = textwrap.dedent(
        """
        import sys
        from importlib.abc import MetaPathFinder

        class Blocker(MetaPathFinder):
            def find_spec(self, name, path=None, target=None):
                if name.split(".")[0] == "imagecodecs":
                    raise ImportError("blocked")
                return None

        sys.meta_path.insert(0, Blocker())

        from tissueviewer import codecs

        assert codecs.imagecodecs_available() is False, "blocker did not work"

        for c in (1, 8, 32773, 32946):
            assert codecs.missing_codec_reason(c) is None, (c, "flagged")

        for c in (5, 7):
            reason = codecs.missing_codec_reason(c)
            assert reason is not None, (c, "not flagged")
            assert "imagecodecs" in reason, reason

        print("OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
