# Changelog — LiCSBAS

### 2026-12-19 (post-merge cleanups — phase bias + NISAR/python-batch merge)
- Merged upstream `towards-v3` (NISAR data-access, python `licsbas/batch.py`,
  `licsbas/steps`+`licsbas/scripts` split, 59 single-named entry points, new
  tutorials/flowcharts) with the 02op phase bias addition; conflicts resolved
  in `pyproject.toml` (upstream entry points + `licsbas-02op-phasebias`),
  `batch_LiCSBAS.sh` (upstream thin wrapper), `CHANGELOG.md`, `TODONEXT.md`.
  Phase bias now integrated in `licsbas/batch.py` (`--phasebias`), not the
  bash batch script.
- Fixed two latent bugs found by the post-merge mypy/test run: `extras.py`
  error message used `% e` formatting on a string containing `` `%matplotlib` ``
  (would crash with `ValueError` instead of reporting the real error) — now an
  f-string; `batch.py` re-annotated `argv` in the NISAR branch (mypy
  `no-redef` error). `licsbas.extras` (optional `viewer` extras) is now
  tolerated by `test_imports.py` when pygmt is absent.

## [unreleased] — branch `towards-v3`

### 2026-12-20 (NISAR step rename + slc.mli.par + “Output files” in -h)
- The NISAR download step is renamed to follow the “01 get geotiff” family
  convention: `licsbas/steps/_01_get_geotiff_nisar.py`, entry point
  `licsbas-01-get-geotiff-nisar`, wrapper `bin/LiCSBAS01_get_geotiff_NISAR.py`
  (next to `LiCSBAS01_get_geotiff.py` / `LiCSBAS01_get_geotiff_ALOS.py`).
  All references (batch, docs, tutorial, examples, tests, SKILL) updated.
- The step now documents the **output data structure** in its docstring
  (`NISAR_GUNW/<frame>/*.h5` + the `GEOC/` GeoTIFF layout of
  `nisar2geoc`), and prints it as an “Output files” section in `-h`
  (RawDescription epilog), like the other step-01 scripts.
- **`licsbas-nisar2geoc` now writes `slc.mli.par`** into `GEOC/`
  (`radar_frequency: <Hz>` for band A/B from `-f`; `center_time` when the
  product provides it). Previously the NISAR route produced no `slc.mli.par`,
  but downstream steps (03 GACOS, 130/132) derive the wavelength from
  `radar_frequency` there — this closes that gap.
- Step rewritten against the real `lisar_extra` API (`lisar_extra` top-level
  `nisar_data` + `lics_proc_tools`, `get_asf_session().get(..., stream=True)`
  streaming, `sizeMB` filter with `--max`); re-runs skip existing products;
  `--dry_run` only reports. Tests stub this API exactly (`tests/test_nisar_step.py`).

### 2026-12-20 (NISAR: GUNW-only + frame handling; portrait flowcharts)
**NISAR data access is now GUNW-only.** LiCSBAS does not use GSLC products, so
GSLC support was **removed entirely** from the NISAR chain: `nisar2geoc -E`
(GSLC for E/N/U + mli), the download step's `-t GUNW|GSLC` / `--gslc` options,
`batch.py`'s `pNISAR_type`/`pNISAR_gslc` and `--nisar-type/--nisar-gslc`, and
`example_4_nisar.py`'s `--type/--gslc`. `licsbas-nisar2geoc` no longer writes an
mli amplitude at all. (`licsbas-asf2geoc` still maps ASF's `*_amp.tif` to
`X.geo.mli.tif` — that is a GeoTIFF product, not a GSLC.)

**NISAR frames (tracks).** A region is covered by several NISAR frames, and each
frame is a self-contained time series (frame id `<line><pass>_<beam>`, e.g.
`018A_01234`, via `nisar_data.get_frameid`). New behaviour:
- `licsbas-01-get-nisar-data` gained **`--list-frames`** (lists the available
  frames + GUNW count per frame, then exits — no download) and **`--frame
  FID[,FID2,...]`** (download only the selected frame(s); unknown ids are
  rejected with the available list).
