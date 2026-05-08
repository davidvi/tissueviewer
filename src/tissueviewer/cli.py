"""Command-line entry point for TissueViewer."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .config import Config
from .logging_setup import configure_logging


logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tissueviewer",
        description=(
            "Standalone multi-channel OME-TIFF viewer with a built-in web UI."
        ),
    )
    parser.add_argument(
        "target",
        metavar="TARGET",
        nargs="?",
        default=None,
        help=(
            "Path to a single .ome.tif(f) file or a directory containing them. "
            "If omitted, --config must be given or TV_SLIDE_DIR must be set."
        ),
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        default=None,
        help="Include nested subdirectories when TARGET is a directory.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        metavar="FILE",
        help="Path to a YAML configuration file.",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=None,
        help="Listen port (default 8000).",
    )
    parser.add_argument(
        "-H",
        "--host",
        default=None,
        help="Bind address (default 127.0.0.1).",
    )
    parser.add_argument(
        "-o",
        "--open",
        dest="open_browser",
        action="store_true",
        default=None,
        help="Open the default web browser after the server starts.",
    )
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        default=None,
        help="Rescan the target when files change on disk.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Check that all OME-TIFFs can be opened, then exit.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Disable writing .sample.json files.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default INFO).",
    )
    parser.add_argument(
        "--auth-username",
        dest="auth_username",
        default=None,
        metavar="USER",
        help=(
            "Enable HTTP Basic auth with this username. Must be paired with "
            "--auth-password. For public deployments, prefer the "
            "TV_AUTH_USERNAME/TV_AUTH_PASSWORD env vars to keep credentials "
            "out of shell history."
        ),
    )
    parser.add_argument(
        "--auth-password",
        dest="auth_password",
        default=None,
        metavar="PASS",
        help=(
            "Password for HTTP Basic auth. Must be paired with --auth-username. "
            "Note: this value is visible in shell history and `ps`; prefer "
            "TV_AUTH_PASSWORD or a YAML config file with restricted permissions."
        ),
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"tissueviewer {__version__}",
    )
    return parser


def _resolve_config(args: argparse.Namespace) -> Config:
    target: Optional[Path] = Path(args.target) if args.target else None
    return Config.from_sources(
        cli_args=args,
        config_path=args.config,
        target=target,
    )


def main(argv: Optional[List[str]] = None) -> int:
    """Parse CLI arguments and run the server (or --validate).

    Returns an exit code; ``sys.exit`` is called when invoked as a script.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        config = _resolve_config(args)
    except ValueError as exc:
        parser.error(str(exc))
        return 2  # parser.error exits, this is belt-and-braces

    configure_logging(config.log_level)

    try:
        config.validate()
    except ValueError as exc:
        parser.error(str(exc))  # raises SystemExit(2)
        return 2  # unreachable; keeps type checkers happy

    if args.validate:
        from .validation import run_validation

        return run_validation(config)

    # Defer import so `tissueviewer --version` / --help don't pull in uvicorn.
    from .server import run_server

    try:
        run_server(config)
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        print("\nInterrupted.")
        return 0
    return 0


# Public alias for tests and external callers.
build_parser = _build_parser


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
