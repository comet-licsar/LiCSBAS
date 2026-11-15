# TODONEXT — proposed major changes

These are proposed (not yet implemented) larger improvements to LiCSBAS. A brief
implementation plan is in [PLAN.md](PLAN.md).

## 1. Proper package layout: `licsbas` importable package + console entry points
- Today the library is used as flat, top-level modules (`import LiCSBAS_tools_lib`,
  `import cmocean`, `import GMT`, ...), historically made visible via `PYTHONPATH`
  (`bashrc_LiCSBAS.sh`) and now via `pip install .`. This pollutes the top-level
  namespace and risks collisions with unrelated PyPI names (`cmocean`, `SCM`, `GMT`).
- Move everything under a single package, e.g. `licsbas` (with `from licsbas import tools_lib, meta, ...`),
  and move the `bin/` scripts into `licsbas.steps` (or `licsbas.bin`) renamed as modules.
- Install the steps as console entry points (e.g. `licsbas-02-ml-prep`, `licsbas-131-corrections`,
  or unified `licsbas 02_ml_prep`) using their existing `main(argv)` functions,
  replacing the PATH/`.py-with-shebang` invocation style (`LiCSBAS14_vel_std.py ...`)
  used by `batch_LiCSBAS.sh` and the wiki.
- Keep thin compatibility shims for a few releases, then drop `bashrc_LiCSBAS.sh`
  and the `bin/` directory.

## 2. Single source of truth for dependencies and environment
- Remove the parallel dependency definitions: `LiCSBAS_requirements.txt`,
  `LiCSBAS_requirements_optional.txt`, `environment.yml`, `apt.txt`.
  Keep `pyproject.toml` as the canonical list; generate `requirements*.txt`/`environment.yml`
  from it in CI if they must stay for legacy users.
- Prune clearly obsolete entries (e.g. `lapack` stub, `bottleneck`, `colorcet` — a bundled
  fallback `backup_colorcet` already exists) and add sensible lower bounds.

## 3. Publication and release process
- Publish to PyPI (name: `licsbas`) with GitHub trusted publishing and a `bumpversion`/
  single-source `__version__` (currently `LiCSBAS_meta.ver` and `pyproject.toml` can drift —
  they already disagree).
- Add a changelog fragment per release (currently only scattered docstrings).
- Tag releases per the existing "1–2 releases per year" strategy.

## 4. Repository hygiene and packaging test coverage
- Stop shipping generated/IDE artifacts (`__pycache__`, `.idea/`) in the tree;
  complete the `.gitignore` (`*.png`, `*json` are overly broad — they hide e.g. `LICENSE`-adjacent
  files and real JSON data).
- Add a smoke test: import every installed module + one cheap function from each
  (e.g. colormap lookup, IO round-trip of a tiny h5) so `pip install .` regressions fail in CI
  instead of in user notebooks.

## 5. Untangling `licsar_extra`
- `licsar_extra` is currently a git-URL extra (no version pin, no PyPI release).
  Either publish it on PyPI with a real version, or move the needed `lics_unwrap` /
  `lics_tstools` code into LiCSBAS proper under an optional import, so `pip install .[unwrap]`
  is reproducible over time.
- Unify the two unwrapping entry points (`02` vs `02to05`) that are duplicated in
  `batch_LiCSBAS.sh` option parsing.

## 6. Continuously integrated checks
- GitHub Actions: build the wheel for Linux/macOS/Windows, check metadata,
  and run the smoke tests from item 4 on the latest supported Python releases.