- `licsbas-nisar2geoc` **warns if the input GUNWs span more than one frame**
  (frames cannot be combined into one time series); help/`-i` doc now say
  explicitly: **one frame per `GEOC/`**.
- `batch.py`: `nisar2geoc` now gets an explicit **`-i`** (it was missing — it
  would have searched CWD); with exactly one selected frame
  (`--nisar-frames` / `pNISAR_frames`) `-i` points at that frame's subfolder.
- **E/N/U are written once**, derived from the **first GUNW's own `radarGrid`**
  metadata (the `earthquake_responder.py` approach — no GSLC needed);
  best-effort (skipped, with a note, if unavailable).

**Flowcharts are portrait now.** `tutorial/make_flowchart.py` defaults to
`rankdir=TB` (top-to-bottom) and `licsbas-batch --flowchart-landscape` was
removed; all four tutorial PNGs were regenerated vertically (`0_licsar.png`,
`0_nisar.png`, `0_sbovl.png`, `1_ts.png`). `licsbas/flowchart.py` still accepts
`rankdir` for opt-in LR layouts.

**Tutorial/docs/tests** — the NISAR tutorial cells now teach the per-frame
workflow (`--list-frames` then `--frame` then `nisar2geoc -i NISAR_GUNW/<frame>`);
`docs/05_nisar.md`, the NISAR flowchart config, `examples/example_4_nisar.py`
(`--frames`/`--outdir`) and the README row were updated accordingly. New tests:
`tests/test_nisar_step.py::test_list_frames_only` and `::test_frame_filter`
(stubbed, no network); `test_nisar_chain` now checks `-i NISAR_GUNW[/<frame>]`
and the `--frame` passthrough. Full suite: **90 passed, 2 skipped**.

**Color bars with units on step-0X/1X preview PNGs.** `plot_lib.make_im_png`
and `make_3im_png` accept a `cbar_label` argument now, and the per-IFG
previews that were colour-blind before (wrapped phase, e.g. the 02/02to05/
03/04/05/12/13/16 `*.png` previews) now render a color bar labelled **`rad`**;
quantity previews got units too (`mm/yr` for velocity, `mm` for intercept/
residual/DEM-err, `mm` for DEM/STC, `coherence` for the coherence maps of
steps 04/12). The step-15 `mask.png` was **not** touched (as requested). Full
suite still green (92 passed, 2 skipped incl. the merged 02op tests).

**Original `batch_LiCSBAS.sh` restored from `main`.** The python thin wrapper
was replaced by the full 856-line shell batch (settings block + step chain),
so **both** batch systems work: the traditional `./batch_LiCSBAS.sh` (calls the
`bin/LiCSBAS*.py` wrappers on PATH) and the v3 python engine
(`licsbas-batch` / `examples/example_*.py`).
### 2026-12-19 (phase bias correction operator — optional 02op step)
- New optional step `LiCSBAS02op_phasebias` (entry point
  `licsbas-02op-phasebias`, `licsbas/steps/_02op_phasebias.py`,
  `bin/LiCSBAS02op_phasebias.py` wrapper): runs the standalone `phasebias`
  package (https://github.com/comet-licsar/InSAR_PhaseBias_Correction,
  tag v1.1.0) — all 5 steps, sequential, with `--dry-run`, `--steps` resume,
  and auto-generated `config.txt`. Clear install guidance when the package
  is missing.
- Python batch: `BatchConfig(do02op_phasebias=True)` (+ `p02op_phasebias_out`,
  `p02op_phasebias_options`) / `licsbas-batch --phasebias`; step 02 then
  reads the corrected stack (`$p02op_phasebias_out/GEOC`).
- Companion repo work (tag v1.1.0): restructured into a pip-installable
  `phasebias` package (`phasebias-01..05` console entry points);
  `updated_previous` merged into `main` (old main preserved as
  `archive/chunk-based-main`); fixes: `np.VisibleDeprecationWarning` removed
  in numpy >= 1.25, unsorted `os.walk` order misaligning coherence/phase
  lists (root cause of step-03 `NoneType` crash), step-03 blocking
  `plt.show()` -> saved PNGs, step-05 no longer requires the
  `.geo.hgt.tif` DEM (falls back to any metadata raster as georeferencing
  template).
