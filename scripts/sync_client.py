#!/usr/bin/env python3
"""Copy the pre-built Vue client into ``src/tissueviewer/web/``.

Run this after rebuilding the UI (``cd client && npm run build``) and before
packaging the wheel. Committing the synced ``web/`` directory lets users
install the project from a source checkout without needing Node.js.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CLIENT_DIST = REPO_ROOT / "client" / "dist"
TARGET = REPO_ROOT / "src" / "tissueviewer" / "web"


def main() -> int:
    if not CLIENT_DIST.is_dir():
        print(
            f"ERROR: client/dist not found at {CLIENT_DIST}.\n"
            "Build the client first:\n"
            "  cd client && npm install && npm run build",
            file=sys.stderr,
        )
        return 1
    index = CLIENT_DIST / "index.html"
    if not index.is_file():
        print(f"ERROR: {index} is missing.", file=sys.stderr)
        return 1

    if TARGET.exists():
        shutil.rmtree(TARGET)
    shutil.copytree(CLIENT_DIST, TARGET)
    print(f"Copied {CLIENT_DIST} → {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
