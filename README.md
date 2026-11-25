
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

## Recommended installation

Our recommendation is to use Linux OS or UNIX in general, but MobaXterm should allow installation on Windows if really needed.
After git clone this repository:
```bash
git clone https://github.com/comet-licsar/LiCSBAS.git
cd LiCSBAS
```
With [(micro)mamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html) or conda, you can create and activate environment:
```bash
# "${SHELL}" <(curl -L micro.mamba.pm)  # to install micromamba
micromamba env create -f environment.yml
micromamba activate licsbas
# pip install git+https://github.com/comet-licsar/licsar_extra.git  # easiest way to install extra tools for reunwrapping and iono/tide corrections
# micromamba env update -n licsbas -f environment_optional.yml   # to add other optional extras (see below)
```
Afterwards, you need to set path prior to using LiCSBAS commands using:
```bash
./bashrc_LiCSBAS.sh
LiCSBAS_check_install.py # to check if installation ran ok 
```


## Alternative installation via pip

LiCSBAS can be directly installed with `pip` (Python >= 3.10 required):

```bash
# directly from the repository
pip install 'git+https://github.com/comet-licsar/LiCSBAS.git'

# or from a checkout of the repository (or a release tarball)
# pip install .
```

However, **GDAL** (Python bindings) is expected to be provided by your OS/distribution or conda and is *not* installed by pip,
e.g. `conda install -c conda-forge gdal` or `sudo apt install python3-gdal` (see `apt.txt`).

Following extras can be installed using pip:

| Extra | Installs | Needed for |
| --- | --- | --- |
| `unwrap` | [licsar_extra](https://github.com/comet-licsar/licsar_extra) | for unwrapping in `LiCSBAS02to05_unwrap.py` and iono/tide corrections in `LiCSBAS131_corrections.py` |
| `comcat` | usgs-libcomcat | `LiCSBAS_get_eqoffsets.py` only |
| `all` | both of the above | e.g. `pip install .[all]` |


## Sample Products and Tutorial

We offer tutorial jupyter notebooks used at annual [COMET InSAR Workshops](https://comet-licsar.github.io/ciw.html), launchable in both Binder and Google Colab:

| Tutorial | Binder | Google Colab |
|---|---|---|
| [main](https://github.com/comet-licsar/LiCSBAS/blob/main/licsbas_tutorial.ipynb) (LiCSBAS <v3) | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/HEAD?labpath=licsbas_tutorial.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/main/licsbas_tutorial.ipynb) |
| [v3.0rc](https://github.com/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial.ipynb) (`licsbas-*` console commands) | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/towards-v3?labpath=tutorial/tutorial.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial.ipynb) |
| [v3 batch processing](https://github.com/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_batch.ipynb) (`licsbas.batch` workflows) | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/towards-v3?labpath=tutorial/tutorial_batch.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/towards-v3/tutorial/tutorial_batch.ipynb) |

The tutorial uses pre-processed data that it downloads. You can also use the original LiCSBAS tutorial data (same AOI, different frame and time period):

- Tutorial: [LiCSBAS_sample_CF.pdf](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/documents/LiCSBAS_sample_CF.pdf) (1.3MB)
- Sample batch script: [batch_LiCSBAS_sample_CF.sh](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/documents/batch_LiCSBAS_sample_CF.sh) (2021/3/11 updated)
- Sample results: [LiCSBAS_sample_CF.tar.gz](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/sample/LiCSBAS_sample_CF.tar.gz) (63MB) (2021/3/11 updated)

## Batch Processing

We recommend users to get familiar with LiCSBAS via tutorial above.
Once understood, you can set own batch script simply by
```bash
copy_batch_LiCSBAS.sh
nano batch_LiCSBAS.sh # i.e. edit the file in your favourite editor
./batch_LiCSBAS.sh  # to start the batch processing - or perform a useful dry run if 'check_only' is enabled
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

## Related Tools

[LiCSAR Extra](https://github.com/comet-licsar/licsar_extra)  
[InSAR Phase Bias Correction](https://github.com/ymaghsoudi-InSAR/InSAR_PhaseBias_Correction)  
[ICASAR](https://github.com/matthew-gaddes/ICASAR)  
[LiCS Atmo](https://github.com/matthew-gaddes/LiCSAtmo)  


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
