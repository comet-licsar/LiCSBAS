# STATUS — LiCSBAS v3.0.0 finalisation

_Last updated: 2026-11-26, branch `towards-v3`._

## Current state: **READY TO TAG/RELEASE** (commit + tag remain)

### Done (verified)
- **Deps final**: hard deps incl. `beautifulsoup4`, `psutil`, `cmcrameri`,
  `python-dateutil`, `utm`, `gdal-wheel` (x86_64/aarch64). Removed unused pins.
- **Extras**: `unwrap` (licsar_extra @ v1.6), `plot` (networkx, seaborn),
  `ml` (scikit-learn), `viewer` (pygmt, ipympl, contextily, Pillow),
  `comcat` (usgs-libcomcat), `all`.
- **PEP 639 license**: `license = "GPL-3.0-or-later"`, classifier removed —
  wheel/sdist build clean (no warnings).
- **Entry points cleaned**: 14 broken entries removed (plot-tile, plot-velocity*,
  multipolygon, extras, extras-light, meta); ALOS case fixed. 72 remain
  (36 × dual naming). **New test asserts every EP resolves to callable main().**
- **`LiCSBAS_lib/` deleted** (git status shows `D LiCSBAS_lib/_shims/*`).
  Legacy imports no longer emulated; legacy CLI still works via `bin/` wrappers
  + entry points + `python -m licsbas.steps.*` (all 53 steps have `__main__`).
- **Guarded optional imports**: pygmt in `_17_plot_corrections` (catches
  Exception incl. GMTCLibNotFound), `licsbas/extras.py` helpful ImportError,
  sklearn in `131_bo*`, licsar_extra in `02to05`/`17`.
- **Tutorials**: `tutorial/tutorial.ipynb` + `tutorial/tutorial_bash-compatible.ipynb`
  (moved into tutorial/); postBuild (root) downloads 022D_04826_121209 data.
- **Docs**: README (v3 note, install, extras table, binder/colab links, CF frame),
  CHANGELOG (3.0.0 final entry above rc1), TODONEXT (v3.1+ adapted),
  `.agents/skills/licsbas/SKILL.md` created.
- **Tests**: `tests/test_smoke.py` — **29 passed** in clean venv `/tmp/v3test`
  (base install, no optional deps).
- **build**: `python -m build` → sdist+wheel OK, no warnings.

### Remaining before release
1. `git add -A && git commit` (all the above).
2. `git tag v3.0.0` → push branch + tag (needs credentials — not in env).
3. Create GitHub release v3.0.0 (needs token).
4. Optional: `pip upload` to PyPI as `licsbas` (needs account/token).

### Commands that were verified
```
/tmp/v3test/bin/python -m pytest tests/ -q          # 29 passed
/tmp/v3test/bin/python -m build                     # sdist+wheel clean
python bin/LiCSBAS14_vel_std.py -h                  # legacy wrapper works
/tmp/v3test/bin/pip install "/path/LiCSBAS[unwrap]" # licsar_extra v1.6 from git OK
```
