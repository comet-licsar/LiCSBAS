# TODONEXT — LiCSBAS v3 follow-ups

Done in the v3 series (see CHANGELOG.md / PLAN.md / STATUS.md): proper
pip-packaged `licsbas` package, 72 console entry points (dual `licsbas-*`/
`licbas-*` naming), `main()` wrapping, single-source versioning, cleaned
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
- [ ] Docs: wiki pages still reference the old flat layout; add a
      "v3 layout" page mapping old names → new names.
- [ ] Type hints / `mypy` clean baseline (start with `tools_lib` + `io_lib`).
- [ ] PyPI: publish `licsbas` (and consider a PyPI release of `licsar_extra`).

## Housekeeping
- [ ] Archive `LiCSBAS_requirements*.txt` / `environment_optional.yml` with a
      deprecation notice (kept only to mirror v1/v2 setups); keep `environment.yml`
      (still the recommended conda route).
