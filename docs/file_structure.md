# File structure

> Faithful port of the original wiki page — the LiCSBAS file layout is unchanged in v3.




| Name                              |     Format      | Contents                                                |
| --------------------------------- | :-------------: | ------------------------------------------------------- |
| GEOCml1/                          |       dir       |                                                         |
| ├── yyyymmdd_yyyymmdd/            |       dir       |                                                         |
| │   ├── yyyymmdd_yyyymmdd.cc      | uint8 (float32) | Coherence                                               |
| │   ├── yyyymmdd_yyyymmdd.unw     |     float32     | Unwrapped interferogram                                 |
| │   └── yyyymmdd_yyyymmdd.unw.png |       png       | Quick look of unw                                       |
| ├── yyyymmdd_yyyymmdd/            |       dir       |                                                         |
| ├── ...                           |                 |                                                         |
| ├── EQA.dem_par                   |      text       | Parameters of equiangular geographical coordinates      |
| ├── slc.mli.par                   |      text       | Parameters of interferograms                            |
| [├── slc.mli]                     |      float32      | Multilook intensity (MLI) image                         |
| [├── slc.mli.png]                 |       png       | Quick look of MLI                                       |
| [├── hgt]                         |      float32      | Height image based on DEM                               |
| [├── hgt.png]                     |       png       | Quick look of hgt                                       |
| [├── baselines]                   |      text       | Perpendicular baselines<br />Used for network plot      |
| [├── E.geo]                       |      float32      | East component of LOS unit vector                       |
| [├── N.geo]                       |      float32      | North component of LOS unit vector                      |
| [└── U.geo]                       |      float32      | Upward component of LOS unit vector<br />Used in Step03 |

[├── ] : optional

### Example of EQA.dem_par

```
width: 3338
nlines: 2685
corner_lat:     38.3944444  decimal degrees
corner_lon:    138.3788889  decimal degrees
post_lat: -0.001 decimal degrees
post_lon: 0.001 decimal degrees

ellipsoid_name: WGS 84
ellipsoid_ra:        6378137.000   m
ellipsoid_reciprocal_flattening:  298.2572236
```

### Example of slc.mli.par

```
range_samples:   3338
azimuth_lines:   2685
radar_frequency: 5405000000.0 Hz
```



## Output of Steps 1-1 to 1-6

