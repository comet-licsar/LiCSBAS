---
name: licsbas
description: Work with the LiCSBAS InSAR time-series package (v3, pip package `licsbas`). Use when installing, running, debugging, or extending LiCSBAS steps, writing batch scripts/workflows, adding NISAR data access, or building/editing the tutorial notebooks & flowcharts.
---

# LiCSBAS v3 — agent guide

Branch: `towards-v3` (v3 is NOT on `main` yet — raw.githubusercontent / Colab /
README badge links must use the `towards-v3` branch until the v3 release).

## Repo layout
- `licsbas/` — the Python package:
  - `licsbas/{meta,tools_lib,io_lib,loop_lib,inv_lib,plot_lib,extras,extras_light}.py`
  - `licsbas/steps/_NN_*.py` — ~56 step modules, each `def main()` +
    `if __name__ == "__main__"` guard (runnable via `python -m licsbas.steps.<stem>`)
    + the NISAR access step `licsbas/steps/_01_get_nisar_data.py`.
  - `licsbas/scripts/` — heavy *script* steps (not per-IFG steps):
    `_asf2geoc.py` (ASF GeoTIFF → `GEOC/`), `_nisar2geoc.py` (NISAR GUNW `.h5` →
    `GEOC/`: iono + range-offset removal, coherence mask, rasterio/rioxarray
    WGS-84 export on **one shared grid**, `baselines` + `metadata.txt`).
  - `licsbas/batch.py` — python batch engine: `BatchConfig` (dataclass),
    `build_pipeline()`, `run_batch(cfg, dry_run)`, `save_flowchart(cfg, png,
    rankdir=...)`, workflow registry `@register_workflow(name, desc)` with
    workflows **`standard`, `reunw_5`, `sbovl`, `sbovl_abs`, `nisar`** —
    `licsbas-batch --list-workflows`, `--workflow <name>`, `--check-only`,
    `--flowchart x.png` (portrait PNG by default).
  - `licsbas/flowchart.py` — Graphviz `dot` (subprocess; **no python
    `graphviz` dep**): `FlowStep(name,details,active,phase,note,alt)`,
    `render_flowchart(steps, out_png, title=..., rankdir=...)`. `rankdir` is
    `"TB"` (default) or `"LR"` (landscape). `alt=True` → amber node + dashed
    edge from the first node of the previous phase + "(alternative route)" tag.
    In-phase steps cluster into subgraphs; inactive steps render grey with
    "(optional - switched off)".
  - `licsbas/colormaps/` — bundled Scientific Colour Maps.
- `bin/` — thin legacy wrappers (`LiCSBAS*.py`, also `LiCSBAS_asf2geoc.py`,
  `LiCSBAS_nisar2geoc.py`, `LiCSBAS01_get_NISAR_data.py`); import the module and
  call `main()`. **Preserve** `bin/` and `bashrc_LiCSBAS.sh` (user requirement).
- `examples/` — dry-run batch templates that also write a PNG flowchart:
  `example_1_standard.py`, `example_2_reunw_02to05.py`, `example_3_sbovl.py`,
  `example_4_nisar.py` (`--bbox`, `--frames 018A_01234`, `--execute`, …).
- `batch_LiCSBAS.sh` — **original shell batch script (restored from `main`)**;
  the python batch engine is `licsbas-batch` / `examples/*.py`. Both coexist.
- `docs/` — wiki pages ported to local markdown, v3 naming:
  `01_installation.md` (incl. v1→v3), `02_workflow.md`, `03_visualization.md`,
  `04_other_tools.md`, `05_nisar.md` (NISAR access), `file_structure.md`,
  `links.md`. README is the *short* front page: it links to docs/ + tutorials.
- `tutorial/` — see "Tutorials & flowcharts" below.
- `tests/` — pytest; `test_smoke.py` (entry points etc.), `test_batch.py`,
  `test_02to05_plots.py`, `test_nisar_step.py`, `test_nisar2geoc.py`
  (stubbed, no network/HDF5), `test_imports.py`. Env to test in:
  `~/micromamba/envs/insar/bin/python` (py3.12). **Run:
  `~/micromamba/envs/insar/bin/python -m pytest tests/ -q`** (87 passed, 2 skipped
  after the 2026-12-19 backports).

