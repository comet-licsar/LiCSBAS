# 5. NISAR data (experimental)

> **Status:** experimental. These steps are optional and do **not** affect the
> classic LiCSAR workflow in [02_workflow.md](02_workflow.md). They require the
> extra `licsar_extra` package and the NISAR extras.

LiCSBAS is designed around LiCSAR (Sentinel-1) data downloaded from the
COMET-LiCS portal by `licsbas-get-geotiff`. For **NISAR** (NISAR L2 **GUNW —
the only product type used; GSLC is not needed**) and other ASF products we
provide the following tools:

| Tool | Entry point | What it does |
| --- | --- | --- |
| `licsbas-01-get-nisar-data` | `licsbas.steps._01_get_nisar_data` | Search ASF for NISAR GUNW in a bbox (per frame; `--list-frames` / `--frame` to select) and **download** the `.h5`, grouped into per-frame subfolders |
| `licsbas-asf2geoc` | `licsbas.scripts._asf2geoc` | Convert ASF *pre-processed* product directories (`*_unw_phase.tif`, `*_corr.tif`, `*_lv_*`, `*_dem.tif`, `*_amp.tif`) into a LiCSBAS `GEOC/` layout |

Both use LiCSBAS conventions (`long/lat` bounding boxes as `lon1/lon2/lat1/lat2`,
`licsbas-*` entry points) and are the starting point before
`licsbas-ml-prep` (step 02).

## 5.1 Install

```bash
pip install licsar_extra[nisar]          # asf_search, geopandas, shapely, pyproj, h5py, dask, rasterio, requests
# and make sure licsar_extra 'python/' is importable (e.g. pip install -e licsar_extra)
```

Optional ASF credentials (for authenticated / larger downloads):

```
# ~/.asf_credentials  (or $LiCSAR_configpath/asf_credentials)
ASF_USERNAME=you@example.com
ASF_PASSWORD=...
```

Without credentials the step will still fetch publicly accessible scene URLs.

## 5.2 `licsbas-01-get-nisar-data` (search + download)

```bash
# GUNW interferograms for a study area (LiCSBAS bbox: lon1/lon2/lat1/lat2)
licsbas-01-get-nisar-data -g -118.4/-118.2/33.8/33.7 -s 20250101 -e 20251231 -o NISAR_GUNW

# Only list the selection (no download)
licsbas-01-get-nisar-data -g -118.4/-118.2/33.8/33.7 --dry_run

# Which frames (tracks) are available here?
licsbas-01-get-nisar-data -g -118.4/-118.2/33.8/33.7 --list-frames

# Download only one (or a few) frame(s)
licsbas-01-get-nisar-data -g -118.4/-118.2/33.8/33.7 --frame 018A_01234 -o NISAR_GUNW
```

Options:

| Option | Meaning | Default |
| --- | --- | --- |
| `-g` | geographic extent `lon1/lon2/lat1/lat2` (required) | — |
| `--frame` | NISAR frame id(s) `FID[,FID2,...]` (e.g. `018A_01234`) — download only these | all |
| `--list-frames` | list the available frames + GUNW count per frame, then exit | off |
| `-s` / `-e` | start / end date `yyyymmdd` | `20250101` / today |
| `-o` | output directory | `./NISAR_GUNW` |
| `--max` | maximum scenes to fetch | `500` |
| `--dry_run` | search + list only, do not download | off |

Output layout (a NISAR **frame** is a track; its id — e.g. `018A_01234`,
`<line><pass>_<beam>` — is derived from the scene name via `get_frameid`):

```text
NISAR_GUNW/
├── 018A_01234/
│   ├── NISAR_L2_PR_GUNW_..._018_A_01234_....h5
│   └── NISAR_L2_PR_GUNW_..._018_A_01234_....h5
└── 019A_01235/
    └── NISAR_L2_PR_GUNW_..._019_A_01235_....h5
```

Existing non-empty files are not re-downloaded. Downloads are streamed over
HTTP through the `asf_search` session (no shell `wget`).

## 5.3 Converting to a LiCSBAS layout

There are two converters into the `GEOC/` layout, depending on your source:

