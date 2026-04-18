"""TissueViewer — standalone OME-TIFF viewer with a built-in web UI."""

__version__ = "0.2.0"

from .config import Config
from .app import create_app

__all__ = ["__version__", "Config", "create_app"]
