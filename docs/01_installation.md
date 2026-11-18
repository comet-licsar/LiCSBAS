# 1. Installation

> v3 note: LiCSBAS now ships as the Python package **`licsbas`**, installable with `pip`
>(see the [README](../README.md#installation) for the full extras table).
> The `LiCSBAS*.py` commands from the original wiki keep working via the installed `bin/`
> wrappers; the recommended invocations are the `licbas-*` console entry points.
> All steps import optional packages **lazily** — the core pipeline works without any extras.

## Option A — pip (recommended)

```bash
git clone https://github.com/comet-licsar/LiCSBAS.git
cd LiCSBAS
pip install .                # or: pip install .[all] for every optional extra
python -c "import licsbas; print(licsbas.__version__)"   # sanity check
licbas-plot-ts -h            # sanity check one entry point
```

**GDAL** is a hard system dependency (imported by ~14 step modules):
prebuilt `gdal-wheel` binaries are pulled in automatically on x86_64/aarch64.
On other platforms provide GDAL via your OS or conda, e.g.
`sudo apt install python3-gdal` (see `apt.txt`) or `conda install -c conda-forge gdal`.

Other system packages that may be needed for optional features (Debian/Ubuntu):

```bash
sudo apt install gmt            # pygmt viewer (extra `viewer`)
```

Optional extras (all lazy — only needed when you use the corresponding feature):

| Extra     | Provides                                                            | Needed for                                    |
| --------- | ------------------------------------------------------------------- | --------------------------------------------- |
| `unwrap`  | [licsar_extra](https://github.com/comet-licsar/licsar_extra) @ v1.6 | re-unwrapping in `02to05`, corrections in `132` (needs SNAPHU) |
| `plot`    | networkx, seaborn                                                   | network plots, ERA5 plots                     |
| `ml`      | scikit-learn                                                        | RANSAC corrections in `131_boi_absolute` / `131_bovl2abs` |
| `viewer`  | pygmt, ipympl, contextily, Pillow                                   | `licsbas.extras` viewer, Jupyter widgets (needs system `gmt`) |
| `all`     | all of the above                                                    | e.g. `pip install .[all]`                     |

`licsbas-get-eqoffsets` (earthquake-lookup offsets) needs `usgs-libcomcat`, which is
deliberately **not** shipped as an extra (its dependency chain triggers a source GDAL build);
install it manually only if you use that step (e.g. `conda install -c conda-forge libcomcat`).

## Option B — (micro)mamba/conda

```bash
micromamba env create -f environment.yml
micromamba activate licsbas
# optional extras:
micromamba env update -n licsbas -f environment_optional.yml
```

## Legacy (pre-v3) conda installation

The original wiki installation instructions (conda-forge environment built from
`environment.yml` + manual `pip install`) still work for a pre-v3-style checkout, but
new installs should prefer `pip install .` as above. The only practical difference:
pre-v3 you had to clone the repository and add `bin/` to your `PATH` manually;
v3 installs the same `bin/` wrappers and all `licbas-*` entry points automatically.

**Back to the [workflow](02_workflow.md).**
