# PLAN — brief implementation plan for TODONEXT.md

General, phased plan. Each phase is independently shippable; order respects
dependencies (packaging first, because later phases assume a real package).

## Phase 0 — packaging baseline (done in this commit)
- `pyproject.toml` installs the `LiCSBAS_lib` modules in the existing flat
  top-level convention (keeps `import LiCSBAS_meta`-style scripts and notebooks working).
- `licsar_extra` exposed as the optional extra `[unwrap]`, `usgs-libcomcat` as `[comcat]`.
- README documents `pip install .`, extras, and the GDAL-via-conda caveat.

## Phase 1 — rename to a real package
1. Create `licsbas/` with submodules mirroring `LiCSBAS_lib/*.py`; update imports inside
   (intra-package) and in `bin/` scripts (`from licsbas import tools_lib as tools_lib ...`).
2. Add `licsbas/__init__.py` with `__version__` (single source); make `LiCSBAS_meta.ver`
   read from it.
3. Keep old top-level names as auto-generated shims for ≥2 releases, then remove.
4. Update `pyproject.toml` (`tool.setuptools.packages.find where=["."]`) and README.

## Phase 2 — steps as entry points
1. Move `bin/*.py` to `licsbas/steps/*.py` (strip `.py` from names).
2. Generate `[project.scripts]` entries from the existing `main()` functions.
3. Switch `batch_LiCSBAS.sh` invocations to the new command names (feature-flag by version).
4. Deprecate `bashrc_LiCSBAS.sh`; update wiki/notebooks links.

## Phase 3 — dependencies cleanup
1. Delete `LiCSBAS_requirements*.txt`, `environment.yml`; keep `apt.txt` only as GDAL/OS hint.
2. Consolidate onto `pyproject.toml` extras; add minimum versions where APIs are used
   (e.g. `numpy>=1.26`, `xarray>=2024.01`); drop `lapack`, `bottleneck`.

## Phase 4 — CI + tests + publication
1. `tests/`: import-all-modules smoke test + tiny IO/plot round-trip.
2. GitHub Actions: matrix of supported Pythons, `pip wheel .`, `twine check`, run smoke tests.
3. Enable PyPI trusted publishing for release tags; move changelog into `CHANGELOG.md`.
4. Publish `licsar_extra` on PyPI (or vendor the needed modules) and pin the `[unwrap]` extra.

## Acceptance criteria (end state)
- `pip install licsbas[unwrap]` reproduces a working environment on Linux/macOS/Windows.
- Full pipeline (01→16) runs using only installed entry points, no `PATH`/`PYTHONPATH` setup.
- `import licsbas; licsbas.__version__` matches the wheel version.
- CI is green for every release tag from at least 3 consecutive releases.
