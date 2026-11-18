---
name: licsbas
description: Work with the LiCSBAS InSAR time-series package (v3, pip package `licsbas`). Use when installing, running, debugging, or extending LiCSBAS steps, writing batch scripts, or building the tutorial/notebooks.
---

# LiCSBAS v3 — agent guide

## Repo layout
- `licsbas/` — the Python package (flat, no subpackages except `steps/` and `colormaps/`):
  - `licsbas/{meta,tools_lib,io_lib,loop_lib,inv_lib,plot_lib,extras,extras_light}.py`
  - `licsbas/steps/_NN_*.py` — 53 step modules, each with `def main()` and a
    `if __name__ == "__main__"` guard (runnable via `python -m licsbas.steps.<stem>`).
  - `licsbas/colormaps/` — bundled Scientific Colour Maps data.
- `bin/` — thin legacy wrappers (`LiCSBAS14_vel_std.py` …); import the step module
  and call `main()`. **Preserve** `bin/` and `bashrc_LiCSBAS.sh` (they only put
  `bin/` on `PATH`).
- `tests/test_smoke.py` — 29 smoke tests (imports, entry points, step `main()`).
- `tutorial/` — `tutorial.ipynb` (pygmt viewer), `tutorial_bash-compatible.ipynb`
  (pygmt-free `pylight_plot_interactive`), `install_complete.sh`, `postBuild` (Binder).

## Hard rules (v3.0.0)
1. **Optional deps are optional.** `licsar_extra`, `pygmt`, `ipympl`, `contextily`,
   `Pillow`, `networkx`, `seaborn`, `scikit-learn`, `usgs-libcomcat` are extras
   (`unwrap`, `viewer`, `plot`, `ml`) or manual installs (libcomcat: its
   openquake/gdal source-build chain makes it unsuitable as an extra). Any
   module-level import of them must be inside `try/except` or inside a function,
   with a helpful error (`pip install 'licsbas[<extra>]'`) raised only at runtime use.
2. **No module-level `sys.exit()`** in step files (breaks `importlib` discovery).
3. **SNAPHU** is a system binary, checked lazily in `_02to05_unwrap` only.
4. **GDAL** (`osgeo`) is a hard dependency (13+ files) — `gdal-wheel` is a pip dep
   on x86_64/aarch64; elsewhere it must come from the system/conda.
5. Entry points live only in `pyproject.toml` `[project.scripts]`, all named
   `licsbas-*`. Every target must be an
   existing `licsbas.steps.<stem>` with a callable `main()`.
6. License is PEP 639: `license = "GPL-3.0-or-later"` (no `License ::` classifier).

## Install / test commands (clean venv)
```bash
python -m venv /tmp/v3test && /tmp/v3test/bin/pip install -U pip
/tmp/v3test/bin/pip install "/path/to/LiCSBAS[all]"   # extras need bracket syntax with path
/tmp/v3test/bin/pip install "licsbas[unwrap] @ file:///path/to/LiCSBAS"  # alternative form
/tmp/v3test/bin/python -m pytest tests/ -q            # must pass without optional extras too
/tmp/v3test/bin/python -m build                       # sdist+wheel, no PEP 639 warnings
```
- `pygmt` import needs the **system** GMT library (`sudo apt-get install gmt`);
  without it, `import licsbas.extras` must raise the helpful ImportError.

## Conventions
- Steps: argparse in `main()`, results printed as usual; keep `main()` importable.
- Error style for missing optional deps:
  `raise RuntimeError(f"Step X needs package Y — install with: pip install 'licsbas[extra]'")`
- Keep `STATUS.md` updated when working in long sessions (it is the compaction-safe
  progress log for this repo).
- Release: tag `v3.x.y`, GitHub release, then `pip` users get it via
  `pip install git+https://github.com/comet-licsar/LiCSBAS.git@v3.x.y`.
