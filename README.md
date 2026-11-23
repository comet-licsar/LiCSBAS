# LiCSBAS

LiCSBAS is an open-source package in Python and bash to carry out InSAR time series analysis primarily using LiCSAR products
(at least interferograms and coherence maps) which are freely available on the [COMET-LiCS web portal](https://comet.nerc.ac.uk/COMET-LiCS-portal/).

It was originally developed by Dr. Yu Morishita during his research visit stay at the University of Leeds and is currently maintained by the COMET team
while his original version (and other tools) exists at his [original site](https://github.com/yumorishita).

With LiCSBAS, users can easily derive the time series and velocity of the displacement if sufficient LiCSAR products are available in the area of interest.
LiCSBAS also contains visualization tools to interactively display the time series of displacement to help investigation and interpretation of the results.

[<img src="https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/comet-lics-web.png"  height="220">](https://comet.nerc.ac.uk/COMET-LiCS-portal/) <img src="https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/sample_vel.png"  height="220">  <img src="https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/sample_ts.png"  height="220">

THIS IS RESEARCH CODE PROVIDED TO YOU "AS IS" WITH NO WARRANTIES OF CORRECTNESS. USE AT YOUR OWN RISK.

**v3 (2026):** LiCSBAS is now a proper Python package (`licsbas`) installable with `pip`;
the traditional CLI workflow (`LiCSBAS*.py` on `PATH`) keeps working unchanged.
Everything that used to be in the original wiki (installation details, v1→v3 differences,
step reference, batch options) now lives in the [docs](docs/) — starting with
[**01 — Installation & v1 → v3**](docs/01_installation.md).

## Installation

```bash
git clone https://github.com/comet-licsar/LiCSBAS.git
cd LiCSBAS
pip install .                # or: pip install .[all] for every optional extra
```

Alternative: a (micro)mamba/conda environment from `environment.yml`.
GDAL is the only hard system requirement (prebuilt `gdal-wheel` binaries are used
where available; otherwise `conda install -c conda-forge gdal`).
Optional features are **extras** and all lazy-loaded — the core pipeline works
without any of them.

→ Full details, extras table, legacy (`bin/`) invocation, development strategy and
bug reports: [**docs/01_installation.md**](docs/01_installation.md).
→ End-to-end chain and per-step command reference: [**docs/02_workflow.md**](docs/02_workflow.md).

## Documentation

The main wiki pages have been ported to local markdown under [docs/](docs/) and updated for v3 (console entry points, `licsbas.batch`, tutorial paths):

| Page | What it covers |
|---|---|
| [**01 — Installation & v1 → v3**](docs/01_installation.md) | Conda environment, `pip install .`, extras, entry points vs legacy wrappers, batch wrapper, dev strategy, bug reports |
| [**02 — Workflow & quick start**](docs/02_workflow.md) | End-to-end chain (01 → 02-05 → 11–16), step-by-step command reference, `02to05` re-unwrapping, SBOI notes |
| [**03 — Visualization**](docs/03_visualization.md) | `licsbas-disp-img`, `licsbas-plot-ts`, `licsbas-plot-network`, tiles, NetCDF export |
| [**04 — Other tools**](docs/04_other_tools.md) | `cum2vel`, dense network, contours, COMET extras, misc. utilities |
| [**05 — NISAR data**](docs/05_nisar.md) *(experimental)* | `licsbas-01-get-nisar-data` (ASF search + download GUNW/GSLC), `licsbas-nisar2geoc` (NISAR GUNW → `GEOC/` + `baselines`), `licsbas-asf2geoc` (ASF GeoTIFF → `GEOC/`) |
| [File structure](docs/file_structure.md) | Output products and per-step naming conventions (`GEOC → TS_* → results_*`) |
| [Links](docs/links.md) | Data sources (ALOS/F3), tools (SNAPHU, GMT, ...), references, community |

Similarly, the original [quick start](https://github.com/yumorishita/LiCSBAS/wiki/2_0_workflow#quick-start) describes the processing philosophy that we keep in our version and only further maintain and develop.

## Tutorials

The tutorials are Jupyter notebooks, runnable directly with [Binder](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/towards-v3) (no local install needed) or in [Google Colab].
They come in two parts — **Module 0** (data preparation, steps 0–5) and **Module 1** (time series, steps 11–16 + viewer) — and in several data flavours:

<!-- NOTE: badges/links point at the `towards-v3` branch until v3 is merged into `main`. -->

| Tutorial | Binder | Google Colab |
|---|---|---|
| [**0 — steps 0\* with LiCSAR data**](https://github.com/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_0.ipynb) (incl. the `02to05_unwrap` alternative route) | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/towards-v3?labpath=tutorial/tutorial_0.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_0.ipynb) |
| [**0 — steps 0\* with NISAR data**](https://github.com/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_0_nisar.ipynb) *(experimental: ASF search + `nisar2geoc`)* | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/towards-v3?labpath=tutorial/tutorial_0_nisar.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_0_nisar.ipynb) |
| [**0 — steps 0\* with SBOVNL (SBOI) data**](https://github.com/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_0_sbovl.ipynb) (`--sbovl` chain) | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/towards-v3?labpath=tutorial/tutorial_0_sbovl.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_0_sbovl.ipynb) |
| [**1 — time series (steps 1\*)** + viewer](https://github.com/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_1.ipynb) | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/towards-v3?labpath=tutorial/tutorial_1.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_1.ipynb) |
| [Bash-compatible tutorial](https://github.com/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_bash-compatible.ipynb) (`licsbas-*` console commands, GMT-free viewer) | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/towards-v3?labpath=tutorial/tutorial_bash-compatible.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_bash-compatible.ipynb) |
| [Batch processing (python & shell)](https://github.com/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_batch.ipynb) — `licsbas.batch` workflows (incl. `nisar`, `reunw_5`, `sbovl`) + PNG flowcharts | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/towards-v3?labpath=tutorial/tutorial_batch.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_batch.ipynb) |

Each **Module 0** notebook links to the **Module 1** (time series) notebook and
works from either side. You can also test the `dev` branch version of the
tutorials: [![Binder (dev)](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/dev?labpath=tutorial/tutorial_0.ipynb)

### Sample products

The tutorials use the original LiCSBAS tutorial data that can be downloaded separately if needed, including the sample scripts for learning outside of the notebook, that is:

- Frame ID: 022D_04826_121209 (Italy, Campi Flegrei)
- Time: 2016/09/09-2018/05/08 (~1.7 years, 67 epochs, ~217 interferograms)
- Clipped around Campi Flegrei (14.03/14.22/40.78/40.90)

- Tutorial: [LiCSBAS_sample_CF.pdf](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/documents/LiCSBAS_sample_CF.pdf) (1.3MB)
- Sample batch script: [batch_LiCSBAS_sample_CF.sh](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/documents/batch_LiCSBAS_sample_CF.sh) (2021/3/11 updated)
- Sample results: [LiCSBAS_sample_CF.tar.gz](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/sample/LiCSBAS_sample_CF.tar.gz) (63MB) (2021/3/11 updated)

## Batch Processing

We recommend users to get familiar with LiCSBAS via the tutorial above.
Once understood, run your chain via the **python batch processor**
(`licsbas/batch.py`, installed entry point `licsbas-batch`, or the legacy
`./batch_LiCSBAS.sh` wrapper) with predefined workflow templates — `standard`,
`reunw_5/10/20`, `sbovl`, `sbovl_abs` and `nisar` — visible in
`licsbas-batch --list-workflows` and as ready-to-adapt scripts in `examples/`:

- `example_1_standard.py` — standard chain (historical defaults),
- `example_2_reunw_02to05.py` — re-unwrapping via `LiCSBAS02to05_unwrap.py`,
- `example_3_sbovl.py` — SBOI chain using the `--sbovl` options,
- `example_4_nisar.py` — NISAR GUNW chain (download + `nisar2geoc` + standard steps).

Each script is a dry run by default and also writes a PNG flowchart of the chain
(Graphviz `dot`), e.g. `licsbas-batch --workflow nisar --nisar-bbox 14.0/14.25/40.75/40.95
--flowchart chain.png --flowchart-landscape`. For simple cases the old command
line keeps working: `./batch_LiCSBAS.sh --help`.

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
