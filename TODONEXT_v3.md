# TODONEXT_v3 — steps remaining to make LiCSBAS v3.0.0 installable via `pip install licsbas`

_State: code is release-ready; tag `v3.0.0` (`8ad74f7`) is on origin; `dist/`
contains `licsbas-3.0.0-py3-none-any.whl` + sdist. Nothing is published yet._

## 1. GitHub release (so the tag is announced + downloadable)
- [ ] Create release **v3.0.0** on `comet-licsar/LiCSBAS` — either:
  - Web UI: https://github.com/comet-licsar/LiCSBAS/releases → "Draft a new
    release" → pick existing tag `v3.0.0`, paste the 3.0.0 CHANGELOG entry, publish.
  - or API (needs a fine-grained PAT with "Contents: read-write" on that repo):
    ```bash
    curl -s -X POST https://api.github.com/repos/comet-licsar/LiCSBAS/releases \
      -H "Authorization: Bearer <PAT>" -H "Accept: application/vnd.github+json" \
      -d '{"tag_name":"v3.0.0","name":"LiCSBAS v3.0.0","body":"pip-installable licsbas package, see CHANGELOG.md","draft":false,"prerelease":false}'
    ```
  - (or `gh release create v3.0.0 --notes-file <(sed -n '/## 3.0.0/,/## /p' CHANGELOG.md)` once `gh` + auth are set up).

## 2. Register on PyPI (this is what makes `pip install licsbas` work)
- [ ] **Register**: create an account at https://pypi.org (or use an existing
      org account). The name **`licsbas` is free** (checked 2026-11: no
      project by that name on PyPI) — register early to avoid squatting.
      Project URL in pyproject already points to the GitHub repo.
- [ ] Create an **API token** (pypi.org → "Add a new token", scope: the
      `licsbas` project). Store it securely (env var / secret manager), **do
      not commit it anywhere**.
- [ ] **Publish** (from a clean checkout at tag `v3.0.0`):
      ```bash
      python -m venv /tmp/publish && /tmp/publish/bin/pip install -U twine build
      git checkout v3.0.0
      python -m build                       # -> dist/licsbas-3.0.0.*
      twine check dist/*                    # metadata sanity
      twine upload dist/*   # reads TWINE_USERNAME (__token__) + TWINE_PASSWORD
      ```
- [ ] **Verify from a truly clean machine/venv**:
      ```bash
      pip install licsbas
      licsbas-01-get-geotiff --help
      pytest   # or a quick import smoke test
      ```
- [ ] Check that `pip install "licsbas[unwrap]"` resolves
      `licsar_extra @ git+https://github.com/comet-licsar/licsar_extra.git@v1.6`
      (needs `git` on the user's machine — documented in README).

## 3. Announce / polish
- [ ] Watch the **GitHub Actions CI** run on the push that carries the tag
      (smoke × 4 Pythons, viewer, mypy) and make sure it is green.
- [ ] Add a PyPI badge to README once published (optional).
- [ ] Consider publishing **`licsar_extra`** to PyPI the same way so the
      `unwrap` extra no longer needs `git` (future; currently pinned
      `@v1.6`, which is stable).
- [ ] Update the COMET tutorial/Binder links to `pip install licsbas` once
      published (tutorials currently work via git+ install too).

## Notes / gotchas
- `usgs-libcomcat` (for `licsbas-get-eqoffsets`) is **intentionally not an
  extra** — it drags in `openquake` and needs working GDAL; README documents
  manual install.
- PyPI requires the wheel to be pure-python (`py3-none-any`) — it is.
- The old name `licsar` is **taken** on PyPI by an unrelated project; do not
  try to use it. `licsbas` is the canonical v3 name.
