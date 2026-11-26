# Plan: NISAR data access + LiCSBAS2 backports (v3 / `towards-v3`)

Branch: `towards-v3` · Repos: `LiCSBAS` (v3, active) · `licsar_extra` (module provider) · `LiCSBAS2` + `licsar_proc` (read-only reference).

Sync rule: commit + push **before** and **after** each task.

---

## Task 1 — NISAR GUNW/GSLC ingest into LiCSBAS v3

### 1.0 Fix `licsar_extra` imports first (so loading actually works)

Current problems in `licsar_extra/python/`:
- `nisar_data.py`: `from LiCSAR_misc import *` — **unused** anywhere (only `grep` is
  *shell* `grep`). This import would fail on a clean install (no `LiCSAR_misc` module in
  `licsar_extra`) and masks the real dependency surface. → **remove it.**
- `nisar_data.py`: `import lics_proc_tools as lp` — fine when modules are top-level
  (PYTHONPATH) but breaks under the `licsar_extra.*` packaging. → make robust
  (try top-level, fall back to `from licsar_extra import licsar_tools`). *Note: licsar_extra
  imports are top-level by convention, so keep `lics_proc_tools` but guard it.*
- `lics_proc_tools.py`: self-contained except a lazy `import lics_unwrap` inside funcs and
  a local `runcmd` (correct—does **not** depend on `LiCSAR_misc`). → no change needed.
- NISAR-only third-party deps not in requirements: `asf_search, geopandas, shapely, pyproj,
  h5py, dask, rasterio, requests`. → add to `requirements.txt` (NISAR path is optional at
  runtime; the LiCSBAS step imports `nisar_data` lazily and exits with a clear message
  if deps are missing).

Verified: `lisar_proc` `nisardata.py` uses `lsr.bbox_to_wkt` / `lp.cliparea_geo2coords` —
both exist in `lics_proc_tools.py`, so the LiCSBAS-bbox API is available.

API we will call (all in `nisar_data.py`):
- `get_nisar_data(wkt, dtype='GUNW'|'GSLC', startdate, enddate, outAspd=True, shortpd=True)`
  → `geopandas.GeoDataFrame` with `sceneName,url,flightDirection,pathNumber,frameNumber,geometry`.
- `download_nisar_datapd(nsrs, nisarslcpath)` → `(num_downloaded, [paths])` (ASF creds via
  `~/.asf_credentials` or `$LiCSAR_configpath/asf_credentials`).
- `get_frameid(fileid)` → `frame_id = ff[5]+ff[6]+'_'+ff[7]` (compatibility id; used for
  per-frame subfolders).
- WKT from LiCSBAS `-g lon1/lon2/lat1/lat2`: `lp.cliparea_geo2coords(g, outputaswkt=True)`
  or `lp.bbox_to_wkt`.

### 1.1 New step `licsbas/steps/_01_get_nisar_gunw.py`  (`licsbas-01get-nisar-gunw`)

Behavior (mirrors `earthquake_responder.py:861+` + `fullchain`):
```
- g  lon1/lon2/lat1/lat2      (LiCSBAS bbox, required)
- t/--type   GUNW | GSLC       (default GUNW)
- s startdate  YYYYMMDD        (default 20250101)
- e enddate    YYYYMMDD        (default today)
- o outdir                  (default ./NISAR_<type>)
```
1. `wkt = lp.cliparea_geo2coords(g, outputaswkt=True)`.
2. `nsrs = nd.get_nisar_data(wkt, dtype=type, startdate, enddate, outAspd=True, shortpd=True)`.
3. Group scenes by `frame_id = nd.get_frameid(sceneName)` → download each group into
   `outdir/<frame_id>/` via `download_nisar_datapd` (skips already-downloaded `.h5`).
4. Warn if no ASF credentials / `asf_search` missing (do **not** hard-fail during import).
5. Print summary table: frame_id, n_scenes, first/last date, path.

Guard imports (`nisar_data`, `asf_search`, …) in `try/except ImportError` ⇒ clear
"install NISAR deps" message, matching the `lics_unwrap` import pattern in `_02to05_unwrap`.