- Validated end-to-end on the 082D_05125_020000 test dataset (2017-2021,
  12407 ifgs): 1190 corrected interferograms written (a1=0.537, a2=0.350).

### 2026-12-19 (tutorial & documentation restructure; flowcharts; NISAR batch template)
**Tutorial** — the monolithic `tutorial/tutorial.ipynb` is kept as the *master single-file template*, and four composed tutorials are published from it (`tutorial/build_notebooks.py` re-generates them):
- `tutorial_0.ipynb` — **Module 0, LiCSAR data** (steps `0-1` → `0-5`), **plus a new ``02to05_unwrap`` alternative-route cell** that explains the *re-unwrapping* option (starts from the **wrapped** phase, does the unwrapping itself, and **substitutes steps `0-2` → `0-5`**).
- `tutorial_0_nisar.ipynb` — **Module 0, NISAR data** (experimental): `licsbas-01-get-nisar-data` (ASF search + GUNW/GSLC download) → `licsbas-nisar2geoc` (→ `GEOC/`, shared WGS-84 grid, `baselines`, `metadata.txt`; `--no_iono`/`--no_offsets`/`-D`) → the *same* steps `0-2` → `0-5`. The `licsbas-asf2geoc` (GeoTIFF) alternative is called out.
- `tutorial_0_sbovl.ipynb` — **SBOVNL (SBOI)** chain: steps `0-1` → `1-6` all with `--sbovl` (and the `--sbovl_abs` flavour), incl. the forced `120_choose_reference` and the skipped classic loop-closure `12`.
- `tutorial_1.ipynb` — **Module 1: time series**, steps `11` → `16` + viewers/exports (data-source agnostic; works on any Module-0 output). All four are cross-linked so a Binder session can jump between them in the same session, and each has fresh Binder + Colab badges.
- All four are `nbformat` 4.5 valid and their shared setup cell was smoke-tested on `nbconvert --execute` (idempotent, no hard GDAL/pip install on a ready env).

**Flowcharts** — new **PNG flowcharts**, rendered with Graphviz `dot` (landscape `LR` by default, portrait `TB` for the long SBOVNL chain), shown **just before the first script** of each notebook: `tutorial/0_licsar.png`, `0_nisar.png`, `0_sbovl.png`, `1_ts.png`. Configs live in `tutorial/tutorial_cfg/*.json`; regenerate with `python3 tutorial/make_flowchart.py` (no new Python dep — shells out to `dot`). `licsbas/flowchart.py` gained a `rankdir` argument, **alternative-route styling** (amber node + dashed edge from the divergence point + “(alternative route)” tag) and a `--flowchart-landscape` flag on `licsbas-batch`.

**Batch / docs** — added `examples/example_4_nisar.py`, a ready-to-adapt **NISAR GUNW** batch template (dry-run by default; `--execute` to run; `--gslc`, `--bbox`, `--no-iono/--no-offsets`, `--dem`, `--cc-thre`, …), completing the `standard` / `reunw_02to05` / `sbovl` / `nisar` template set. `README.md` is now minimal (installation detail moved to `docs/01_installation.md`) with a tutorials table (Binder + Colab per notebook); Badge/links point at the `towards-v3` branch until v3 lands on `main`.

**`bin/` wrappers** — the `"DEPRECATED wrapper …"` banner was removed from all 55 `bin/*.py` legacy wrappers (reworded to `"Legacy wrapper for the console entry point …"`); they remain the supported traditional PATH-based CLI.