## Hard rules (v3.0.0)
1. **Optional deps are optional.** `licsar_extra` (`unwrap`/`nisar` extras),
   `pygmt`, `ipympl`, `contextily`, `Pillow`, `networkx`, `seaborn`,
   `scikit-learn`, `usgs-libcomcat`, and the NISAR stack
   (`asf_search`, `h5py`, `rasterio`, `rioxarray`, `xarray`, `dask`, `pyproj`,
   `statsmodels`) are extras (`unwrap`, `nisar`, `viewer`, `plot`, `ml`) or
   manual installs (libcomcat). Any module-level import of them must be inside
   `try/except` or inside a function, with a helpful error
   (`pip install 'licsbas[<extra>]'`) raised only at runtime use. NISAR modules
   are imported lazily (`_get_nds()` in `_01_get_nisar_data`, `_nd` in
   `_nisar2geoc`) so `-h` works without the extras.
2. **No module-level `sys.exit()`** in step files (breaks `importlib` discovery).
3. **SNAPHU** is a system binary, checked lazily in `_02to05_unwrap` only.
4. **GDAL** (`osgeo`) is a hard dependency — `gdal-wheel` is a pip dep on
   x86_64/aarch64; otherwise from the system/conda.
5. Entry points live only in `pyproject.toml` `[project.scripts]`, all named
   `licsbas-*` (the `licbas-*` spelling was a typo — never reintroduce it).
   Every target must be an existing module with a callable `main()`.
   New NISAR/ASF entry points: `licsbas-01-get-nisar-data`, `licsbas-nisar2geoc`,
   `licsbas-asf2geoc`.
6. License is PEP 639: `license = "GPL-3.0-or-later"` (no `License ::` classifier).
7. `bin/` wrappers are **supported legacy CLI** (user requirement — never remove). The
  `"DEPRECATED"` banner has been removed from all 55 `bin/*.py` (docstring now
  says `"Legacy wrapper for the console entry point \u0060\u0060…\u0060\u0060"`); do not re-add it.
8. GeoTIFF writing uses `TIFF_OPTIONS = ["COMPRESS=DEFLATE","PREDICTOR=2",
   "TILED=YES"]` (see `io_lib`); float32 unw, uint8 cc (clip NaN → 0..255).

## LiCSBAS2 backports (done 2026-12-19 — do not regress)
Applied to the **standard** step-02/03 route, each cited inline in the code
(see CHANGELOG 2026-12-19): `_02_ml_prep` uint8-cc NaN cast
(`2627e50`), `EQA.dem_par` corner computed *after* dlon/dlat nlook scaling
(`98cd3a8`, 4 sites), radar_freq precedence `--freq` > `metadata.txt` > default
+ Hz sanity + stale-par update (`51f09b6`); `_03op_gacos` `gdal.Warp`
`outputBounds` = outer edges (±½px) + `sltd_grid.txt` grid check & mismatch
detection (`fcd0b6d`). **The 02to05 route was audited and needs none of them.**
`EQA.dem_par` is only written when missing ⇒ stale `GEOCml*` outputs should be
regenerated after an upgrade.

## NISAR data access (optional, experimental)
- `licsbas-01-get-nisar-data`: ASF bbox search + streamed download of NISAR
  CSL2 **GUNW `.h5`** (LiCSBAS uses GUNW only — **GSLC is not used at all**)
  into per-frame subfolders. **`--frame FID[,FID2,...]`** restricts to selected
  frames; **`--list-frames`** lists the available frames + GUNW count per frame
  and exits (no download). Frame id = `<line><pass>_<beam>` (e.g. `018A_01234`),
  from `nisar_data.get_frameid`. Uses `licsar_extra.nisar_data` (lazy). No shell
  `wget`.
