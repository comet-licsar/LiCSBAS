# TODONEXT — LiCSBAS v3 follow-ups

Done in the v3 series (see CHANGELOG.md / PLAN.md / STATUS.md): proper
pip-packaged `licsbas` package, 59 console entry points (all `licsbas-*` naming), `main()` wrapping, single-source versioning, cleaned
repo/ignore files, CI + 29 smoke tests, PEP 639 license, optional extras
(`unwrap`/`plot`/`ml`/`viewer`; `usgs-libcomcat` deliberately not an extra —
openquake/GDAL-source dep chain), lazy SNAPHU check, two tutorial
notebooks, README/CHANGELOG updates, `.agents/skills/licsbas/SKILL.md`.

## Next release (3.0.0 final)
- [x] CI on the new layout (`.github/workflows/ci.yml`: smoke matrix py3.10–3.13 + viewer job with system `gmt`).
- [x] PyPI name decided: **`licsbas`** (lowercase, as on PyPI).
- [x] Tag `v3.0.0`; tutorial notebooks + Binder/Colab links updated to the v3 layout
      (`tutorial/tutorial.ipynb`, `tutorial/tutorial_bash-compatible.ipynb`, `licsbas.*` imports).
- [x] `licsar_extra` pinned to the `v1.6` tag in the `unwrap` extra.
- [x] `LiCSBAS_lib/` shim layer **removed** (user decision, earlier than 4.0);
      legacy *imports* no longer emulated — `bin/` wrappers + entry points keep
      the traditional CLI workflow.
- [ ] Publish `licsbas` 3.0.0 to PyPI (needs a token; local wheel/sdist build verified).
- [ ] Create the GitHub `v3.0.0` release (needs a token).

## NISAR data access (new, optional) — added 2026-11
- [x] `licsbas-01-get-nisar-data` (ASF bbox search + GUNW/GSLC `.h5` download, per-frame subfolders).
- [x] `licsbas-nisar2geoc` (NISAR GUNW `.h5` → `GEOC/`: iono + range-offset corrections,
      rasterio WGS-84 export on a single shared grid, `baselines` + `metadata.txt`,
      E/N/U + hgt + mli top-level files). Recommended NISAR route.
- [x] `licsbas-asf2geoc` (ASF/NIISAR pre-processed GeoTIFF → `GEOC/`).
- [x] `docs/05_nisar.md` + README NISAR section / doc-table row.
- [x] `bin/LiCSBAS01_get_NISAR_data.py`, `bin/LiCSBAS_nisar2geoc.py`, `bin/LiCSBAS_asf2geoc.py`.
- [x] Tests: `tests/test_nisar_step.py`, `tests/test_nisar2geoc.py` (stubbed, no network/HDF5).
- [ ] `licsar_extra`: publish the NISAR extras (`asf_search`, `geopandas`, `shapely`, `pyproj`)
      + `nisar_data.py` / `lics_proc_tools.py` (pushed separately in that repo).
- [ ] End-to-end NISAR run on real GUNW `.h5` (CI tests are stubbed / no network yet).

### Deferred: LiCSBAS2 bug-fix backports (standard step-02/03 route **only**)
> These 4 (PLANS_NISAR.md Task 2) fix `_02_ml_prep` (step 02) and `_03op_gacos` (step 03) —
> the **standard** pipeline route, *not* the `02to05` substitution route (which replaces
> steps 02–05 and does not need them). Deferred until the NISAR work above is verified.
> Each will add an inline comment citing the LiCSBAS2 commit/PR + a CHANGELOG line.
- [ ] `2627e50` — `_02_ml_prep` `cc.astype(np.uint8)` on NaN → `np.clip(np.nan_to_num(cc),0,255).astype(np.uint8)` (1 line; avoids undefined cast).
- [ ] `98cd3a8` (#174) — `_02_ml_prep` EQA.dem_par corner shifted ½ *original* pixel then spacing scaled → off by (n−1)/2 px for `-n>1` (4 sites).
- [ ] `fcd0b6d` (#178) — `_03op_gacos` `gdal.Warp(outputBounds=centers)` off 0.5 px → pass outer edges (center ± ½ px); record grid in `sltd/sltd_grid.txt`.
- [ ] `51f09b6` (#173) — `_02_ml_prep` radar_freq precedence `--freq` > `metadata.txt` > default (v3 ignores `metadata.txt`).

## v3.1+
- [ ] **Do NOT remove `bin/` wrappers or `bashrc_LiCSBAS.sh`** — user requirement,
      they keep the traditional PATH-based workflow (already decided, kept in 3.0.0).
- [x] ~~Migrate steps off top-level globals in `main()`~~ — audited: only
      `_13_sb_inv.py` uses `globals()`, intentionally (loop-var cleanup); no action needed.
- [x] ~~`batch_LiCSBAS.sh`: fix unquoted `[ ... ]` tests~~ — done in v3.0.0 final
      (122 tests quoted, `bash -n` clean).
- [x] ~~`LiCSBAS_get_eqoffsets`: soften `usgs-libcomcat` missing-dep handling~~ —
      import no longer exits at module level; `main()` errors with install guidance;
      `licsbas-get-eqoffsets` entry point added.
- [ ] Consider per-step `pyproject` metadata (per-step help, `--version`).
- [x] ~~Type hints / `mypy` clean baseline~~ — done in v3.0.0 final:
      `[tool.mypy]` config in `pyproject.toml` + `mypy` CI job; `mypy licsbas/`
      passes on all 68 source files. `--strict` remains a stretch goal:
      annotate `tools_lib` + `io_lib` first, then widen.
- [x] ~~Docs: wiki pages still reference the old flat layout~~ — done in v3.0.0 final:
      main wiki pages ported to local `docs/` (01_installation, 02_workflow,
      03_visualization, 04_other_tools, file_structure, links) with
      old-name → `licsbas-*` mappings; README documentation section links to them.
- [ ] PyPI: publish `licsbas` (and consider a PyPI release of `licsar_extra`).

## Housekeeping
- [ ] Archive `LiCSBAS_requirements*.txt` / `environment_optional.yml` with a
      deprecation notice (kept only to mirror v1/v2 setups); keep `environment.yml`
      (still the recommended conda route).
