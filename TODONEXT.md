# TODONEXT — LiCSBAS v3 follow-ups

Done in this series (see CHANGELOG.md / PLAN.md): proper pip-packaged `licsbas`
package, 53 console entry points, 61 legacy shims, guarded optional imports,
`main()` wrapping, single-source versioning, cleaned repo/ignore files,
CI-ready import tests.

## Next release (3.0.0 final)
- [ ] CI green on the new layout (see `.github/workflows/`), publish to PyPI as
      `LiCSBAS 3.0.0`.
- [ ] Decide the PyPI name: `LiCSBAS` (canonical, keeps import/package
      distinction) vs `licsbas`. **Current packaging uses `LiCSBAS`.**
- [ ] Tag `v3.0.0` and update the Binder/Colab tutorial links to the v3
      layout (the tutorial notebook imports `LiCSBAS_*` — add a compatibility
      header or switch to `from licsbas...`).
- [ ] `licsar_extra`: pin a tag/release on PyPI (currently a git+URL extra).

## v3.1+
- [ ] Remove the legacy shims and `bin/` wrappers (only after a 3.x + one
      extra release; emit DeprecationWarning 2 releases before removal).
- [ ] Migrate steps off top-level globals in `main()` (argparser currently
      relies on `globals()` in a few scripts).
- [ ] `batch_LiCSBAS.sh`: fix unquoted `[ ... ]` tests (cosmetic
      `unary operator expected` noise; e.g. lines using `$p12_multi_prime`).
- [ ] Consider per-step `pyproject` metadata (per-step help, `--version`).
- [ ] Docs: wiki pages still reference the old flat layout; add a
      "v3 layout" page mapping old names → new names.
- [ ] `LiCSBAS_get_eqoffsets`: make `usgs-libcomcat` a soft dependency (skip
      with a warning instead of hard-exit).
- [ ] Type hints / `mypy` clean baseline (start with `tools_lib` + `io_lib`).

## Housekeeping
- [ ] Remove `LiCSBAS_lib/` entirely at 4.0 (shims go, `LiCSBAS*.py` names
      deprecated in favour of `licsbas-*`).
- [ ] Archive `LiCSBAS_requirements*.txt` / `environment*.yml` with a
      deprecation notice (they are only kept to mirror v1/v2 setups).