| Tool | Source | When to use |
|---|---|---|
| `licsbas-nisar2geoc` (**recommended for NISAR**) | NISAR L2 PR **GUNW `.h5`** | You downloaded raw NISAR with §5.2 and want the iono + range-offset corrected time series. |
| `licsbas-asf2geoc` | pre-exported **GeoTIFF**s (unw/cc/E/N/U/hgt/mli) | You already have LiCSAR-style GeoTIFFs (ASF or the `nisar_data` export). |

Both produce the same directory structure and `metadata.txt`, and **all exported
GeoTIFFs (unw/cc of every IFG plus the top-level E/N/U, hgt) are written onto a
single shared WGS-84 grid** (first product defines it) with `DEFLATE`,
`PREDICTOR=2`, `TILED=YES` compression.

> **Frames (tracks):** one region is covered by several NISAR frames. Each
> frame subfolder is a **self-contained time series** — run the converter
> (and the rest of LiCSBAS) **once per frame**, producing one `GEOC/` per
> frame. GUNWs from different frames cannot be combined; `nisar2geoc` prints
> a warning if it sees a mixed-frame input.

### `licsbas-nisar2geoc` (NISAR GUNW `.h5` → `GEOC/`) — *recommended*

Converts NISAR L2 PR GUNW `.h5` into the LiCSBAS `GEOC/` layout. The unwrapped
phase is corrected the way `earthquake_responder.py` does it (the smooth
**ionospheric** and **range-offset** ramps are removed, a 2-D quadratic ramp is
removed unless range-offsets were already used, then a coherence-threshold mask
is applied). The WGS-84 conversion uses the **rasterio (`rio`)** approach of
`nisar_data.py` (`rio.write_crs` → `rio.to_raster` → `gdalwarp -t_srs EPSG:4326`).
It also writes a LiCSBAS-standard `baselines` file (per-pair `bperp`, read by
`io_lib.read_bperp_file`).

```bash
# one frame (track) per GEOC:
licsbas-nisar2geoc -i NISAR_GUNW/018A_01234 -o GEOC_018A_01234 \
    [-c lonmin/lonmax/latmin/latmax] [-t 0.5] [-f A|B] \
    [--no_iono] [--no_offsets] [--no_deramp_quad] \
    [-D] [-n 4] [--dry_run]
```

 -i  one frame folder (searched recursively), or a single GUNW `.h5`
 -t  coherence threshold for masking unw (default 0.5)
 -f  NISAR band `A` (1.27e9) or `B` (1.2215e9); fixes `radar_freq` in metadata
 --no_iono / --no_offsets / --no_deramp_quad — opt out of that correction
 -D  also try to fetch a NISAR DEM for `X.geo.hgt.tif` (needs earthaccess + net)
```text
GEOC/
├── 20250601_20250615/20250601_20250615.geo.unw.tif   # iono+range-offset corrected, cc-masked
├── 20250601_20250615/20250601_20250615.geo.cc.tif
├── X.geo.E.tif / X.geo.N.tif / X.geo.U.tif            # written once, from the first GUNW (radarGrid metadata)
├── X.geo.hgt.tif                                      # (if -D given)
├── baselines                                          # bperp per pair — LiCSBAS standard
└── metadata.txt                                       # center_time, radar_freq
```

### `licsbas-asf2geoc` (GeoTIFFs → `GEOC/`)

When an ASF/NISAR product has already been exported to GeoTIFFs (unwrapped
phase, coherence, look vectors, DEM, amplitude), convert that parent directory
into the `GEOC/` layout with a pure-GDAL warp:

```bash
licsbas-asf2geoc -i <parent_dir_of_ifg_dirs> -o GEOC \
    [-c lonmin/lonmax/latmin/latmax] [-t 0.5] [-n 4] [-r nearest]
```

It writes one `<pair>/<pair>.geo.{unw,cc}.tif` per product subdirectory plus the
top-level `X.geo.E/N/U/hgt/mli.tif` and `metadata.txt` (same layout as above,
minus `baselines`).

## 5.4 Feeding LiCSBAS

The `GEOC/` directory produced in §5.3 is what `licsbas-ml-prep` (step 02)
consumes. For NISAR, the recommended route is §5.2 (`_01_get_nisar_data`) →
§5.3 (`_nisar2geoc`) → `licsbas-ml-prep` → the rest of the workflow
([02_workflow.md](02_workflow.md)).

---
Also see: [01_installation.md](01_installation.md),
[02_workflow.md](02_workflow.md), [03_visualization.md](03_visualization.md).