### 1.2 Port `LiCSBAS_asf2geoc.py` → `licsbas/scripts/_asf2geoc.py`  (`licsbas-asf2geoc`)

Self-contained (GDAL-only). One LiCSBAS2-specific import to adapt:
- `import LiCSBAS_tools_lib as tools_lib; tools_lib.get_n_cpu_avail()` →
  keep the existing graceful fallback to `multiprocessing.cpu_count()` (already there),
  and additionally try `licsbas.tools_lib` (v3) before falling back.
Otherwise: 1:1 port (converts ASF `*_unw_phase.tif/_corr.tif/_lv_*/*` product dirs into
LiCSBAS `GEOC/` layout: `*.geo.unw.tif`, `*.geo.cc.tif`, `X.geo.{E,N,U}.tif`, `X.geo.hgt.tif`,
`metadata.txt` with `center_time`+`radar_freq`).

### 1.3 Entry points + docs

- pyproject: add `licsbas-01get-nisar-gunw = licsbas.steps._01_get_nisar_gunw:main` and
  `licsbas-asf2geoc = licsbas.scripts._asf2geoc:main`.
- New `docs/05_nisar.md`: both tools, ASF credential setup, expected NISAR file naming
  (`NISAR_L2_PR_{GUNW,GSLC}_...`), frame-id convention, and how the output feeds
  `licsbas-02ml-prep`.
- README: add a short "NISAR data (experimental)" note + link.
- `licsbas/steps/__init__.py` + `licsbas/scripts/__init__.py`: new `__all__` entries.
- Test: `tests/test_nisar_step.py` (CLI `--help`, import guard behaviour, arg parsing)
  without network; skip real download.

---

## Task 2 — Selective backports from LiCSBAS2 (prioritized)

Two trees diverged (v3 = modern xarray/dask rewrite). We port only concrete, low-risk,
clearly-beneficial fixes. Decisions:

| Commit        | Step | What | Action | Why |
|---------------|------|------|--------|-----|
| `2627e50`     | 02   | `cc.astype(np.uint8)` NaN-cast warning → `np.clip(np.nan_to_num(cc),0,255).astype(np.uint8)` | **PORT** (v3 has the bug, 1 line) | avoids undefined cast / silent corruption |
| `98cd3a8`#174 | 02   | EQA.dem_par corner shifted by half *original* pixel, then spacing scaled → off by (n-1)/2 px for `-n>1` | **PORT** (v3 has bug, 4 sites) | georeferencing correctness for multilooked data |
| `fcd0b6d`#178 | 03   | `gdal.Warp(outputBounds=centers)` → off 0.5 px; pass **outer edges** (center ± ½px) | **PORT** core geometry fix + record grid in `sltd/sltd_grid.txt` | GACOS delay sampled 0.5px off at edges |
| `51f09b6`#173 | 02   | radar_freq: `--freq` > `metadata.txt` > default (currently v3 ignores metadata.txt) | **PORT** | correct radar_freq when metadata provides it |

Deliberately **deferred** (feature / larger, or not present in v3):
- `12_loop_closure`: `--keep_ifg_list` (`ab3f6e5`), `n_unw` counting discarded IFGs (`e1fecea`).
- `14_vel_std`: make `vstd` optional/off-by-default (`be6a95f`).
- `16_filt_ts`: stable-ref re-referencing (`caf29de`), LP linear-fit (`f0bd592`), IndexError (`9a0e66b`).
- `aria2geoc` NISAR sign flip (`ce10acf`) — v3 has no `aria2geoc`.
- New scripts `sweets2geoc`, `align_geoc` — separate features; note in TODONEXT.

All backports add a short comment referencing the LiCSBAS2 commit/PR, keep v3 structure,
and come with a note in CHANGELOG.

---

## Out of scope (record in TODONEXT.md)
- `lics_processing.py` / `earthquake_responder.py` full pipeline (operational, not needed here).
- `sweets2geoc` / `align_geoc` ports.
- Full `nisar_data.generate_ifg` reprocessing path (keep v3 to `download + organize`).
