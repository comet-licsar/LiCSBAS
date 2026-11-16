
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

<img src="https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/LiCSBAS_plot_ts.py_demo_small.gif" alt="Demonstration Video"/>

THIS IS RESEARCH CODE PROVIDED TO YOU "AS IS" WITH NO WARRANTIES OF CORRECTNESS. USE AT YOUR OWN RISK.

**v3 note (2026):** LiCSBAS now ships as a proper Python package (`licsbas`) installable with `pip`
(see [Installation](#installation)). The old flat layout is emulated by compatibility layers:
`import LiCSBAS_meta` → `licsbas.meta`, `LiCSBAS14_vel_std.py` on `PATH` → `licsbas-14-vel-std`
console entry point, etc. Everything described below keeps working.

## Installation

LiCSBAS v3 is installable with `pip` (Python >= 3.10 required). It installs the `licsbas` package
(library, steps, bundled colormaps) **and** a backwards-compatibility layer, so the traditional workflow
(`LiCSBAS*.py` commands on `PATH`, `import LiCSBAS_meta` / `import LiCSBAS_tools_lib` style imports) keeps working unchanged.

Our recommendation is to use Linux OS or UNIX in general, but MobaXterm should allow installation on Windows if really needed.

### Option A — pip (recommended)

```bash
git clone https://github.com/comet-licsar/LiCSBAS.git
cd LiCSBAS
pip install .                      # install licsbas + compatibility layer
# pip install 'git+https://github.com/comet-licsar/LiCSBAS.git'   # without a checkout
```

**GDAL** (Python bindings) is expected to be provided by your OS/distribution or conda and is *not* installed by pip,
e.g. `conda install -c conda-forge gdal` or `sudo apt install python3-gdal` (see `apt.txt`).

### Option B — (micro)mamba/conda environment

```bash
# "${SHELL}" <(curl -L micro.mamba.pm)  # to install micromamba
micromamba env create -f environment.yml
micromamba activate licsbas
# micromamba env update -n licsbas -f environment_optional.yml   # to add some optional extras
# pip install git+https://github.com/comet-licsar/licsar_extra.git  # optional extras for re-unwrap and iono/tide corrections (requires SNAPHU)
```

### Optional extras (pip extras)

| Extra | Installs | Needed for |
| --- | --- | --- |
| `unwrap` | [licsar_extra](https://github.com/comet-licsar/licsar_extra) | GPU unwrapping in step `02to05` and corrections in `131_corrections` (needs SNAPHU) |
| `comcat` | usgs-libcomcat | `LiCSBAS_get_eqoffsets.py` only |
| `all` | both of the above | e.g. `pip install .[all]` |

`licsar_extra` is **optional** — all other steps work without it.

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

# batch pipeline (unchanged)
copy_batch_LiCSBAS.sh
nano batch_LiCSBAS.sh             # edit in your favourite editor
./batch_LiCSBAS.sh
```

## Documentation and Bug Reports

If you have found an issue or bug using the main branch, please report it on the [issues page](https://github.com/comet-licsar/LiCSBAS/issues).

We assume users are familiar with the standard installation procedure of Github repositories, therefore we do not adapt the original [**wiki**](https://github.com/yumorishita/LiCSBAS/wiki) pages that document well all the originally implemented procedures by Dr. Yu Morishita, 
including the installation procedure (if you follow this procedure, please be aware of the different repository URL, this version of LiCSBAS resides at [github.com/comet-licsar/licsbas](https://github.com/comet-licsar/licsbas) while the original wiki refers to the discontinued [github.com/yumorishita/licsbas](https://github.com/yumorishita/licsbas)).

Similarly, the original [quick start](https://github.com/yumorishita/LiCSBAS/wiki/2_0_workflow#quick-start) describes processing philosophy that we keep in our version and only further maintain and develop.  

## Development strategy

We keep regular release strategy of 1-2 releases per year.
The 'main' branch is considered stable and relatively up-to-date (if the main branch contains bug, please report it to us).
The 'dev' branch is considered testing and can contain routine bugs that are usually fast-resolved by our team.  

Besides those branches, there are several forks existing, maintained by current or previous COMET members.
Although we incorporate most of their precious scripts, extending functionality of LiCSBAS,
these can include original approaches not present or documented here (yet).  

For example, Dr. Qi Ou prepared optional steps as LiCSBAS1xx scripts and [provided documentation](https://github.com/qi-ou/LiCSBAS/blob/main/README.md) on their use,
as she worked her way to her [article on Tian Shan](https://www.researchsquare.com/article/rs-7529996/v1).

## Sample Products and Tutorial

The latest tutorial is available as a [Jupyter Notebook](https://github.com/comet-licsar/LiCSBAS/blob/main/licsbas_tutorial.ipynb) that you can directly
[run using Binder](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/HEAD?labpath=licsbas_tutorial.ipynb), or you can test the [dev branch version](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/dev?labpath=licsbas_tutorial.ipynb) that contains latest updates.  

Furthermore, if you have Google account, you can use Google Colab:  
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/main/licsbas_tutorial.ipynb)  

The tutorial still uses the original LiCSBAS tutorial data that can be downloaded separately if needed, including the sample scripts for learning outside of the notebook, that is:

- Frame ID: 124D_04854_171313 (Italy)
- Time: 2016/09/09-2018/05/08 (~1.7 years, 67 epochs, ~217 interferograms)
- Clipped around Campi Flegrei (14.03/14.22/40.78/40.90)

- Tutorial: [LiCSBAS_sample_CF.pdf](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/documents/LiCSBAS_sample_CF.pdf) (1.3MB)

- Sample batch script: [batch_LiCSBAS_sample_CF.sh](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/documents/batch_LiCSBAS_sample_CF.sh) (2021/3/11 updated)
- Sample results: [LiCSBAS_sample_CF.tar.gz](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/sample/LiCSBAS_sample_CF.tar.gz) (63MB) (2021/3/11 updated)

## Batch Processing

We recommend users to get familiar with LiCSBAS via tutorial above.
Once understood, you can set own batch script simply by
```bash
copy_batch_LiCSBAS.sh
nano batch_LiCSBAS.sh # i.e. edit the file in your favourite editor
```

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
