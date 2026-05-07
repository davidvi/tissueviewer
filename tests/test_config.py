"""Configuration merging, env-var and YAML loading tests."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest
import yaml

from tissueviewer.config import Config


def _make_cli_args(**kwargs):
    defaults = {
        "host": None,
        "port": None,
        "recursive": None,
        "open_browser": None,
        "watch": None,
        "log_level": None,
        "no_save": False,
        "auth_username": None,
        "auth_password": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_defaults_are_stable():
    cfg = Config()
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8000
    assert cfg.save_enabled is True
    assert cfg.recursive is False
    assert cfg.log_level == "INFO"
    assert "red" in cfg.colors


def test_yaml_loading(tmp_path: Path):
    path = tmp_path / "cfg.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "host": "1.2.3.4",
                "port": 9090,
                "save_enabled": False,
                "recursive": True,
                "log_level": "DEBUG",
            }
        )
    )
    cfg = Config.from_yaml(path)
    assert cfg.host == "1.2.3.4"
    assert cfg.port == 9090
    assert cfg.save_enabled is False
    assert cfg.recursive is True
    assert cfg.log_level == "DEBUG"


def test_env_overrides_yaml(tmp_path: Path, monkeypatch):
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump({"host": "from.yaml", "port": 5000}))
    monkeypatch.setenv("TV_HOST", "from.env")
    monkeypatch.setenv("TV_PORT", "6000")

    cfg = Config.from_sources(cli_args=None, config_path=path, target=None)
    assert cfg.host == "from.env"
    assert cfg.port == 6000


def test_cli_overrides_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TV_HOST", "from.env")
    monkeypatch.setenv("TV_PORT", "6000")
    args = _make_cli_args(host="from.cli", port=7000)

    cfg = Config.from_sources(cli_args=args, config_path=None, target=None)
    assert cfg.host == "from.cli"
    assert cfg.port == 7000


def test_target_single_file(tiny_ome_tiff):
    cfg = Config.from_sources(
        cli_args=_make_cli_args(),
        config_path=None,
        target=tiny_ome_tiff,
    )
    cfg.validate()
    assert cfg.single_file == tiny_ome_tiff.resolve()
    assert cfg.data_dir == tiny_ome_tiff.parent.resolve()


def test_target_directory(data_dir: Path):
    cfg = Config.from_sources(
        cli_args=_make_cli_args(),
        config_path=None,
        target=data_dir,
    )
    cfg.validate()
    assert cfg.single_file is None
    assert cfg.data_dir == data_dir.resolve()


def test_validation_rejects_unsupported_suffix(tmp_path: Path):
    bad = tmp_path / "not-ome.txt"
    bad.write_text("hi")
    cfg = Config(single_file=bad)
    with pytest.raises(ValueError):
        cfg.validate()


def test_validation_rejects_missing_path(tmp_path: Path):
    cfg = Config(data_dir=tmp_path / "does-not-exist")
    with pytest.raises(ValueError):
        cfg.validate()


def test_validation_rejects_missing_target():
    cfg = Config()
    with pytest.raises(ValueError):
        cfg.validate()


def test_invalid_port():
    cfg = Config(data_dir=Path("."), port=70000)
    with pytest.raises(ValueError):
        cfg.validate()


def test_auth_disabled_by_default():
    cfg = Config()
    assert cfg.auth_enabled is False
    assert cfg.auth_username is None
    assert cfg.auth_password is None


def test_auth_enabled_when_both_set():
    cfg = Config(data_dir=Path("."), auth_username="alice", auth_password="hunter2")
    assert cfg.auth_enabled is True


def test_auth_validation_requires_both(tmp_path: Path):
    # data_dir is fine; we only want to trigger the auth pairing check.
    cfg = Config(data_dir=tmp_path, auth_username="alice")
    with pytest.raises(ValueError, match="auth_username and auth_password"):
        cfg.validate()

    cfg = Config(data_dir=tmp_path, auth_password="hunter2")
    with pytest.raises(ValueError, match="auth_username and auth_password"):
        cfg.validate()


def test_auth_yaml_loading(tmp_path: Path):
    path = tmp_path / "cfg.yaml"
    path.write_text(
        yaml.safe_dump(
            {"auth": {"username": "alice", "password": "hunter2"}}
        )
    )
    cfg = Config.from_yaml(path)
    assert cfg.auth_username == "alice"
    assert cfg.auth_password == "hunter2"


def test_auth_env_vars(monkeypatch):
    monkeypatch.setenv("TV_AUTH_USERNAME", "bob")
    monkeypatch.setenv("TV_AUTH_PASSWORD", "s3cret")
    cfg = Config.from_env()
    assert cfg.auth_username == "bob"
    assert cfg.auth_password == "s3cret"


def test_auth_cli_overrides_env_and_yaml(tmp_path: Path, monkeypatch):
    path = tmp_path / "cfg.yaml"
    path.write_text(
        yaml.safe_dump(
            {"auth": {"username": "from_yaml", "password": "p_yaml"}}
        )
    )
    monkeypatch.setenv("TV_AUTH_USERNAME", "from_env")
    monkeypatch.setenv("TV_AUTH_PASSWORD", "p_env")
    args = _make_cli_args(auth_username="from_cli", auth_password="p_cli")

    cfg = Config.from_sources(cli_args=args, config_path=path, target=None)
    assert cfg.auth_username == "from_cli"
    assert cfg.auth_password == "p_cli"
