
# LiCSBAS

LiCSBAS is an open-source package in Python and bash to carry out InSAR time series analysis primarily using LiCSAR products
(at least interferograms and coherence maps) which are freely available on the [COMET-LiCS web portal](https://comet.nerc.ac.uk/COMET-LiCS-portal/).    

It was originally developed by Dr. Yu Morishita during his research visit stay at the University of Leeds and is currently maintained by the COMET team
while his original version (and other tools) exists at his [original site](https://github.com/yumorishita).  

Here we try keep a unity and ingest new functionality to this version that contains various updates but a lot of experimental functions that were
developed within a programming learning curve of several COMET members.  

With LiCSBAS, users can easily derive the time series and velocity of the displacement if sufficient LiCSAR products are available in the area of interest.
LiCSBAS also contains visualization tools to interactively display the time series of displacement to help investigation and interpretation of the results.

[<img src="https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/comet-lics-web.png"  height="220">](https://comet.nerc.ac.uk/COMET-LiCS-portal/) <img src="https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/sample_vel.png"  height="220">  <img src="https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/sample_ts.png"  height="220">

THIS IS RESEARCH CODE PROVIDED TO YOU "AS IS" WITH NO WARRANTIES OF CORRECTNESS. USE AT YOUR OWN RISK.

**v3 note (2026):** LiCSBAS now ships as a proper Python package (`licsbas`) installable with `pip`
(see [Installation](#installation)). The traditional CLI workflow is emulated:
`LiCSBAS14_vel_std.py` on `PATH` (thin `bin/` wrapper) runs the same code as the
`licsbas-14-vel-std` console entry point or `python -m licsbas.steps._14_vel_std`.
Legacy *imports* (`import LiCSBAS_meta`) are no longer emulated — use `licsbas.meta`.
Everything else described below keeps working.

## Installation

LiCSBAS v3 is installable with `pip` (Python >= 3.8, tested 3.10–3.13). It installs the `licsbas` package
(library, steps, bundled colormaps) **plus** `bin/` wrappers and console entry points, so the traditional workflow
(`LiCSBAS*.py` commands on `PATH`) keeps working unchanged.

Our recommendation is to use Linux OS or UNIX in general, but MobaXterm should allow installation on Windows if really needed.

### Option A — pip (recommended)

```bash
git clone https://github.com/comet-licsar/LiCSBAS.git
cd LiCSBAS
pip install .                      # install licsbas (licsbas-01-get-geotiff ... on PATH)
# pip install 'git+https://github.com/comet-licsar/LiCSBAS.git'   # without a checkout
```

**GDAL**: prebuilt `gdal-wheel` binaries are pulled in automatically on x86_64/aarch64.
On other platforms, provide GDAL via your OS/distribution or conda,
e.g. `conda install -c conda-forge gdal` or `sudo apt install python3-gdal` (see `apt.txt`).

### Option B — (micro)mamba/conda environment

```bash
# "${SHELL}" <(curl -L micro.mamba.pm)  # to install micromamba
micromamba env create -f environment.yml
micromamba activate licsbas
# micromamba env update -n licsbas -f environment_optional.yml   # to add some optional extras
```

### Optional extras (pip extras)

| Extra | Installs | Needed for |
| --- | --- | --- |
| `unwrap` | [licsar_extra](https://github.com/comet-licsar/licsar_extra) @ v1.6 | re-unwrapping in step `02to05` and corrections in `132` (needs SNAPHU) |
| `plot` | networkx, seaborn | network plots (`120_choose_reference`, ERA5 plots, `tools_lib` helpers) |
| `ml` | scikit-learn | RANSAC corrections in `131_boi_absolute` / `131_bovl2abs` |
| `viewer` | pygmt, ipympl, contextily, Pillow | `licsbas.extras` (pygmt viewer) + Jupyter widgets (needs system `gmt`) |
| `all` | all of the above | e.g. `pip install .[all]` |

All extras are **optional** — the core pipeline works without any of them (each step imports them lazily and prints install guidance when actually needed).

`LiCSBAS_get_eqoffsets.py` (earthquake-lookup offsets) needs `usgs-libcomcat`, which we deliberately do **not** ship as an extra because its dependency chain pulls in `openquake` and a source GDAL build; install it manually only if you use that step (e.g. `mamba install -c conda-forge libcomcat` or `pip install usgs-libcomcat` on a system with GDAL already installed).

**NISAR / ASF data (optional, experimental).** Optional steps ingest NISAR / ASF L2 products (see [docs/05_nisar.md](docs/05_nisar.md)):
`licsbas-01-get-nisar-data` (search a bbox on ASF + download GUNW/GSLC `.h5` into per-frame subfolders),
`licsbas-nisar2geoc` (convert NISAR GUNW `.h5` → LiCSBAS `GEOC/` layout: iono + range-offset corrections, rasterio WGS-84 export with a shared grid, `baselines` + `metadata.txt`), and `licsbas-asf2geoc` (convert ASF pre-processed GeoTIFF products into a `GEOC/` layout). They need the [licsar_extra](https://github.com/comet-licsar/licsar_extra) NISAR extras (`pip install licsar_extra[nisar]`) and optional ASF credentials in `~/.asf_credentials`. The classic LiCSAR download step `licsbas-get-geotiff` is unchanged.

### Running the steps

Both invocation styles work and are equivalent (the legacy names run the same `main()` code as the new ones):

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
```

## Documentation

The main wiki pages have been ported to local markdown under [docs/](docs/) and updated for v3 (console entry points, `licsbas.batch`, tutorial paths):

| Page | What it covers |
|---|---|
| [**01 — Installation**](docs/01_installation.md) | Conda environment, `pip install .`, entry points, batch wrapper, sanity checks |
| [**02 — Workflow & quick start**](docs/02_workflow.md) | End-to-end chain (01 → 02-05 → 11–16), step-by-step command reference, `02to05` re-unwrapping, SBOI notes |
| [**03 — Visualization**](docs/03_visualization.md) | `licsbas-disp-img`, `licsbas-plot-ts`, `licsbas-plot-network`, tiles, NetCDF export |
| [**04 — Other tools**](docs/04_other_tools.md) | `cum2vel`, dense network, contours, COMET extras, misc. utilities |
| [**05 — NISAR data**](docs/05_nisar.md) *(experimental)* | `licsbas-01-get-nisar-data` (search + download GUNW/GSLC), `licsbas-nisar2geoc` (NISAR GUNW → `GEOC/` + `baselines`), `licsbas-asf2geoc` (ASF GeoTIFF → `GEOC/`) |
| [File structure](docs/file_structure.md) | Output products and per-step naming conventions (`GEOC → TS_* → results_*`) |
| [Links](docs/links.md) | Data sources (ALOS/F3), tools (SNAPHU, GMT, ...), references, community |

Similarly, the original [quick start](https://github.com/yumorishita/LiCSBAS/wiki/2_0_workflow#quick-start) describes the processing philosophy that we keep in our version and only further maintain and develop.

If you are following the original (v1/v2) installation steps, please be aware of the different repository URL: this version of LiCSBAS resides at [github.com/comet-licsar/licsbas](https://github.com/comet-licsar/licsbas) while the discontinued [github.com/yumorishita/LiCSBAS](https://github.com/yumorishita/LiCSBAS) wiki refers to the old layout.

### Bug reports

If you have found an issue or bug using the main branch, please report it on the [issues page](https://github.com/comet-licsar/LiCSBAS/issues).

## Development strategy

We keep regular release strategy of 1-2 releases per year.
The 'main' branch is considered stable and relatively up-to-date (if the main branch contains bug, please report it to us).
The 'dev' branch is considered testing and can contain routine bugs that are usually fast-resolved by our team.  

Besides those branches, there are several forks existing, maintained by current or previous COMET members.
Although we incorporate most of their precious scripts, extending functionality of LiCSBAS,
these can include original approaches not present or documented here (yet).  

For example, Dr. Qi Ou prepared optional steps as LiCSBAS1xx scripts and [provided documentation](https://github.com/qi-ou/LiCSBAS/blob/main/README.md) on their use,
as she worked her way to her [article on Tian Shan](https://www.researchsquare.com/article/rs-7529996/v1).

## Tutorials

The tutorials are Jupyter notebooks that you can directly [run using Binder](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/HEAD) (no local install needed), or open in the [repository](https://github.com/comet-licsar/LiCSBAS/tree/main/tutorial):

| Tutorial | Binder | Google Colab |
|---|---|---|
| [LiCSBAS tutorial](https://github.com/comet-licsar/LiCSBAS/blob/main/tutorial/tutorial.ipynb) | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/HEAD?labpath=tutorial/tutorial.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/main/tutorial/tutorial.ipynb) |
| [Bash-compatible tutorial](https://github.com/comet-licsar/LiCSBAS/blob/main/tutorial/tutorial_bash-compatible.ipynb) (`licsbas-*` console commands, GMT-free `pylight_plot_interactive` viewer) | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/HEAD?labpath=tutorial/tutorial_bash-compatible.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/main/tutorial/tutorial_bash-compatible.ipynb) |
| [Batch processing (python & shell)](https://github.com/comet-licsar/LiCSBAS/blob/main/tutorial/tutorial_batch.ipynb) — `licsbas.batch` workflows incl. `reunw_5`, PNG flowcharts | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/HEAD?labpath=tutorial/tutorial_batch.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/main/tutorial/tutorial_batch.ipynb) |

You can also test the `dev` branch version of the main tutorial: [![Binder (dev)](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/dev?labpath=tutorial/tutorial.ipynb)

### Sample products

The tutorial still uses the original LiCSBAS tutorial data that can be downloaded separately if needed, including the sample scripts for learning outside of the notebook, that is:

- Frame ID: 022D_04826_121209 (Italy, Campi Flegrei)
- Time: 2016/09/09-2018/05/08 (~1.7 years, 67 epochs, ~217 interferograms)
- Clipped around Campi Flegrei (14.03/14.22/40.78/40.90)

- Tutorial: [LiCSBAS_sample_CF.pdf](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/documents/LiCSBAS_sample_CF.pdf) (1.3MB)

- Sample batch script: [batch_LiCSBAS_sample_CF.sh](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/documents/batch_LiCSBAS_sample_CF.sh) (2021/3/11 updated)
- Sample results: [LiCSBAS_sample_CF.tar.gz](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/sample/LiCSBAS_sample_CF.tar.gz) (63MB) (2021/3/11 updated)

## Batch Processing

We recommend users to get familiar with LiCSBAS via tutorial above.
Once understood, run your chain via the **python batch processor**
(`licsbas/batch.py`, installed entry point `licsbas-batch`, or the legacy
`./batch_LiCSBAS.sh` wrapper). All options of the old `batch_LiCSBAS.sh`
(01-16, 02to05 re-unwrapping, sbovl/sbovl_abs, optional 03-06, ...) are
available as attributes of `licsbas.batch.BatchConfig`:

```python
from licsbas.batch import BatchConfig, run_batch, save_flowchart

run_batch(cfg)            # dry run first: run_batch(cfg, dry_run=True)
cfg = BatchConfig(start_step=1, end_step=16, nlook=10, sbovl=True,
                  p01_start_date="20160909", p01_end_date="20180508")
 save_flowchart(cfg, "chain.png")   # PNG flowchart of the chain (Graphviz)
```

Ready-to-adapt example scripts (each also writes a PNG flowchart):

- `examples/example_1_standard.py` — standard chain (historical defaults),
- `examples/example_2_reunw_02to05.py` — re-unwrapping via `LiCSBAS02to05_unwrap.py`,
- `examples/example_3_sbovl.py` — SBOI chain using the `--sbovl` options.

For simple cases the old command line keeps working: `./batch_LiCSBAS.sh --help`.

## Citations

Morishita, Y.; Lazecky, M.; Wright, T.J.; Weiss, J.R.; Elliott, J.R.; Hooper, A. LiCSBAS: An Open-Source InSAR Time Series Analysis Package Integrated with the LiCSAR Automated Sentinel-1 InSAR Processor. *Remote Sens.* **2020**, *12*, 424, https://doi.org/10.3390/RS12030424.

Morishita, Y.: Nationwide urban ground deformation monitoring in Japan using Sentinel-1 LiCSAR products and LiCSBAS. *Prog. Earth Planet. Sci.* **2021**, *8*, 6,  https://doi.org/10.1186/s40645-020-00402-7.

Lazecký, M.; Spaans, K.; González, P.J.; Maghsoudi, Y.; Morishita, Y.; Albino, F.; Elliott, J.; Greenall, N.; Hatton, E.; Hooper, A.; Juncu, D.; McDougall, A.; Walters, R.J.; Watson, C.S.; Weiss, J.R.; Wright, T.J. LiCSAR: An Automatic InSAR Tool for Measuring and Monitoring Tectonic and Volcanic Activity. *Remote Sens.* **2020**, *12*, 2430, https://doi.org/10.3390/rs12152430.

Lazecký, M.; Ou, Q.; McGrath, J.; Payne, J.; Espin, P.; Hooper, A.; Wright, T. Strategies for improving and correcting unwrapped interferograms implemented in LiCSBAS. *Procedia Computer Science* **2024**, *239*, 2408-2412, https://doi.org/10.1016/j.procs.2024.06.435.

## Acknowledgements

This work has been accomplished during Dr. Yu Morishita’s visit at University of Leeds, funded by JSPS Overseas Research Fellowship.
Further updates of the software are organised by the COMET LiCSAR team.

COMET is the UK Natural Environment Research Council's Centre for the Observation and Modelling of Earthquakes, Volcanoes and Tectonics.
LiCSAR is developed as part of the NERC large grant, "Looking inside the continents from Space" (NE/K010867/1).
LiCSAR contains modified Copernicus Sentinel data [2014-] analysed by the COMET.
LiCSAR uses [JASMIN](http://jasmin.ac.uk), the UK’s collaborative data analysis environment.  

Further development and maintenance of LiCSBAS is supported through activities within the NERC large grant, "Looking inside the continents from Space" (NE/K010867/1),
and ESA Open SAR Library 4000140600/23/I-DT extension, recognised as the [AlignSAR InSAR Time Series extension](https://github.com/AlignSAR/alignSAR/tree/main/alignsar_extension_InSAR_TS).  

The [Scientific Colour Maps](http://www.fabiocrameri.ch/colourmaps.php) ([Crameri, 2018](https://doi.org/10.5194/gmd-11-2541-2018)) is used in LiCSBAS.


[<img src="https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/COMET_logo.png"  height="60">](https://comet.nerc.ac.uk/)   [<img src="https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/logo-leeds.png"  height="60">](https://environment.leeds.ac.uk/see/)  [<img src="https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/LiCS_logo.jpg"  height="60">](https://comet.nerc.ac.uk/COMET-LiCS-portal/) 
