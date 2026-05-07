"""CLI parsing and entry-point tests."""

from __future__ import annotations

import pytest

from tissueviewer.cli import build_parser, main


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "tissueviewer" in out.lower()


def test_help_flag():
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_missing_target_errors(monkeypatch):
    # No target, no config, no TV_SLIDE_DIR env.
    monkeypatch.delenv("TV_SLIDE_DIR", raising=False)
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_parser_recognizes_core_flags():
    parser = build_parser()
    ns = parser.parse_args(
        [
            "/tmp/whatever",
            "-p",
            "9000",
            "-H",
            "0.0.0.0",
            "--recursive",
            "--open",
            "--watch",
            "--no-save",
            "--log-level",
            "DEBUG",
        ]
    )
    assert ns.target == "/tmp/whatever"
    assert ns.port == 9000
    assert ns.host == "0.0.0.0"
    assert ns.recursive is True
    assert ns.open_browser is True
    assert ns.watch is True
    assert ns.no_save is True
    assert ns.log_level == "DEBUG"


def test_parser_recognizes_auth_flags():
    parser = build_parser()
    ns = parser.parse_args(
        [
            "/tmp/whatever",
            "--auth-username",
            "alice",
            "--auth-password",
            "hunter2",
        ]
    )
    assert ns.auth_username == "alice"
    assert ns.auth_password == "hunter2"


def test_validate_flag_runs(monkeypatch, data_dir, capsys):
    # ``--validate`` must run without starting the server and exit 0 here.
    rc = main([str(data_dir), "--recursive", "--validate"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "files OK" in out
