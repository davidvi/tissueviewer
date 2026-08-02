"""Codec availability checks.

``tifffile`` decodes some TIFF compression schemes by itself and delegates
the rest to ``imagecodecs``. The split is not obvious: Deflate, PackBits,
LZMA and Zstd are handled natively (Deflate via the standard library's
``zlib``), while LZW, JPEG and the other image codecs need ``imagecodecs``.

``imagecodecs`` is a declared dependency, so ``pip install tissueviewer``
always provides it — but a deployment that puts the source checkout on
``PYTHONPATH`` instead of installing it never resolves the dependency list
and can run without it.

Nothing fails at import time in that case. The server starts, slides open,
and the DZI manifest is served normally; only the individual tile requests
fail, with a ``ValueError`` raised deep inside ``tifffile``. To the user the
slide simply renders blank, and the cause is visible only as a stack trace
in the server log. Worse, the failure is data-dependent: a library of
uncompressed slides works perfectly until the first LZW slide arrives.

These helpers surface the problem once, loudly, at startup, and let
``--validate`` name the files that would fail. Rather than guessing which
compression types need help, they ask ``tifffile`` itself, so the answer
stays correct as it gains or drops codec support.
"""

from __future__ import annotations

import functools
import logging


logger = logging.getLogger(__name__)


# TIFF ``Compression`` tag value 1 means "no compression".
COMPRESSION_NONE = 1

_MISSING_CODECS_MESSAGE = (
    "The 'imagecodecs' package is not installed. Slides that are "
    "uncompressed or use Deflate/PackBits/Zstd still work, but any slide "
    "using LZW, JPEG or another imagecodecs-backed compression will fail at "
    "tile-render time with a ValueError from tifffile, and render blank. "
    "Install it with 'pip install imagecodecs'. Installing tissueviewer "
    "normally pulls this in automatically, so a missing imagecodecs usually "
    "means the package is being run from a source checkout that was never "
    "pip-installed."
)


@functools.lru_cache(maxsize=1)
def imagecodecs_available() -> bool:
    """Return whether ``imagecodecs`` can be imported."""
    try:
        import imagecodecs  # noqa: F401
    except ImportError:
        return False
    return True


def check_codec_support() -> bool:
    """Log a warning if imagecodecs-backed compressions cannot be decoded.

    Returns the same value as :func:`imagecodecs_available` so callers can
    branch on it. Deliberately never raises — a server whose slides are all
    uncompressed (or Deflate) is perfectly usable and should still start.
    """
    if imagecodecs_available():
        return True
    logger.warning(_MISSING_CODECS_MESSAGE)
    return False


def _decoder_unavailable_reason(compression: int) -> str | None:
    """Ask tifffile why it cannot decode ``compression``, if it cannot.

    Returns ``None`` when the compression is decodable, or when the answer
    cannot be determined — never guess, because a false positive here marks
    a perfectly good slide as broken.
    """
    try:
        from tifffile import TIFF

        decompressors = TIFF.DECOMPRESSORS
    except (ImportError, AttributeError):  # pragma: no cover - old tifffile
        return None

    try:
        decompressors[compression]
    except KeyError as exc:
        # tifffile's own wording, e.g. "<COMPRESSION.LZW: 5> requires the
        # 'imagecodecs' package". It is quoted by KeyError's repr.
        return str(exc).strip("\"'")
    except Exception:  # pragma: no cover - defensive
        return None
    return None


def missing_codec_reason(compression: int) -> str | None:
    """Return why ``compression`` cannot be decoded here, else ``None``.

    ``compression`` is the raw TIFF ``Compression`` tag value.
    """
    if compression == COMPRESSION_NONE:
        return None

    reason = _decoder_unavailable_reason(compression)
    if reason is None:
        return None
    if "imagecodecs" in reason:
        return f"{reason}; install it with 'pip install imagecodecs'"
    return reason


__all__ = [
    "COMPRESSION_NONE",
    "check_codec_support",
    "imagecodecs_available",
    "missing_codec_reason",
]
