# TissueViewer

Standalone multi-channel OME-TIFF viewer with a built-in web UI.

Point it at a file or a folder and open your browser.

![TissueViewer Screenshot](https://github.com/davidvi/TissueViewer/raw/main/img/screenshot.png)

## Contents

- [What it is](#what-it-is)
- [Supported formats](#supported-formats)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Command-line reference](#command-line-reference)
- [Environment variables](#environment-variables)
- [Configuration file](#configuration-file)
- [Filename conventions](#filename-conventions)
- [Programmatic use](#programmatic-use)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Docker migration](#docker-migration)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## What it is

TissueViewer is a zero-config viewer for high-resolution multi-channel
microscopy images. It serves deep-zoom tiles over HTTP and ships with a
pre-built [OpenSeadragon](https://openseadragon.github.io/) front-end that
lets you colourise channels, adjust gains and windowing, and save per-slide
settings.

## Supported formats

- **OME-TIFF** (`.ome.tif`, `.ome.tiff`) — any bit depth, any number of
  channels, with or without a built-in pyramid.

Support for additional formats (plain TIFF, OME-Zarr) is planned as
pluggable handlers; see `src/tissueviewer/formats/` for the registry.

## Installation

```bash
pip install tissueviewer
```

Or from a source checkout:

```bash
git clone https://github.com/davidvi/tissueviewer.git
cd tissueviewer
pip install .
```

Requires Python 3.10 or later. On macOS / Linux / Windows.

## Quick start

Open a single file:

```bash
tissueviewer /path/to/slide.ome.tiff
```

Browse a folder of slides (root folder becomes the `public` location):

```bash
tissueviewer /path/to/slides
```

Browse a nested tree of folders:

```bash
tissueviewer /path/to/slides --recursive --open
```

Use a config file:

```bash
tissueviewer --config config.yaml
```

Check every file in a directory can be opened, then exit:

```bash
tissueviewer /path/to/slides --validate
```

## Command-line reference

```
usage: tissueviewer [TARGET] [options]

positional:
  TARGET                Path to an .ome.tif(f) file or a directory of them.

options:
  -r, --recursive       Include nested subdirectories.
  -c, --config FILE     YAML configuration file.
  -p, --port N          Listen port (default 8000).
  -H, --host HOST       Bind address (default 127.0.0.1).
  -o, --open            Open the default web browser after start.
  -w, --watch           Rescan TARGET on filesystem changes.
      --validate        Verify every OME-TIFF, then exit.
      --no-save         Disable writing .sample.json sidecars.
      --log-level LEVEL DEBUG | INFO | WARNING | ERROR  (default INFO).
  -V, --version         Show version and exit.
  -h, --help            Show help and exit.
```

`TARGET` is optional if either `--config` is given or `TV_SLIDE_DIR` is set.

## Environment variables

Kept for backward compatibility with the Docker deployment. CLI and config
values take precedence.

| Variable       | Effect                                              |
|----------------|-----------------------------------------------------|
| `TV_SLIDE_DIR` | Default data directory (equivalent to positional TARGET). |
| `TV_HOST`      | Default bind address.                               |
| `TV_PORT`      | Default listen port.                                |
| `TV_SAVE`      | `false`/`0`/`no` disables sample.json writes.       |
| `TV_LOG_LEVEL` | Default log level.                                  |

## Configuration file

```yaml
# config.yaml
data_dir: /srv/tissue-viewer/slides
recursive: true
host: 0.0.0.0
port: 8000
save_enabled: false
log_level: INFO
colors:
  - red
  - green
  - blue
```

```bash
tissueviewer --config config.yaml
```

Precedence (highest wins): CLI flags → environment variables → YAML →
built-in defaults.

## Filename conventions

All recognized slide files end in `.ome.tif` or `.ome.tiff` (case-insensitive).

For a slide named `patient42.ome.tiff`, two sidecar files may appear next
to it:

| File                        | Who writes it       | Purpose                                             |
|-----------------------------|---------------------|-----------------------------------------------------|
| `patient42.sample.json`     | the web UI          | Per-slide channel colours / gains / annotations.    |
| `patient42.metadata.json`   | TissueViewer itself | Cache of OME-XML metadata; regenerated on mtime.    |

Delete them freely to reset.

### Locations

The web UI groups slides into *locations*. The mapping:

- Single-file mode → the file lives under the `public` location.
- Directory mode (no `--recursive`) → files at the root → `public`; every
  immediate subdirectory → its own location named after the subdirectory.
- Directory mode with `--recursive` → files at the root still go to
  `public`; files in nested subdirectories are grouped under a slash-joined
  location path like `2024/batch_A`.

## Programmatic use

`create_app` builds a regular FastAPI instance, suitable for any ASGI
server (uvicorn, hypercorn, daphne).

```python
from tissueviewer import Config, create_app

app = create_app(Config(data_dir="/srv/slides", recursive=True))
```

```bash
uvicorn my_module:app --host 0.0.0.0 --port 8000
```

## Troubleshooting

- **`ModuleNotFoundError: imagecodecs`** — install `imagecodecs` or
  reinstall `tissueviewer`; many OME-TIFFs use LZW/JPEG/Zstd compression.
- **Port already in use** — `tissueviewer --port 8001`.
- **Blank tiles / wrong colours** — delete the slide's `.sample.json` to
  reset settings, then reload.
- **Apple Silicon wheels** — `imagecodecs` and `opencv-python-headless`
  ship arm64 wheels; no local build required.
- **Zarr 2 vs 3** — both are supported. The pin is `zarr>=2.15,<4`.
- **OpenCV GUI warning** — `tissueviewer` depends on
  `opencv-python-headless`; a warning about `cv2.imshow` not being
  available is normal and harmless.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for local setup, how to rebuild the
Vue UI, and how to cut a release.

## Docker migration

TissueViewer used to ship as a Docker image with a Java-based
`bioformats2raw` conversion pipeline. That mode is gone in 0.2; see
[MIGRATION.md](MIGRATION.md) for guidance.

## License

Creative Commons Attribution-NonCommercial 4.0 International — see
[LICENSE.md](LICENSE.md).

## Acknowledgements

TissueViewer uses [OpenSeadragon](https://openseadragon.github.io/) for
high-performance tiled image visualisation.