- `licsbas-nisar2geoc`: **one frame per GEOC** (frames/tracks cannot be
  combined; it warns if the input GUNWs span >1 frame). Removes smooth
  ionospheric ramp and the range-offset ramp *before* export (per
  `earthquake_responder.py`), applies coherence mask, writes `unw/cc` per IFG,
  **`X.geo.E/N/U.tif` once, from the first GUNW's own `radarGrid` metadata**,
  `+ hgt` with `-D`, one shared WGS-84 grid (first IFG defines it; later ones
  re-registered), standard **`baselines`** (4-col) and `metadata.txt`.
  `-i <frame_folder>`, `-t cc_thre`, `-f A|B`, `--no_iono/--no_offsets/
  --no_deramp_quad`, `-D`, `--dry_run`.
- `licsbas-asf2geoc`: ASF pre-exported GeoTIFF (unw/cc/E/N/U/hgt/mli) → `GEOC/`
  (the alternate entry to the same layout).
- Docs: `docs/05_nisar.md`; tutorial: `tutorial/tutorial_0_nisar.ipynb`;
  batch: `nisar` workflow + `examples/example_4_nisar.py`.
- `licsar_extra` (separate repo, `comet-licsar/licsar_extra`, `main` branch —
  keep it in sync with the NISAR extras) provides `nisar_data` + helpers.

## Conventions
- Steps: argparse in `main()`, keep `main()` importable; batch engine calls
  steps in-process via `importlib` (`build_pipeline` → list of
  `(module, argv)`), or run `licsbas-<name>` on `PATH`.
- Error style for missing optional deps:
  `raise RuntimeError(f"Step X needs package Y — install with: pip install 'licsbas[extra]'")`
- Keep `STATUS.md` / `TODONEXT.md` / `CHANGELOG.md` updated in long sessions
  (they are the compaction-safe progress log for this repo).
- Release: tag `v3.x.y`, GitHub release, then `pip` users get it via
  `pip install git+https://github.com/comet-licsar/LiCSBAS.git@v3.x.y`.
  **When v3 lands on `main`**, switch all `towards-v3` branch refs in
  README.md + `tutorial/build_notebooks.py` (`BRANCH=`) back to `main`/`HEAD`.

## Tutorials & flowcharts (restructured 2026-12-19)
- `tutorial/tutorial.ipynb` = **master single-file template** (marked as such in
  its title cell). The published tutorials are **composed from it** by
  `python3 tutorial/build_notebooks.py` →
  - `tutorial_0.ipynb` (LiCSAR step-0\*, **incl. the `02to05` alternative-route
    cell** after step 0-2),
  - `tutorial_0_nisar.ipynb`, `tutorial_0_sbovl.ipynb`, `tutorial_1.ipynb`
    (time series 11→16 + viewers).
  All cross-linked (relative links open in the same Binder session) with fresh
  Binder + Colab badges; each is nbformat 4.5 valid.
- **Flowcharts** (`licsbas/flowchart.py` + `tutorial/make_flowchart.py`):
  **portrait (TB)** PNGs from JSON configs in `tutorial/tutorial_cfg/*.json`,
  shown just before the first script. `rankdir` TB (default) / LR (opt-in in a
  config); `alt` styling for the 02to05 route. Regenerate:
  `python3 tutorial/make_flowchart.py [name]`. The four PNGs live in
  `tutorial/` (they are `git add -f`-ed; `*.png` is git-ignored).

## Install / test commands
```bash
# clean venv check
python -m venv /tmp/v3test && /tmp/v3test/bin/pip install -U pip
/tmp/v3test/bin/pip install "/path/to/LiCSBAS[all]"
/tmp/v3test/bin/python -m pytest tests/ -q          # must pass w/o optional extras too
/tmp/v3test/bin/python -m build                     # sdist+wheel, no PEP 639 warnings
# in-repo dev env (recommended)
~/micromamba/envs/insar/bin/python -m pytest tests/ -q
~/micromamba/envs/insar/bin/python tutorial/build_notebooks.py
~/micromamba/envs/insar/bin/python tutorial/make_flowchart.py
~/micromamba/envs/insar/bin/licsbas-batch --list-workflows
```
