"""Smoke tests that hit the FastAPI app via TestClient."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tissueviewer.app import create_app
from tissueviewer.config import Config


@pytest.fixture
def client(tiny_ome_tiff: Path):
    config = Config(
        single_file=tiny_ome_tiff,
        data_dir=tiny_ome_tiff.parent,
        save_enabled=True,
    )
    app = create_app(config)
    with TestClient(app) as c:
        yield c


def test_root_serves_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    # The bundled index.html contains this div.
    assert '<div id="app">' in resp.text


def test_favicon(client):
    resp = client.get("/favicon.ico")
    assert resp.status_code == 200
    assert len(resp.content) > 0


def test_samples_json(client, tiny_ome_tiff: Path):
    resp = client.get("/samples.json?location=public")
    assert resp.status_code == 200
    body = resp.json()
    assert body["save"] is True
    assert isinstance(body["colors"], list)
    names = [s["name"] for s in body["samples"]]
    assert "sample" in names


def test_dzi_endpoint(client):
    url = "/public/0;1/false/red;green/1.0;1.0/sample.dzi"
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"<Image" in resp.content
    assert b"TileSize=" in resp.content


def test_tile_endpoint(client):
    url = "/public/0;1/false/red;green/1.0;1.0/sample_files/6/0_0.jpeg"
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/jpeg")
    assert resp.content[:3] == b"\xff\xd8\xff"  # JPEG magic


def test_save_disabled(tiny_ome_tiff: Path):
    config = Config(
        single_file=tiny_ome_tiff,
        data_dir=tiny_ome_tiff.parent,
        save_enabled=False,
    )
    app = create_app(config)
    with TestClient(app) as c:
        resp = c.post("/save/public/sample", json={"foo": "bar"})
        assert resp.status_code == 403


def test_save_writes_sidecar(client, tiny_ome_tiff: Path):
    payload = {"channels": [{"color": "red", "gain": 1.0}]}
    resp = client.post("/save/public/sample", json=payload)
    assert resp.status_code == 200
    sidecar = tiny_ome_tiff.parent / "sample.sample.json"
    assert sidecar.exists()
    import json

    assert json.loads(sidecar.read_text()) == payload


def test_histogram(client):
    resp = client.get("/histogram/public/0/sample")
    assert resp.status_code == 200
    body = resp.json()
    assert "bins" in body
    assert len(body["bins"]) == 64


# ---------------------------------------------------------------------------
# HTTP Basic auth
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_client(tiny_ome_tiff: Path):
    config = Config(
        single_file=tiny_ome_tiff,
        data_dir=tiny_ome_tiff.parent,
        save_enabled=True,
        auth_username="alice",
        auth_password="hunter2",
    )
    app = create_app(config)
    with TestClient(app) as c:
        yield c


def test_auth_blocks_unauthenticated_root(auth_client):
    resp = auth_client.get("/")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"].lower().startswith("basic")


def test_auth_blocks_unauthenticated_static(auth_client):
    # Static assets should also be gated.
    resp = auth_client.get("/favicon.ico")
    assert resp.status_code == 401


def test_auth_blocks_unauthenticated_api(auth_client):
    resp = auth_client.get("/samples.json?location=public")
    assert resp.status_code == 401


def test_auth_rejects_wrong_password(auth_client):
    resp = auth_client.get("/", auth=("alice", "wrong"))
    assert resp.status_code == 401


def test_auth_rejects_wrong_user(auth_client):
    resp = auth_client.get("/", auth=("eve", "hunter2"))
    assert resp.status_code == 401


def test_auth_rejects_malformed_header(auth_client):
    resp = auth_client.get("/", headers={"Authorization": "Basic not-base64!!"})
    assert resp.status_code == 401


def test_auth_accepts_correct_credentials(auth_client):
    resp = auth_client.get("/", auth=("alice", "hunter2"))
    assert resp.status_code == 200
    assert '<div id="app">' in resp.text


def test_auth_off_when_unconfigured(client):
    # The default ``client`` fixture has no auth set; root should be public.
    resp = client.get("/")
    assert resp.status_code == 200