| Name                                                |      Format      | Output<br />of Step | Contents                                                     |
| --------------------------------------------------- | :--------------: | :-------------------: | ------------------------------------------------------------ |
| TS_GEOCml1/                                         |       dir        | 1-1                  |                                                              |
| ├── 11bad_ifg_ras/                                  |       dir        | 1-1                  |                                                              |
| │   └── yyyymmdd_yyyymmdd.unw.png                   |       png        | 1-1                  | png of bad ifg at Step 1-1                                    |
| ├── 11ifg_ras/                                      |       dir        | 1-1                  |                                                              |
| │   └── yyyymmdd_yyyymmdd.unw.png                   |       png        | 1-1                  | png of good ifg at Step 1-1                                   |
| ├── 12bad_ifg_cand_ras/                             |       dir        | 1-2                 |                                                              |
| │   └── yyyymmdd_yyyymmdd.unw.png                   |       png        | 1-2                 | png of bad ifg candidate at Step 1-2                         |
| ├── 12bad_ifg_ras/                                  |       dir        | 1-2                 |                                                              |
| │   └── yyyymmdd_yyyymmdd.unw.png                   |       png        | 1-2                 | png of bad ifg at Step 1-2                                   |
| ├── 12ifg_ras/                                      |       dir        | 1-2                 |                                                              |
| │   └── yyyymmdd_yyyymmdd.unw.png                   |       png        | 1-2                 | png of good ifg at Step 1-2                                  |
| ├── 12loop/                                         |       dir        | 1-2                 |                                                              |
| │   ├── bad_ifg_loopref.txt                         |       text       | 1-2                 | List of bad ifgs identified with considering reference point |
| │   ├── bad_ifg_loop.txt                            |       text       | 1-2                 | List of bad ifgs                                             |
| │   ├── bad_ifg_noref.txt                           |       text       | 1-2                 | List of bad ifgs identified without considering reference point |
| │   ├── bad_loop_cand_png/                          |       dir        | 1-2                 |                                                              |
| │   │   └── **yyyymmdd_yyyymmdd_yyyymmdd_loop.png** |       png        | 1-2                 | png of bad loop candidate                                    |
| │   ├── bad_loop_png/                               |       dir        | 1-2                 |                                                              |
| │   │   └── **yyyymmdd_yyyymmdd_yyyymmdd_loop.png** |       png        | 1-2                 | png of bad loop                                              |
| │   ├── **loop_info.txt**                           |       text       | 1-2                 | Statistics of loop closure check                             |
| │   └── loop_ph_rms_masked[.png]                    | float32<br />[png] | 1-2                 | RMS of all loop phases used for selection of preliminary reference (and quick look) |
| │   └── good_loop_png/                              |       dir        | 1-2                 |                                                              |
| │   │   └── **yyyymmdd_yyyymmdd_yyyymmdd_loop.png** |       png        | 1-2                 | png of good loop                                             |
| ├── 12no_loop_ifg_ras/                              |       dir        | 1-2                 |                                                              |
| │   └── yyyymmdd_yyyymmdd.unw.png                   |       png        | 1-2                 | png of ifg without loops                                     |
| ├── 13increment/                                    |       dir        | 1-3                 |                                                              |
| [│   ├── yyyymmdd_yyyymmdd.increment]               |      float32       | 1-3                 | Incremental displacement                                     |
| │   └── yyyymmdd_yyyymmdd.increment.png             |       png        | 1-3                 | png of increment                                             |
| ├── 13resid/                                        |       dir        | 1-3                 |                                                              |
| [│   ├── yyyymmdd_yyyymmdd.res]                     |      float32       | 1-3                 | Residual of SB inversion for each ifg                        |
| │   └── yyyymmdd_yyyymmdd.res.png                   |       png        | 1-3                 | png of res                                                   |
| ├── 16filt_cum/                                     |       dir        | 1-6                | Filtering for cumulative displacement |
| [│   └── **yyyymmdd_deramp.png**]                   |        png         |         1-6         | png of deramping                                             |
| [│   └── **yyyymmdd_hgt_linear.png**]               |        png         |         1-6         | png of topography-correlated noise reduction                 |
| [│   └── **yyyymmdd_hgt_corr.png**] |      png      | 1-6              | png of correlation between hgt and phase                     |
| │   └── **yyyymmdd_filt.png**                       |       png        | 1-6                 | png of filtering                                         |
| ├── 16filt_increment | dir | 1-6 | Filtering for incremental displacement |
| [│   └── yyyymmdd_yyyymmdd_deramp.png]              |        png         |         1-6         | png of deramping                                             |
| [│   └── yyyymmdd_yyyymmdd_hgt_linear.png]          |        png         |         1-6         | png of topography-correlated noise reduction                 |
| [│   └── yyyymmdd_yyyymmdd_hgt_corr.png]            |        png         |         1-6         | png of correlation between hgt and phase                     |
| │   ├── yyyymmdd_yyyymmdd_filt.png | png | 1-6 | png of filt |
| ├── **cum_filt.h5**                                 |       hdf5       | 1-6                 | Filtered cumulative displacement and other metadata          |
| ├── **cum.h5**                                      |       hdf5       | 1-3                 | Unfiltered cumulative displacement and other metadata        |
| ├── info/                                           |       dir        | 1-1                  |                                                              |
| │   ├── 11bad_ifg.txt                               |       text       | 1-1                  | List of bad ifgs identified at Step 1-1                       |
| │   ├── **11ifg_stats.txt**                         |       text       | 1-1                  | Statistics of ifgs                                           |
| │   ├── 11removed_image.txt                         |       text       | 1-1                  | List of removed images identified at Step 1-1                 |
| │   ├── 12bad_ifg_cand.txt                          |       text       | 1-2                 | List of bad ifg candidates identified at Step 1-2            |
| │   ├── 12bad_ifg.txt                               |       text       | 1-2                 | List of bad ifgs identified at Step 1-2                      |
| │   ├── 12network_gap_info.txt                      |       text       | 1-2                 | Network gap information                                      |
| [│   ├── 12no_loop_ifg.txt] | text | 1-2 | List of ifgs with no loop |
| │   ├── 12ref.txt | text | 1-2 | Coordinates of preliminary reference point |
| │   ├── 12removed_image.txt                         |       text       | 1-2                 | List of removed images identified at Step 1-2                |
| │   ├── 13parameters.txt | text | 1-3 | Processing parameters at Step 1-3 |
| │   ├── 13ref.txt | text | 1-3 | Coordinates of  reference point determined ad Step 1-3 |
| │   ├── 13ref.kml | kml | 1-3 | kml of reference point |
| │   ├── 13resid.txt                                 |       text       | 1-3                 | List of RMS of residuals                                     |
| │   ├── 13rms_cum_wrt_med[.png] | float32 | 1-3 | RMS of cum wrt median used for ref selection |
| │   ├── 13used_image.txt                            |       text       | 1-3                 | List of images used for SB inversion at Step 1-3             |
| │   ├── 15parameters.txt | text | 1-5 | Processing parameters at Step 1-5 |
| │   ├── 16parameters.txt | text | 1-6 | Processing parameters at Step 1-6 |
| │   ├── 16ref.txt | text | 1-6 | Coordinates of  reference point determined ad Step 1-6 |
| │   ├── 16ref.kml                                   |        kml         |         1-6         | kml of reference point                                       |
| │   ├── 16rms_cum_wrt_med[.png]                     |      float32       |         1-6         | RMS of filtered cum wrt median used for ref selection        |
| │   ├── EQA.dem_par                                 |        text        |         1-1          | Parameters of equiangular geographical coordinates           |
| │   └── slc.mli.par                                 |       text       | 1-1                  | Parameters of interferograms                                 |
| ├── mask_ts_masked.png                              |       png        | 1-5                 | Preview of masking at Step 1-5 with masked noise indices     |
| ├── **mask_ts.png**                                 |       png        | 1-5                 | Preview of masking at Step 1-5                               |
| ├── network/                                        |       dir        | 1-1                  |                                                              |
| │   ├── network11_all.png                           |       png        | 1-1                  | SB network before Step 1-1                                    |
| │   ├── network11_nobad.png                         |       png        | 1-1                  | SB network after Step 1-1                                     |
| │   ├── **network11.png**                           |       png        | 1-1                  | SB network at Step 1-1 with bad ifgs denoted by red lines     |
| │   ├── network12_all.png                           |       png        | 1-2                 | SB network before Step 1-2                                   |
| │   ├── network12_nobad.png                         |       png        | 1-2                 | SB network after Step 1-2                                    |
| │   ├── **network12.png**                           |       png        | 1-2                 | SB network at Step 1-2 with bad ifgs denoted by red lines    |
| │   ├── network13_all.png                           |       png        | 1-3                 | SB network of all available ifgs                             |
| │   ├── network13_nobad.png                         |       png        | 1-3                 | SB network without bad ifgs identified at Steps 1-1 to 1-2         |
| │   └── **network13.png**                           |       png        | 1-3                 | SB network with bad ifgs denoted by red lines                |
| └── results/                                        |       dir        | 1-1                  |                                                              |
| ├── coh_avg[.png]                                   |      float32       | 1-2                 | Average of coherence (and quick look)                        |
| [   ├── hgt[.png]]                                  |      float32       | 1-1                  | Height (and quick look)                                      |
| ├── mask[.png]                                      |      float32       | 1-5                 | Mask (and quick look)                                        |
| ├── maxTlen[.png]                                   |      float32       | 1-3                 | Maximum time length of connected network (and quick look)    |
| ├── n_gap[.png]                                     |      float32       | 1-3                 | Number of gaps in network (and quick look)                   |
| ├── n_ifg_noloop[.png]                              |      float32       | 1-3                 | Number of interferograms with no loops (and quick look)      |
| ├── n_loop_err[.png]                                |      float32       | 1-2                 | Number of unclosed loops (and quick look)                    |
| ├── n_unw[.png]                                     |      float32       | 1-2                 | Number of used unwrapped data (and quick look)               |
| ├── resid_rms[.png]                                 |      float32       | 1-3                 | RMS of residuals in SB inversion (and quick look)            |
| [   ├── slc.mli[.png]]                              |      float32       | 1-1                  | MLI (and quick look)                                         |
| ├── stc[.png]                                       |      float32       | 1-4                 | Spatiotemporal consistency (and quick look)                  |
| ├── vel[.png]                                       |      float32       | 1-3                 | Velocity (and quick look)                                    |
| ├── vel.filt[.png]                                  |      float32       | 1-6                 | Velocity for filtered time series (and quick look)           |
| ├── vel.filt.mskd[.png]                             |      float32       | 1-6                 | Masked velocity for filtered time series (and quick look)    |
| ├── vel.mskd[.png]                                  |      float32       | 1-5                 | Masked velocity (and quick look)                             |
| ├── vintercept[.png]                                |      float32       | 1-3                 | Intercept of linear model (and quick look)                   |
| ├── vintercept.filt[.png]                           |      float32       | 1-6                 | Intercept of linear model for filtered time series (and quick look) |
| ├── vintercept.filt.mskd[.png]                      |      float32       | 1-6                 | Masked intercept of linear model for filtered time series (and quick look) |
| └── vstd[.png]                                      |      float32       | 1-4                 | STD of velocity (and quick look)                             |

[├── ] : optional, **bold**: important files that should be checked

**[Back to the workflow](02_workflow.md) · [Other tools](04_other_tools.md)**