### 2026-12-19 (backport of 4 LiCSBAS2 bug fixes into the v3 step-02/03 route)
Backported four concrete, low-risk fixes from the `LiCSBAS2` repo (each cited
inline in the code). The 02to05 reunw route was audited and needs **none** of
them (see below). Full suite still green (87 passed, 2 skipped).
- **`_02_ml_prep.py`: uint8 cast of coherence (`2627e50` #169)** — `cc.astype(
  np.uint8)` cast a residual NaN to an integer (undefined behaviour; a
  `RuntimeWarning` on numpy≥1.24). Now `np.clip(np.nan_to_num(cc), 0, 255)
  .astype(np.uint8)`.
- **`_02_ml_prep.py`: `EQA.dem_par` corner (`98cd3a8` #174)** — the grid corner
  `lon_w_g = lon_w_p + dlon/2` used the **unscaled** pixel and got scaled only
  `dlon` afterwards, so for `nlook>1` the corner was off by `(nlook−1)/2`
  original pixels (a `GEOCml{n*}` grid that didn't tile under it). The corner is
  now computed **after** `dlon/dlat` are scaled by `nlook`, at all four sites
  (ifg / sbovl / else / fallback). `EQA.dem_par` is only written when missing,
  so existing `GEOCml*` should be regenerated.
- **`_02_ml_prep.py`: radar frequency (`51f09b6` #173)** — precedence is now
  `--freq` > `radar_freq` in `GEOC/metadata.txt` > Sentinel-1 default, with a
  warning on `--freq`/metadata mismatch and an Hz-range sanity check; an
  existing `slc.mli.par` with a stale `radar_frequency` is updated when `--freq`
  is given. (For Sentinel-1 `5.405e9` the behaviour is unchanged; for L-band
  datasets the frequency is no longer silently wrong.)
- **`_03op_gacos.py`: GACOS resampled grid (`fcd0b6d` #178)** — `gdal.Warp(
  outputBounds=...)` was given the pixel **corners** instead of the **outer
  edges**, shrinking the output grid by one pixel (delays ±0.5 px off at the
  edges, and `no_gacos_ifg.txt` could drop the first image in one pass). Now
  expands by half a pixel. `licsbas-03op-ERA5`'s `gdal.Warp` call already
  passes outer edges and was left unchanged. A `sltd_grid.txt` grid record is
  written so that outputs made on a different grid (by a build with the shrunk
  grid, or before `EQA.dem_par` was fixed) are caught and the user is told to
  remove them, since existing outputs are not re-created — this matters because
  `03op` and `04` leave existing `unw`/`corr` files in place.
- **Audited `_02to05_unwrap.py`**: it needs **none** of the four fixes — it has no
  uint8 `cc` cast, writes no `slc.mli.par`/`EQA.dem_par` corner (those come from
  step 02, now fixed), does no `gdal.Warp` GACOS resampling, and its `--freq` is
  only ever set by the flag (no overwrite bug, unlike step 02). No changes made there.

> **LiCSBAS2 backport status:** the four concrete bug fixes above are now in v3.
> Deferred (features, not bug fixes, to be taken on their own merits): `--keep_ifg_list`,
> optional `04 vstd`/`vstd`/`vel`, 04 LP linear-fit, NISAR sign flip, `sweets2geoc`
> / `align_geoc`.

### 2026-11-12 (NISAR data access — new, optional)
- **Fix `licsar_extra` imports** (so NISAR modules actually load): removed the
  unused `from LiCSAR_misc import *` from `python/nisar_data.py` and made the
  `lics_proc_tools` import fall back to the `licsar_extra` package; added the
  NISAR-only deps (`asf_search, geopandas, shapely, pyproj, h5py, dask, rasterio,
  requests`) to `requirements.txt` and a `licsar_extra[nisar]` extra in `setup.py`.
- **New step `licsbas-01-get-nisar-data`** (`licsbas/steps/_01_get_nisar_data.py`):
  search ASF for NISAR GUNW/GSLC in a LiCSBAS bbox (`-g lon1/lon2/lat1/lat2`) and
  download the `.h5` into per-frame subfolders (via `get_frameid`). Uses the
  `asf_search` session for the download (streamed HTTP, optional ASF
  credentials) — **no shell `wget`**. Supports `--dry_run`; existing files are
  skipped. The classic LiCSAR step `licsbas-get-geotiff` is untouched. Covered by
  `tests/test_nisar_step.py` (stubbed, no network).
- **New tool `licsbas-asf2geoc`** (`licsbas/scripts/_asf2geoc.py`): ported from
  LiCSBAS2 — converts ASF/NIISAR pre-processed GeoTIFF product dirs into a LiCSBAS
  `GEOC/` layout. Only the `LiCSBAS_tools_lib` import was re-targeted to
  `licsbas.tools_lib` (graceful fallback preserved); now exposed as an entry point.
- **New tool `licsbas-nisar2geoc`** (`licsbas/scripts/_nisar2geoc.py`): the NISAR
  analog of `asf2geoc` but for raw NISAR GUNW `.h5`. Applies the
  `earthquake_responder.py` corrections (removes the smooth ionospheric +
  range-offset ramps, a 2-D quadratic ramp unless range-offsets were used, then a
  coherence mask). Uses the **rasterio (`rio`)** WGS-84 conversion of
  `licsar_data.py` (`rio.write_crs` → `rio.to_raster` → `gdalwarp -t_srs EPSG:4326`
  with `COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES`) — not the pure-GDAL warp of
  `asf2geoc`. **All** exported GeoTIFFs (unw/cc of every IFG + top-level E/N/U,
  hgt, mli) are written onto a **single shared WGS-84 grid** (first product defines
  it). Writes a LiCSBAS-standard `baselines` file (per-pair `bperp`, read by
  `io_lib.read_bperp_file`) plus `metadata.txt` (center_time, radar_freq) in the
  `asf2geoc` style. `-E <GSLC.h5>` for E/N/U + mli, `-D` for a DEM; `bin/LiCSBAS_nisar2geoc.py`
  wrapper. Covered by `tests/test_nisar2geoc.py` (stubbed, no HDF5).
- Docs: new `docs/05_nisar.md`; NISAR note + doc-table row in `README.md`.
- Entry points: 79 (added `licsbas-01-get-nisar-data`, `licsbas-asf2geoc`, `licsbas-nisar2geoc`).

### 2026-11-21 (test-suite health + matplotlib 3.10 fix)
- **`tools_lib.get_cmap`**: the legacy `plt.cm.register_cmap('cmocean.ice', ...)`
  rejects dotted names on matplotlib ≥ 3.5 (silently), so `plt.get_cmap()` then
  raised. Now registers via the modern `matplotlib.colormaps.register(..., force=True)`
  (with a legacy fallback) — cmocean / SCM / GMT / colorcet cmaps work again on
  modern matplotlib (fixes `test_colomaps_bundled`).
- **Test-isolation fix** (`tests/test_02to05_plots.py`): the `_deps` fixture
  injected fake `pandas`/`statsmodels`/... into `sys.modules` and never removed them,
  which poisoned xarray (`from pandas.errors import ...`) for every later test. It now
  stubs only genuinely-missing deps and cleans up on teardown.
- **Test-logic fix** (`tests/test_imports.py`): `test_entry_points_exist_and_resolve`
  now guards `returncode != 0` before expecting a “missing optional tool” message
  (so modules that import fine — `EP_OK` — pass even when `licsar_extra` is present).
- Fixed a duplicate-file bug in `lisar2geoc`/download dedup (iterating over the list
  it was just cleared) so product discovery actually works.
- **`tutorial/tutorial.ipynb` first cell**: made it a self-contained, idempotent
  setup cell that detects a missing **GDAL binary stack (`osgeo`, not on PyPI)** and
  installs it from conda-forge (Colab/Binder), then `pip install licsbas[viewer]`,
  and prompts a kernel restart if anything was installed. Previously it only
  `import licsbas` and raised a “please pip install” message, so it failed on
  Google Colab (the Binder equivalent was the `gdal`/`gdal-wheel` environment.yml fix).

### 2026-07-24 (steps/scripts split + entry points)
- **Package layout**: unnumbered utility scripts (cum2vel, disp_img, plot_ts, out2nc,
  profile, contour, ...) moved from `licsbas/steps/` to a new `licsbas/scripts/`
  sub-package; `licsbas/steps/` now holds only the numbered pipeline steps (01-17).
  `bin/` wrappers, `licsbas.batch`, `tests/`, `docs/` and `pyproject.toml` updated.
- **Entry points completed**: previously missing `licsbas-*` console commands added
  (`licsbas-cum2tif`, `licsbas-cum2flt`, `licsbas-cum-clip`, `licsbas-cum-interpolate`,
  `licsbas-cum-plate-motion`, `licsbas-decompose-los`, `licsbas-detect-coreg-error`,
  `licsbas-mask-flt`, `licsbas-profile`, `licsbas-remove-reffx-vstd`, `licsbas-reset-nulls`,
  `licsbas-resid-check`, `licsbas-vel-plate-motion`, `licsbas-check-install`,
  `licsbas-13-sb-inv`, `licsbas-130-remove-noloops`, `licsbas-remove-noloops`).
  Total console entry points: 76.

### 2026-07-24 (batch usability, docs, typo fixes)
- **Workflow templates**: `licsbas.batch` now ships named `BatchConfig` factories
  (`standard`, `reunw_5`, `reunw_10`, `reunw_20`, `sbovl`, `sbovl_abs`) via
  `make_config()` / `list_workflows()`, extensible with `@register_workflow()`;
  CLI: `licsbas-batch --workflow reunw_5 [--nlook ...]` and `--list-workflows`.
- **ERA5 step** (`licsbas/steps/_03op_era5.py`): the STD before/after panel of
  `ERA5_info2.png` no longer requires `seaborn` — new `plot_lib.plot_gacos_info2`
  (matplotlib-native hexbin correlation diagram, shared with the GACOS step).
- **02to05 GACOS correction plots** (`licsbas/steps/_02to05_unwrap.py`): with `--gacos`, the
  chain now also writes the standard LiCSBAS-style per-ifg correction plots
  (`pair.gacos.png` before/after/difference, same `make_3im_png` style as
  `LiCSBAS03op_GACOS.py`) plus `GACOS_info2.png` (STD before/after), built
  post-hoc from the exported `pair.unw` using the same `lics_unwrap` helpers —
  no change to licsar_extra needed. Covered by `tests/test_02to05_plots.py`.
- `tutorial/tutorial_batch.ipynb` restructured around the workflow templates
  (all chains, incl. `reunw_5`, generated via `make_config`, with PNG flowcharts
  and the template registry).
- README: new **Tutorials** section with Binder (logo-badge) + Google Colab
  links for every tutorial notebook; **Documentation** section presents the
  `docs/` pages as a table; `licbas-*` → `licsbas-*` typo fixed in
  `docs/*.md` and `TODONEXT.md`.
- `tests`: entry-point smoke test now reads the repo `pyproject.toml` (single
  source of truth, robust to stale dev installs); tide/iono tests now verify the
  standard `LiCSBAS131_corrections.py` step receives `--tide`/`--iono`.

### Python batch processor (replaces batch_LiCSBAS.sh)
- New `licsbas/batch.py` (CLI: `licsbas-batch`): all settings/flags of
  `batch_LiCSBAS.sh` (standard chain, 02to05 re-unwrapping, sbovl/sbovl_abs,
  optional steps 03-06, eqoffsets, tide/iono/gacos corrections, 120 re-run
  after nullification, ...) are now a python `BatchConfig`;
  steps are executed **in-process** through `licsbas.steps.*` (v3 layout).
- New `licsbas/flowchart.py`: renders any processing chain to a PNG via the
  Graphviz `dot` binary (no new python dependency).
- `batch_LiCSBAS.sh` is now a thin wrapper around `python -m licsbas.batch`.
- New `examples/`: `example_1_standard.py`, `example_2_reunw_02to05.py`,
  `example_3_sbovl.py` — three ready-to-adapt chains, each also writing a
  PNG flowchart of the performed steps.

### Naming fix & tutorial
- The `licbas-*` console aliases (a "licbas" typo in the v3 name set) are now
  unified under `licsbas-*` (e.g. `licsbas-unwrap`, `licsbas-get-geotiff`);
  duplicate aliases dropped → 59 entry points, all `licsbas.*`; smoke test and
  skills/TODO docs updated accordingly.
- New `tutorial/tutorial_batch.ipynb`: walkthrough of **both** batch workflows —
  the python batch (`licsbas.batch.BatchConfig` / `run_batch` / `save_flowchart`)
  and the shell batch (`./batch_LiCSBAS.sh` / `licsbas-batch`), incl. the three
  example chains and PNG flowcharts.
## [3.0.0] — 2026-11-26 (branch `towards-v3`)

**First stable v3 release**: `pip install licsbas` (or from this repo) now works
end-to-end on Python 3.10–3.13. Changes on top of 3.0.0rc1:

### Packaging finalisation
- `LiCSBAS_lib/` shim layer **removed**: legacy *imports* (`import LiCSBAS_meta`)
  are no longer emulated — use `licsbas.meta` etc. Legacy *commands* keep working:
  `bin/` wrappers + `licsbas-*` console entry points (incl. short aliases like
  `licsbas-unwrap`, `licsbas-filt-ts`) + `python -m licsbas.steps.*`.
  `bashrc_LiCSBAS.sh` / `start` now only put `bin/` on `PATH`.
- Dependency audit (AST-based) finalised the hard-dependency list:
  added `beautifulsoup4`, `psutil`, `cmcrameri`, `python-dateutil`, `utm`;
  removed unused pins (`opendata`, `python-snappy`, `tqdm`, `numexpr`…);
  `gdal-wheel` is pulled in automatically on x86_64/aarch64.
- Everything optional now lives in extras: `.[unwrap]` (licsar_extra @ v1.6),
  `.[plot]` (networkx, seaborn), `.[ml]` (scikit-learn), `.[viewer]`
  (pygmt, ipympl, contextily, Pillow), `.[all]`.
  `usgs-libcomcat` (eqoffsets step) is deliberately *not* an extra — its
  dependency chain pulls in `openquake` and a source GDAL build.
  Steps import these lazily and print install guidance when actually needed.
- License declared in PEP 639 form (`license = "GPL-3.0-or-later"`, no more
  build warning); classifiers cleaned.
- Entry points cleaned: 14 broken/stale entries removed (plot-tile, plot-velocity*,
  plot-network-multipolygon, extras, extras-light, meta-as-step), ALOS case fixed.

### Robustness
- Optional imports guarded everywhere: `pygmt` (viewer-only), `sklearn`
  (`131_boi_absolute`, `131_bovl2abs`), `licsar_extra` (`02to05`, `17`),
  `contextily`, `libcomcat` (`get_eqoffsets`); SNAPHU presence is checked at
  run-time in `02to05` only (clear message, no module-level abort).
- `licsbas.extras` (pygmt viewer) raises a helpful ImportError with install
  instructions when viewer extras / system GMT are missing.
- Bugfixes found during finalization: `130_remove_noloops` had two broken
  `.format()` calls (one crashed at runtime with a `TypeError`); four
  `colormaps/*/__init__.py` declared `__all__` as a `set` (now `list`).
- `mypy` baseline: `[tool.mypy]` config + CI job; `mypy licsbas/` passes
  on all 68 source files.

### Testing & CI
- New `tests/test_smoke.py` (29 tests): package imports, all step modules import
  without optional deps, all declared entry points resolve to a callable `main()`.
- New `.github/workflows/ci.yml`: smoke job (py3.10–3.13 matrix) + viewer job
  (installs system `gmt`, verifies pygmt extras).

### Tutorial & Binder
- Two notebooks in `tutorial/`: `tutorial.ipynb` (pygmt viewer via
  `licsbas.extras`) and `tutorial_bash-compatible.ipynb`
  (`licsbas-*` CLI + pygmt-free `pylight_plot_interactive`), plus an
  alternative viewer cell in both; `%matplotlib widget` (ipympl) for
  interactive plots.
- Binder: `postBuild` unchanged (downloads tutorial data);
  `apt.txt` now includes `gmt`; `install_complete.sh` rewritten for v3.
- README updated (install, extras table, new binder/colab links).

## [3.0.0rc1] — 2026-11-16 (branch `towards-v3`)

First **v3 release candidate**: LiCSBAS is now a proper, pip-installable Python package.

### Packaging (big news)
- New `licsbas` package: `licsbas.{meta, tools_lib, io_lib, loop_lib, inv_lib,
  plot_lib, extras, extras_light}`, `licsbas.steps` (all 53 steps),
  `licsbas.colormaps` (bundled cmocean / GMT / SCM / colorcet fallback data +
  `extract_cmaps_*.sh`).
- `pip install .` installs the package **and** the whole backwards-compatibility
  layer, so the traditional workflow keeps working:
  - legacy top-level imports: `import LiCSBAS_meta`, `LiCSBAS_tools_lib`,
    `LiCSBAS_extras_light`, ... now resolve to the real `licsbas.*` modules
    (61 shims under `LiCSBAS_lib/_shims/`);
  - 53 console entry points: `licsbas-01-get-geotiff` … `licsbas-14-vel-std`,
    `licsbas-check-install`, `licsbas-plot-ts`, ...;
  - legacy `LiCSBAS*.py` commands stay available as thin `bin/` wrappers, and
    `bashrc_LiCSBAS.sh` + `batch_LiCSBAS.sh` continue to work unchanged.
- Single source of truth for dependencies: `pyproject.toml`
  (required: astropy, beautifulsoup4, h5py, matplotlib, networkx, numpy,
  pandas, Pillow, psutil, requests, rioxarray, scikit-learn, seaborn, scipy,
  shapely, statsmodels, utm, xarray, cmcrameri, ipympl, pygmt).
  Conda-only / system packages (gdal, snaphu, contextily, ...) are **not**
  pip dependencies.
- Optional extras: `pip install .[unwrap]` (licsar_extra: GPU unwrapping in
  `02to05`, corrections in `131_corrections`, absolute azimuth-offset steps),
  `.[comcat]` (usgs-libcomcat, `LiCSBAS_get_eqoffsets` only), `.[all]`.

### Robustness / maintenance
- `LiCSBAS131_bovl2abs` (and its WIP companion `_131_boi_absolute`): guarded
  the optional `daz_lib_licsar` import; fixed a pre-existing syntax error.
- `_17_plot_corrections`, `_02to05_unwrap`, `_131_corrections`, `_131_bo*`:
  optional `licsar_extra` imports are now guarded with clear install guidance.
- All 9 interactive steps got a proper `def main()` (console-script friendly);
  removed a buggy double-`__main__` guard that broke entry-point invocations.
- `tools_lib.plot_vel_tif`: fixed invalid regex escapes (`invalid escape
  sequence '\d'` warnings) and added a `cum_abs` fallback lookup.
- Matplotlib now uses `Agg` unless interactive drawing is requested
  (fixes `libpng error: Invalid WIL2 chunk` / missing-display errors in
  headless batch runs).
- Versioning: `licsbas.__version__` (3.0.0rc1) is the single source
  (`LiCSBAS_meta.ver` stays in sync); scripts report `ver{version}` in `--help`.
- Repository hygiene: `.gitignore` cleaned, `.idea/` untracked,
  `LiCSBAS_lib/` now contains only the compatibility shims.

### Compatibility
- Everything from 1.x continues to work: old import names, `bin/*.py` scripts,
  `batch_LiCSBAS.sh`, `bashrc_LiCSBAS.sh`, matplotlib `cm_*` color maps.
- Shims are transitional and will be removed in a future major release
  (importing them is safe for now; no DeprecationWarning spam added on purpose).

### Known limitations
- GDAL must come from conda/OS (not pip-installable); documented in README.
- `LiCSBAS_get_eqoffsets` still hard-exits without `usgs-libcomcat` by design.
- A few optional dependencies (e.g. `sklearn` for RANSAC paths) are detected at
  import time per step; install the extras if you use those steps.

History of 1.x releases: see git history and the `dev` branch tags
(v1.15 → 2024/11).
