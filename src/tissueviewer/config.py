"""Configuration dataclass with layered loading (CLI > env > YAML > defaults)."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml


DEFAULT_COLORS = [
    "red",
    "green",
    "blue",
    "yellow",
    "magenta",
    "cyan",
    "white",
]


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in ("true", "1", "yes", "on")


@dataclass
class Config:
    """Runtime configuration for a TissueViewer instance.

    Exactly one of ``data_dir`` or ``single_file`` is required.
    """

    data_dir: Optional[Path] = None
    single_file: Optional[Path] = None
    host: str = "127.0.0.1"
    port: int = 8000
    save_enabled: bool = True
    recursive: bool = False
    open_browser: bool = False
    watch: bool = False
    colors: list[str] = field(default_factory=lambda: list(DEFAULT_COLORS))
    tile_cache_size: int = 4
    log_level: str = "INFO"

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_yaml(cls, path: Path) -> "Config":
        """Load a configuration from a YAML file."""
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        if not isinstance(raw, Mapping):
            raise ValueError(f"YAML config at {path} must be a mapping")
        return cls._from_mapping(raw)

    @classmethod
    def _from_mapping(cls, data: Mapping[str, Any]) -> "Config":
        kwargs: dict[str, Any] = {}
        for name in (
            "host",
            "port",
            "save_enabled",
            "recursive",
            "open_browser",
            "watch",
            "tile_cache_size",
            "log_level",
        ):
            if name in data and data[name] is not None:
                kwargs[name] = data[name]

        if "data_dir" in data and data["data_dir"] is not None:
            kwargs["data_dir"] = Path(data["data_dir"]).expanduser()
        if "single_file" in data and data["single_file"] is not None:
            kwargs["single_file"] = Path(data["single_file"]).expanduser()
        if "colors" in data and data["colors"] is not None:
            kwargs["colors"] = list(data["colors"])

        # Coerce bools that may come in as strings from YAML.
        for bool_key in ("save_enabled", "recursive", "open_browser", "watch"):
            if bool_key in kwargs:
                kwargs[bool_key] = _to_bool(kwargs[bool_key])

        if "port" in kwargs:
            kwargs["port"] = int(kwargs["port"])
        if "tile_cache_size" in kwargs:
            kwargs["tile_cache_size"] = int(kwargs["tile_cache_size"])

        return cls(**kwargs)

    @classmethod
    def from_env(cls) -> "Config":
        """Build a Config from ``TV_*`` environment variables only."""
        env_map: dict[str, Any] = {}
        if os.getenv("TV_SLIDE_DIR"):
            env_map["data_dir"] = os.environ["TV_SLIDE_DIR"]
        if os.getenv("TV_HOST"):
            env_map["host"] = os.environ["TV_HOST"]
        if os.getenv("TV_PORT"):
            env_map["port"] = os.environ["TV_PORT"]
        if os.getenv("TV_SAVE") is not None:
            env_map["save_enabled"] = _to_bool(os.environ["TV_SAVE"])
        if os.getenv("TV_LOG_LEVEL"):
            env_map["log_level"] = os.environ["TV_LOG_LEVEL"]
        return cls._from_mapping(env_map)

    @classmethod
    def from_sources(
        cls,
        *,
        cli_args: Optional[argparse.Namespace] = None,
        config_path: Optional[Path] = None,
        target: Optional[Path] = None,
    ) -> "Config":
        """Merge layered sources into a single ``Config``.

        Precedence (highest wins): CLI args > env vars > YAML file > defaults.
        ``target`` is the positional TARGET argument from the CLI (file or dir).
        """
        cfg = cls()  # defaults

        # YAML
        if config_path is not None:
            yaml_cfg = cls.from_yaml(config_path)
            cfg = _merge(cfg, yaml_cfg)

        # Env
        env_cfg = cls.from_env()
        cfg = _merge(cfg, env_cfg)

        # CLI
        cli_cfg_updates: dict[str, Any] = {}
        if cli_args is not None:
            for attr in (
                "host",
                "port",
                "recursive",
                "open_browser",
                "watch",
                "log_level",
            ):
                val = getattr(cli_args, attr, None)
                if val is not None:
                    cli_cfg_updates[attr] = val
            if getattr(cli_args, "no_save", False):
                cli_cfg_updates["save_enabled"] = False
        if cli_cfg_updates:
            cfg = replace(cfg, **cli_cfg_updates)

        # TARGET takes precedence over data_dir from env/YAML.
        if target is not None:
            target = target.expanduser().resolve()
            if target.is_file():
                cfg = replace(cfg, single_file=target, data_dir=target.parent)
            else:
                cfg = replace(cfg, data_dir=target, single_file=None)

        return cfg

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> None:
        """Raise ``ValueError`` if the configuration is not usable."""
        if self.single_file is None and self.data_dir is None:
            raise ValueError(
                "No TARGET specified: provide a file or directory on the command "
                "line, set TV_SLIDE_DIR, or use --config."
            )
        if self.single_file is not None:
            if not self.single_file.exists():
                raise ValueError(f"Single file not found: {self.single_file}")
            name_lower = self.single_file.name.lower()
            if not (name_lower.endswith(".ome.tif") or name_lower.endswith(".ome.tiff")):
                raise ValueError(
                    f"Only .ome.tif/.ome.tiff files are supported (got {self.single_file.name})"
                )
        elif self.data_dir is not None:
            if not self.data_dir.exists():
                raise ValueError(f"Data directory not found: {self.data_dir}")
            if not self.data_dir.is_dir():
                raise ValueError(f"Data path is not a directory: {self.data_dir}")

        if not (0 < self.port < 65536):
            raise ValueError(f"Invalid port: {self.port}")


def _merge(base: Config, overlay: Config) -> Config:
    """Return ``base`` with non-default fields from ``overlay`` applied."""
    defaults = Config()
    updates: dict[str, Any] = {}
    for f in base.__dataclass_fields__:
        overlay_val = getattr(overlay, f)
        default_val = getattr(defaults, f)
        if overlay_val != default_val:
            updates[f] = overlay_val
    if not updates:
        return base
    return replace(base, **updates)
