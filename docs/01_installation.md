# 1. Installation & v1 → v3

> LiCSBAS now ships as the Python package **`licsbas`**, installable with `pip`.
> The traditional CLI workflow keeps working: the `LiCSBAS*.py` commands from the
> original wiki are installed as thin `bin/` wrappers that run the same `main()`
> code as the new `licsbas-*` console entry points. All optional packages are
> imported **lazily** — the core pipeline works without any extras.

## What changed from v1/v2 to v3

| Original (v1/v2 wiki) | v3 (this repository) |
| --- | --- |
| clone + `source bashrc_LiCSBAS.sh` (manual `PATH`) | `pip install .` — installs `bin/` wrappers **and** `licsbas-*` entry points |
| `import LiCSBAS_meta` (top-level script import) | `from licsbas import meta` |
| `import LiCSBAS_tools_lib` | `from licsbas import tools_lib` |
| `LiCSBAS14_vel_std.py` (PATH-based) | `licsbas-14-vel-std` — **same code**, legacy name still on `PATH` |
| `batch_LiCSBAS.sh` | `licsbas-batch` / `python -m licsbas.batch` / `examples/*.py` |
| repo at `github.com/yumorishita/LiCSBAS` (discontinued) | repo at `github.com/comet-licsar/LiCSBAS` |

*Note:* legacy *imports* (`import LiCSBAS_meta`) are **not** emulated — use
`licsbas.meta`. Entry-point names are all `licsbas-*`.

## Option A — pip (recommended)

```bash
git clone https://github.com/comet-licsar/LiCSBAS.git
cd LiCSBAS
pip install .                      # install licsbas (licsbas-01-get-geotiff ... on PATH)
# pip install 'git+https://github.com/comet-licsar/LiCSBAS.git'   # without a checkout
python -c "import licsbas; print(licsbas.__version__)"   # sanity check
licsbas-plot-ts -h                 # sanity check one entry point
```

Python ≥ 3.8 (tested 3.10–3.13). We recommend Linux/UNIX in general; on Windows,
MobaXterm should allow installation if really needed.

**GDAL** is a hard dependency (imported by ~14 step modules): prebuilt
`gdal-wheel` binaries are pulled in automatically on x86_64/aarch64. On other
platforms provide GDAL via your OS/distribution or conda, e.g.
`conda install -c conda-forge gdal` or `sudo apt install python3-gdal` (see `apt.txt`).
Other system packages for optional features (Debian/Ubuntu):

```bash
sudo apt install gmt            # pygmt viewer (extra `viewer`)
sudo apt install snaphu         # re-unwrapping in 02to05 (extra `unwrap`)
```

## Option B — (micro)mamba/conda environment

```bash
# "${SHELL}" <(curl -L micro.mamba.pm)  # to install micromamba
micromamba env create -f environment.yml
micromamba activate licsbas
# micromamba env update -n licsbas -f environment_optional.yml   # to add some optional extras
```

## Optional extras (pip extras)

| Extra | Installs | Needed for |
| --- | --- | --- |
| `unwrap` | [licsar_extra](https://github.com/comet-licsar/licsar_extra) @ v1.6 | re-unwrapping in step `02to05` and corrections in `132` (needs SNAPHU) |
| `plot` | networkx, seaborn | network plots (`120_choose_reference`, ERA5 plots, `tools_lib` helpers) |
| `ml` | scikit-learn | RANSAC corrections in `131_boi_absolute` / `131_bovl2abs` |
| `viewer` | pygmt, ipympl, contextily, Pillow | `licsbas.extras` (pygmt viewer) + Jupyter widgets (needs system `gmt`) |
| `all` | all of the above | e.g. `pip install .[all]` |

All extras are **optional** — each step imports them lazily and prints install
guidance only when actually needed.

`LiCSBAS_get_eqoffsets.py` (earthquake-lookup offsets) needs `usgs-libcomcat`,
which we deliberately do **not** ship as an extra because its dependency chain
pulls in `openquake` and a source GDAL build; install it manually only if you
use that step (e.g. `conda install -c conda-forge libcomcat`, or
`pip install usgs-libcomcat` on a system where GDAL is already installed).

**NISAR / ASF data (optional, experimental).** Optional steps ingest NISAR / ASF
L2 products (see [05_nisar.md](05_nisar.md)): they need the
[licsar_extra](https://github.com/comet-licsar/licsar_extra) NISAR extras
(`pip install licsar_extra[nisar]`) and optionally ASF credentials in
`~/.asf_credentials` (`ASF_USERNAME` / `ASF_PASSWORD`). The classic LiCSAR
download step `licsbas-get-geotiff` is untouched.

## Running the steps

Both invocation styles work and are equivalent (the legacy names run the same
`main()` code as the new ones):

```bash
# new-style console entry points (installed by pip)
licsbas-check-install            # sanity check of the installation
licsbas-02-ml-prep --help
licsbas-14-vel-std -t TS/

# legacy workflow, exactly as before (PATH-based .py scripts)
source bashrc_LiCSBAS.sh          # adds bin/ to PATH (the PYTHONPATH line is now optional)
LiCSBAS_check_install.py          # same sanity check, legacy name
LiCSBAS14_vel_std.py -t TS/

# batch pipeline (now python; see licsbas/batch.py and examples/)
./batch_LiCSBAS.sh --check-only                       # prints the commands
python3 examples/example_1_standard.py --execute      # standard chain
python3 examples/example_2_reunw_02to05.py --execute  # 02to05 re-unwrapping
python3 examples/example_3_sbovl.py --execute         # SBOI (--sbovl) chain
python3 examples/example_4_nisar.py --execute         # NISAR GUNW chain
```

## Development strategy & bug reports

We keep a regular release strategy of 1–2 releases per year. The `main` branch
is considered stable and relatively up to date (if the main branch contains a
bug, please report it to us). The `dev` branch is considered testing and can
contain routine bugs that are usually fast-resolved by our team.

Besides those branches, there are several forks existing, maintained by current
or previous COMET members. Although we incorporate most of their precious
scripts into this repository, they can include original approaches not present
or documented here (yet). For example, Dr. Qi Ou prepared optional steps as
`LiCSBAS1xx` scripts and [provided documentation](https://github.com/qi-ou/LiCSBAS/blob/main/README.md)
on their use, as she worked her way to her [article on Tian Shan](https://www.researchsquare.com/article/rs-7529996/v1).

If you have found an issue or bug, please report it on the
[issues page](https://github.com/comet-licsar/LiCSBAS/issues). If you are
following the original (v1/v2) installation steps, please be aware of the
different repository URL: this version of LiCSBAS resides at
[github.com/comet-licsar/LiCSBAS](https://github.com/comet-licsar/LiCSBAS)
while the discontinued [github.com/yumorishita/LiCSBAS](https://github.com/yumorishita/LiCSBAS)
wiki refers to the old layout.

**Back to the [workflow](02_workflow.md).**
