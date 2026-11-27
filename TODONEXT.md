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

## Since v3.0.0
- [x] **Phase bias correction** (optional 02op step, added 2026-12): new
      `LiCSBAS02op_phasebias` operator (`licsbas-02op-phasebias` entry point,
      `bin/LiCSBAS02op_phasebias.py`) wrapping the companion `phasebias`
      package (comet-licsar/InSAR_PhaseBias_Correction, tag v1.1.0,
      pip-installable). Python batch: `do02op_phasebias=True` /
      `licsbas-batch --phasebias` (auto-redirects step 02 to the corrected
      stack `$p02op_phasebias_out/GEOC`).
      Companion repo work: `updated_previous` merged into `main` (old main
      preserved as `archive/chunk-based-main`), restructured into the
      `phasebias` package with `phasebias-01..05` entry points, plus fixes
      (numpy≥1.25 warning, os.walk ordering/None-crash in step 03, non-blocking
      plots, HGT-less georeferencing fallback in step 05). Validated
      end-to-end on the 082D_05125_020000 dataset (2017–2021, 12407 ifgs →
      1190 corrected ifgs).
- [ ] `phasebias`: publish to PyPI as `insar-phasebias` (package + tag ready;
      needs a PyPI account/token) — then the LiCSBAS operator's install hint
      becomes `pip install insar-phasebias`.

## NISAR data access (new, optional) — added 2026-11
- [x] `licsbas-01-get-geotiff-nisar` (ASF bbox search + **GUNW** `.h5` download — **GUNW-only: GSLC was removed 2026-12-20** — per-frame subfolders;
      **`--list-frames` / `--frame FID[,FID2,...]`** for frame selection).
- [x] `licsbas-nisar2geoc` (NISAR GUNW `.h5` → `GEOC/`: iono + range-offset corrections,
      rasterio WGS-84 export on a single shared grid, `baselines` + `metadata.txt`,
      **E/N/U written once from the first GUNW**; **one frame per `GEOC`** — warns on
      mixed frames). Recommended NISAR route. **mli amplitude: removed (needs GSLC,
      which we do not use).**
- [x] `licsbas-asf2geoc` (ASF/NIISAR pre-processed GeoTIFF → `GEOC/`).
- [x] `docs/05_nisar.md` + README NISAR section / doc-table row.
- [x] `bin/LiCSBAS01_get_geotiff_NISAR.py`, `bin/LiCSBAS_nisar2geoc.py`, `bin/LiCSBAS_asf2geoc.py`.
- [x] Tests: `tests/test_nisar_step.py`, `tests/test_nisar2geoc.py` (stubbed, no network/HDF5).
- [ ] `licsar_extra`: publish the NISAR extras (`asf_search`, `geopandas`, `shapely`, `pyproj`)
      + `nisar_data.py` / `lics_proc_tools.py` (pushed separately in that repo).
- [ ] End-to-end NISAR run on real GUNW `.h5` (CI tests are stubbed / no network yet).

## NISAR follow-up (2026-12-20)
- [x] NISAR step renamed to `01_get_geotiff_nisar` convention; “Output files”
      data structure shown in `-h`; `--max` size filter; real `lisar_extra`
      API (top-level `nisar_data`/`lics_proc_tools`, ASF session streaming).
- [x] `02op_phasebias`: start/end dates in the generated config are now
      **derived from the pair list in `-i`** (first date of the first pair,
      last date of the last pair); `--start/--end` still override.
- [x] `nisar2geoc` now writes `slc.mli.par` (`radar_frequency` [Hz] +
      `center_time` when available) — needed by 03 GACOS / 130 / 132.
- [x] GUNW-only + frame handling (see CHANGELOG 2026-12-20).
- [x] Portrait (TB) tutorial flowcharts; `--flowchart-landscape` removed.
- [x] Original `batch_LiCSBAS.sh` shell script restored from `main` — **both**
      shell and python batch work (`licsbas-batch` / `examples/example_*.py` keep working).
- [x] Preview PNGs (steps 0X + 1X): **colorbar with units added** (`cbar_label`
      in `plot_lib`: `rad` for wrapped phase, `mm/yr`/`mm` for 1X quantities,
      `coherence` for coh maps); step-15 `mask.png` left untouched (as requested).
