# PLAN.md — LiCSBAS v3.0 execution plan (branch `towards-v3`)

v3.0 = a proper, pip-installable `licsbas` package (steps, library, colormaps) with a
**backwards-compatibility layer** so that the legacy workflow keeps working unchanged:
- `LiCSBAS*.py` scripts on `PATH` (e.g. sourced via `bashrc_LiCSBAS.sh`)
- `batch_LiCSBAS.sh` invocations
- `import LiCSBAS_meta` / `from LiCSBAS_out2nc import loadall2cube` style imports
- `from LiCSBAS_extras_light import pylight_plot_interactive` (notebooks/Binder)

Base state: commit `9ce4ac0` ("towards v3") already contains the package re-layout
(`licsbas/`), 53 step modules, legacy shims, `bin/` wrappers, `pyproject.toml`.

## Steps

| # | Step | Commit message | Status |
|---|------|----------------|--------|
| 0 | Housekeeping: drop committed `.idea/` IDE files, complete `.gitignore`, write this plan | `v3: prep — clean IDE files, execution plan` | ✅ `8a828fa` |
| 1 | Port the dev-side manual tweaks (`2e75647`) and the Binder-friendly mpl previewer (`3e19980`) into the v3 layout: `tools_lib` regex fix, `batch_LiCSBAS.sh` settings (`sbovl` master switch etc.), step fixes (`LiCSBAS01/02/120/131_corr/13_sb_inv`), requirements/env files, README merge, `LiCSBAS_extras_light.py` → `licsbas/extras_light.py` + shim | `v3: port dev tweaks and extras_light previewer` | ✅ `d74a6ec` |
| 2 | Robustness: fix pre-existing syntax break in `LiCSBAS131_bovl2abs`, guard the external `daz_lib_licsar` import, guard other non-PyPI third-party imports in steps, `compileall` all 53 steps + library | `v3: repair bovl2abs, guard external imports` | ✅ `758abe0` |
| 3 | Packaging: add `utm`, `extras_light` (+shim) to `pyproject.toml`, bump version to `3.0.0rc1`, build wheel, install into clean env, import test lib + steps, exercise entry points and `bin/` wrappers, dry-run `batch_LiCSBAS.sh` (`check_only=y`) | `v3: packaging updates and full install verification` | ✅ `bf0296b` |
| 4 | Docs/cleanup: README (v3 layout, pip + conda, entry points, compatibility layer, batch workflow), `CHANGELOG.md`, `TODONEXT.md` status, tidy requirements/environment files (single source of truth = `pyproject.toml`) | `v3: documentation and dependency cleanup` | ✅ `6a34163` |
| 5 | Smoke tests (`tests/`) + GitHub Actions CI (install + import + CLI smoke on Python 3.10–3.13) | `v3: smoke tests and CI` | ☐ |
| 6 | Repo skill: pi-compatible `.agents/skills/licsbas/SKILL.md` (+ `references/`) describing LiCSBAS v3.0 for any agent/pi session working in this repo | `v3: add LiCSBAS agent skill` | ☐ |
| 7 | Final verification (wheel build, wrapper + batch dry-run, skill frontmatter check) and **push** `towards-v3` | — | ☐ |

## Compatibility guarantees (acceptance criteria)

1. `pip install .` in a clean env: all `licsbas.*` and legacy top-level `LiCSBAS_*` imports work.
2. `bashrc_LiCSBAS.sh` + `LiCSBAS_check_install.py` style `PATH` workflow works (wrappers).
3. `batch_LiCSBAS.sh` runs (dry `check_only=y` at minimum) and echoes/invokes valid commands.
4. New-style entry points `licsbas-<step>` work identically (same `main()` code path as wrappers).
5. `licsar_extra` remains an **optional** extra (`pip install .[unwrap]`), not a hard dependency.
6. `LiCSBAS_extras_light` (Binder/Colab viewer) importable both as `licsbas.extras_light` and `LiCSBAS_extras_light`.

## Out of scope (tracked in TODONEXT.md)

- Publishing `licsar_extra` on PyPI (separate repo `comet-licsar/licsar_extra`).
- Actual PyPI release of `licsbas` (needs maintainer credentials; CI + metadata prepared).
- Removing the compatibility layer (only after a full v3.x cycle — shims + `bin/` wrappers).
