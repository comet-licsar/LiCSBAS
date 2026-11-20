# Changelog — LiCSBAS

## [unreleased] — branch `towards-v3`

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
