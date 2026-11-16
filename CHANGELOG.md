# Changelog — LiCSBAS

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
