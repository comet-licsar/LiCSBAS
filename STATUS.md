# STATUS — LiCSBAS v3.0.0 finalisation

_Last updated: 2026-11-26, branch `towards-v3`, HEAD/tag **`8ad74f7` = `v3.0.0`** (pushed)._

## Current state: **RELEASED TO GITHUB (tag pushed); GitHub release page + PyPI pending (need credentials)**

### Done (verified)
- **Deps final**: hard deps incl. `beautifulsoup4`, `psutil`, `cmcrameri`,
  `python-dateutil`, `utm`, `gdal-wheel` (x86_64/aarch64). Removed unused pins.
- **Extras**: `unwrap` (licsar_extra @ v1.6), `plot` (networkx, seaborn),
  `ml` (scikit-learn), `viewer` (pygmt, ipympl, contextily, Pillow), `all`.
  **No `comcat` extra** — `usgs-libcomcat` documented as manual install
  (pulls in openquake + needs working GDAL).
- **PEP 639 license**: `license = "GPL-3.0-or-later"`, classifier removed —
  wheel/sdist build clean (no warnings).
- **Entry points cleaned**: 14 broken entries removed; ALOS case fixed;
  `get-eqoffsets` added (was missing, `bin/` wrapper referenced it).
  74 total (37 × dual naming). Test asserts every EP resolves to callable `main()`.
- **`LiCSBAS_lib/` deleted** (61 files, commit `7ac0e42`).
  Legacy CLI still works via `bin/` wrappers + entry points + `python -m licsbas.steps.*`.
- **Guarded optional imports**: pygmt (`_17_plot_corrections`, `licsbas/extras.py`),
  sklearn (`131_bo*`), licsar_extra (`02to05`/`17`), libcomcat (`get_eqoffsets` —
  no longer exits at import; clear message + `sys.exit(1)` in `main()`).
- **Bugfixes found during finalization**: `130_remove_noloops` two broken
  `.format()` calls (one `TypeError` at runtime); four `colormaps/*/__init__.py`
  `__all__` set → list.
- **mypy baseline**: `[tool.mypy]` config in pyproject + `mypy` CI job;
  `mypy licsbas/` passes on all 68 source files.
- **`batch_LiCSBAS.sh`**: 122 unquoted `[ ... ]` string tests fixed; `bash -n` clean.
- **Tutorials**: `tutorial/tutorial.ipynb` + `tutorial/tutorial_bash-compatible.ipynb`;
  postBuild (root) downloads 022D_04826_121209 data.
- **Docs**: README (v3 note, install, extras table, comcat manual-install note),
  CHANGELOG (3.0.0 final entry), TODONEXT (v3.1+ adapted),
  `.agents/skills/licsbas/SKILL.md`.
- **Tests**: `tests/test_smoke.py` — **29 passed** in fresh venvs.
- **build**: `python -m build` → sdist+wheel OK, no warnings; dist/ artifacts present.
- **Shipped-wheel verification**: fresh venv `/tmp/v3ship` +
  `dist/licsbas-3.0.0-py3-none-any.whl` → 29 passed; `licsbas-01-get-geotiff --help` works.

### Remaining (blocked on credentials)
1. ~~commit + tag + push~~ **DONE** — `7ac0e42` → `5433f51` → `7f196b9` → `8ad74f7`;
   tag `v3.0.0` re-pointed to `8ad74f7`; branch + tag on origin.
2. **GitHub release v3.0.0** — needs a token (none in env; no `gh` CLI);
   do via web UI (tag exists, ready to attach) or provide a PAT.
3. **PyPI publish** as `licsbas` — needs account/token (`twine upload dist/`).

### Commands that were verified
```
/tmp/v3ship/bin/python -m pytest tests/ -q          # 29 passed (from shipped wheel)
/tmp/v3final/bin/python -m mypy licsbas/            # Success: no issues (68 files)
/tmp/v3final/bin/python -m build                    # sdist+wheel clean
python bin/LiCSBAS_get_eqoffsets.py                 # clean error w/o libcomcat
bash -n batch_LiCSBAS.sh                            # syntax OK
```
