#!/usr/bin/env python3
"""
Development entry point — run directly without installing the package:

    python server.py /path/to/data --port 8000

This file adds src/ to sys.path so the tissueviewer package is importable
from the source tree, then delegates to the normal CLI. Every change to any
file under src/tissueviewer/ is picked up on the next run — no reinstall
needed.
"""

import sys
from pathlib import Path

# Make the package importable from the source tree without `pip install -e .`.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tissueviewer.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
