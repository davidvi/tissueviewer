"""Codec availability checks.

``tifffile`` decodes uncompressed TIFF data by itself, but delegates every
compressed variant (LZW, JPEG, Deflate, Zstd, ...) to ``imagecodecs``. That
package is a declared dependency, so ``pip install tissueviewer`` always
provides it — but a deployment that puts the source checkout on
``PYTHONPATH`` instead of installing it never resolves the dependency list
and can run without it.

Nothing fails at import time in that case. The server starts, slides open,
and the DZI manifest is served normally; only the individual tile requests
fail, with a ``ValueError`` raised deep inside ``tifffile``. To the user the
slide simply renders blank, and the cause is visible only as a stack trace
in the server log. Worse, the failure is data-dependent: a library of
uncompressed slides works perfectly until the first compressed one arrives.

These helpers surface the problem once, loudly, at startup instead.
"""

from __future__ import annotations

import functools
import logging


logger = logging.getLogger(__name__)


# TIFF ``Compression`` tag value 1 means "no compression", the only case
# tifffile can handle without help.
COMPRESSION_NONE = 1

_MISSING_CODECS_MESSAGE = (
    "The 'imagecodecs' package is not installed. Uncompressed slides will "
    "still work, but any compressed OME-TIFF (LZW, JPEG, Deflate, Zstd, ...) "
    "will fail at tile-render time with a ValueError from tifffile. Install "
    "it with 'pip install imagecodecs'. Note that installing tissueviewer "
    "normally pulls this in automatically; a missing imagecodecs usually "
    "means the package is being run from a source checkout that was never "
    "pip-installed."
)


@functools.lru_cache(maxsize=1)
def imagecodecs_available() -> bool:
    """Return whether ``imagecodecs`` can be imported.

    Cached: the answer cannot change within a process, and this is consulted
    per file during ``--validate``.
    """
    try:
        import imagecodecs  # noqa: F401
    except ImportError:
        return False
    return True


def check_codec_support() -> bool:
    """Log a warning if compressed slides cannot be decoded.

    Returns the same value as :func:`imagecodecs_available` so callers can
    branch on it. Deliberately never raises — a server with an otherwise
    working library of uncompressed slides should still start.
    """
    if imagecodecs_available():
        return True
    logger.warning(_MISSING_CODECS_MESSAGE)
    return False


def missing_codec_reason(compression: int) -> str | None:
    """Return an explanation if ``compression`` cannot be decoded, else None.

    ``compression`` is the raw TIFF ``Compression`` tag value.
    """
    if compression == COMPRESSION_NONE or imagecodecs_available():
        return None
    return (
        f"compression type {compression} requires the 'imagecodecs' package, "
        "which is not installed"
    )


__all__ = [
    "COMPRESSION_NONE",
    "check_codec_support",
    "imagecodecs_available",
    "missing_codec_reason",
]
