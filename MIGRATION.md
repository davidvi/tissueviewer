# Migration guide: Docker → pip

TissueViewer 0.2 drops the Docker/Java delivery and becomes a pure-Python
package. This document summarizes what changed and how to move forward.

## What's gone

- **`Dockerfile`** and **`cloud-deploy/`** — deleted. The Docker image
  included a JRE and `bioformats2raw` to transcode arbitrary vendor
  formats to OME-Zarr on the fly. That conversion pipeline is no longer
  part of the viewer.
- **`server/server.py`** — the legacy OME-Zarr server.
- **`server/watch_folder.py`** — the bioformats2raw watcher.
- **`server/OmeZarrConnector/`** — removed.
- **`/uploadSample`, `/sampleStats`, `/deleteSample` HTTP endpoints** —
  removed. Upload functionality lived in the upload view and required
  server-side disk management; it is out of scope for a file-based
  viewer. The upload view in the bundled Vue UI will simply error — the
  rest of the app works.
- **Volume mounts `/tv-import` and `/tv-store`** — no longer used. Point
  TissueViewer at any directory.

## What stayed the same

- Filename conventions: `.ome.tif` / `.ome.tiff` slides with optional
  `.sample.json` and `.metadata.json` sidecars next to each file.
- HTTP surface used by the Vue client: `/`, `/favicon.ico`, `/assets/*`,
  `/images/*`, `/samples.json`, `/histogram/...`, the DZI and tile URLs,
  and `/save/{location}/{file}`.
- Environment variables `TV_SLIDE_DIR`, `TV_HOST`, `TV_PORT`, `TV_SAVE`
  still work (in addition to the new CLI flags and YAML config).

## Moving your data

If you were running the old Docker image with mounted volumes, your
OME-TIFF files are already usable — just point the CLI at the folder:

```bash
# old
docker run -p 8080:8080 \
  -v /data/import:/tv-import \
  -v /data/store:/tv-store \
  tv

# new
pip install tissueviewer
tissueviewer /data/store --port 8080 --host 0.0.0.0
```

If your `/tv-store` directory still contains OME-Zarr subtrees created by
bioformats2raw, those are **not** supported by this version. Two options:

1. **Convert to OME-TIFF once** using `bioformats2raw` followed by
   `raw2ometiff`, or use `tifffile` directly:

   ```bash
   bioformats2raw input.svs out.zarr
   raw2ometiff out.zarr output.ome.tiff
   ```

2. **Stay on the old Docker image** for now. The 0.1.x releases on git
   history / container registries still work.

## Command-line translation

| Old                                    | New                                                   |
|----------------------------------------|-------------------------------------------------------|
| `docker run -v …:/tv-store tv`         | `tissueviewer /path/to/slides`                        |
| `TV_HOST=0.0.0.0`                      | `--host 0.0.0.0` or `TV_HOST=0.0.0.0`                 |
| `TV_PORT=8080`                         | `--port 8080` or `TV_PORT=8080`                       |
| `TV_SAVE=false`                        | `--no-save` or `TV_SAVE=false`                        |
| watch folder & auto-convert on change  | `--watch` (rescan only — no conversion)               |

## Reverse proxy / network access

Unchanged. Bind to `0.0.0.0` and put nginx/Caddy/etc. in front:

```bash
tissueviewer /data/slides --host 0.0.0.0 --port 8000
```