- [ ] End-to-end NISAR run on real GUNW `.h5` (CI tests are stubbed / no network yet).

### DONE: LiCSBAS2 bug-fix backports (standard step-02/03 route) — applied 2026-12-19
> The 4 fixes (PLANS_NISAR.md Task 2) are now in v3, each with an inline comment
> citing the LiCSBAS2 commit/PR + a CHANGELOG line (see 2026-12-19 changelog). The
> **02to05 substitution route was audited and needs none of them** (no uint8 `cc`
> cast, no par-file corner write, no `gdal.Warp` GACOS resampling, no `--freq`
> overwrite bug). Full suite green (87 passed, 2 skipped).
- [x] `2627e50` — `_02_ml_prep` `cc.astype(np.uint8)` on NaN → `np.clip(np.nan_to_num(cc),0,255).astype(np.uint8)` (1 line; avoids undefined cast).
- [x] `98cd3a8` (#174) — `_02_ml_prep` EQA.dem_par corner now computed **after** `dlon/dlat` are scaled by `-n` (was off by (n−1)/2 px for `-n>1`, 4 sites).
- [x] `fcd0b6d` (#178) — `_03op_gacos` `gdal.Warp(outputBounds=...)` now outer edges (center ± ½ px); grid recorded in `sltd/sltd_grid.txt` and mismatched existing outputs detected.
- [x] `51f09b6` (#173) — `_02_ml_prep` radar_freq precedence `--freq` > `metadata.txt` > default + Hz sanity check + stale-par update.

### DONE: tutorial & documentation restructure — 2026-12-19
- [x] `tutorial.ipynb` kept as **master single-file template** (marked as such in its title cell); the published tutorials are now composed from it:
      - [x] `tutorial/tutorial_0.ipynb` — Module 0, LiCSAR data (steps `0-1` → `0-5`) **+ the `02to05_unwrap` alternative-route cell** (starts from the *wrapped* phase and substitutes steps `0-2` → `0-5`).
      - [x] `tutorial/tutorial_0_nisar.ipynb` — Module 0, NISAR data (`licsbas-01-get-geotiff-nisar` → `licsbas-nisar2geoc` (+ `licsbas-asf2geoc` alternative) → steps `0-2` → `0-5`).
      - [x] `tutorial/tutorial_0_sbovl.ipynb` — SBOVNL (SBOI) chain, steps `0-1` → `1-6` all with `--sbovl`.
      - [x] `tutorial/tutorial_1.ipynb` — Module 1: time series, steps `11` → `16` + viewers/exports (works from Binder *and* Colab; cross-linked with the Module-0 notebooks in the same session).
- [x] **PNG flowcharts** (landscape, Graphviz `dot`; the long SBOVNL chain is portrait): `tutorial/0_licsar.png`, `0_nisar.png`, `0_sbovl.png`, `1_ts.png`, shown just before the first script of each notebook. Regenerate with `python3 tutorial/make_flowchart.py` (configs in `tutorial/tutorial_cfg/*.json`).
- [x] `licsbas/flowchart.py`: `rankdir` parameter (TB/LR) + **alt-route styling** (amber nodes, dashed edge from the divergence point, "(alternative route)" tag) + `--flowchart-landscape` in `licsbas-batch`.
- [x] `examples/example_4_nisar.py` — NISAR GUNW batch template (dry-run by default; `--execute` to run), completing the standard / reunw / sbovl / nisar template set (`licsbas-batch --list-workflows` already had `nisar`).- [x] README: slimmed (installation detail → `docs/01_installation.md`), tutorials table with Binder + Colab badges for all four split notebooks (+ bash-compatible + batch tutorials); badge/links point at the `towards-v3` branch until v3 lands on `main`.
- [x] `bin/` wrappers: removed the `"DEPRECATED"` banner from **all 55** `bin/*.py` (docstring now reads `"Legacy wrapper for the console entry point \u0060\u0060…\u0060\u0060"`). They remain the supported traditional PATH-based CLI (user requirement).

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
