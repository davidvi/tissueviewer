# Contributing to TissueViewer

## Local setup

```bash
git clone https://github.com/davidvi/tissueviewer.git
cd tissueviewer
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest
```

Run the CLI from the source checkout:

```bash
tissueviewer /path/to/slide.ome.tiff
```

## Repository layout

```
src/tissueviewer/        Python package
  formats/               Pluggable image-format handlers (OME-TIFF today)
  routes/                FastAPI endpoint modules
  web/                   Pre-built Vue client, shipped inside the wheel
client/                  Vue source — only needed to rebuild the UI
scripts/sync_client.py   Copies client/dist → src/tissueviewer/web
tests/                   Pytest suite
```

## Rebuilding the web UI

The `src/tissueviewer/web/` directory is committed so that installing from
source does not require Node.js. When you change anything in `client/src`,
rebuild the bundle and re-sync it:

```bash
cd client
npm install
npm run build
cd ..
python scripts/sync_client.py
```

Then commit the updated contents of `src/tissueviewer/web/`.

## Coding guidelines

- Python 3.10+.
- Keep the HTTP surface byte-for-byte compatible with the bundled Vue
  client. The URL shape `/{location}/{chs}/{rgb}/{colors}/{gains}/{file}.dzi`
  (and the windowed `mins/maxs` variant) must stay exactly as-is; the
  pre-built client is not rebuilt per release.
- When splitting routes into modules, register windowed tile/DZI endpoints
  **before** the non-windowed ones. FastAPI matches routes in registration
  order.
- Use `logging.getLogger(__name__)` — no `print()` calls in library code.
- Keep `opencv-python-headless` (not `opencv-python`) in dependencies.

## Release

```bash
# Bump version in src/tissueviewer/__init__.py and pyproject.toml.
# Ensure src/tissueviewer/web/ is up to date.
python scripts/sync_client.py
python -m build
# Sanity check that web assets are in the wheel:
python -m zipfile -l dist/*.whl | grep web/
twine upload dist/*
```

## Filing issues

Please include:

- Python version and platform.
- `pip show tissueviewer` output.
- A small OME-TIFF that reproduces the bug, or (if data is sensitive) the
  OME-XML header and `tifffile.TiffFile(path).series[0].axes/shape/dtype`.
