# 2. Workflow & Quick start

This is a v3-adapted port of the original [wiki](https://github.com/yumorishita/LiCSBAS/wiki)
workflow pages. Commands are now `licsbas-*` console entry points (the legacy `LiCSBAS*.py`
names still work via the installed `bin/` wrappers). Use `-h`/`--help` for the full
option list of any command.

**Package layout (v3):** numbered pipeline steps live in `licsbas/steps/`,
and the unnumbered utility scripts in `licsbas/scripts/` (e.g. `cum2vel`,
`disp_img`, `plot_ts`, `out2nc`, `profile`). All are exposed as `licsbas-*`
console entry points, or run as e.g. `python -m licsbas.scripts._cum2vel`.

**Name mapping (legacy → v3):**

| Original (v1.x) | v3 entry point |
| --- | --- |
| `LiCSBAS01_get_geotiff.py` | `licsbas-get-geotiff` (ALOS: `licsbas-get-geotiff-alos`) |
| `LiCSBAS02_ml_prep.py` | `licsbas-ml-prep` |
| `LiCSBAS03op_GACOS.py` | `licsbas-gacos` |
| `LiCSBAS04op_mask_unw.py` | `licsbas-mask-unw` |
| `LiCSBAS05op_clip_unw.py` | `licsbas-clip-unw` |
| `LiCSBAS11_check_unw.py` | `licsbas-check-unw` |
| `LiCSBAS12_loop_closure.py` | `licsbas-loop-closure` |
| `LiCSBAS13_sb_inv.py` | `licsbas-sb-inv` |
| `LiCSBAS14_vel_std.py` | `licsbas-vel-std` |
| `LiCSBAS15_mask_ts.py` | `licsbas-mask-ts` |
| `LiCSBAS16_filt_ts.py` | `licsbas-filt-ts` |
| `LiCSBAS17_plot_corrections.py` | `licsbas-plot-corrections` |
| `LiCSBAS_plot_ts.py` | `licsbas-plot-ts` |

## Quick start

Make a working directory with the [frame ID of interest](#21-identify-frame-id) and move, e.g.:

```bash
mkdir 124D_04854_171313
cd 124D_04854_171313
```

Copy the batch script and edit it:

```bash
copy_batch_LiCSBAS.sh        # or: cp $(python -c 'import licsbas; print(licsbas.__file__)')/../batch_LiCSBAS.sh.batch .
```

e.g. for Campi Flegrei from September 2016 to May 2018:

```
do05op_clip="y"                              # y/n
p05_clip_range_geo="14.03/14.22/40.78/40.90"  # e.g. 130.11/131.12/34.34/34.6 (in deg)
p01_start_date="20160909"                    # default: 20141001
p01_end_date="20180508"                      # default: today
```

Run the batch script:

```bash
./batch_LiCSBAS.sh
```

> **Predefined workflow templates (v3).** The batch processor also accepts named
> templates via `--workflow` (or `make_config(...)` in python, see
> [`tutorial/tutorial_batch.ipynb`](../tutorial/tutorial_batch.ipynb) and
> `licsbas.batch.register_workflow`):
>
> ```bash
> licsbas-batch --list-workflows
> licsbas-batch --workflow reunw_5 --check-only    # 02to05 re-unwrapping, multilook 5
> licsbas-batch --workflow sbovl --tide --iono      # SBOI chain + corrections
> ```
>
> Any `BatchConfig` field can be overridden by flags, so the templates compose
> with the classic settings above.

All steps from 0-1 (downloading GeoTIFF files) to 1-6 (time series analysis) run, and the
`GEOC`, `GEOCml1`, `TS_GEOCml1` (and `log`) directories are created.

Display the derived time series and velocity:

```bash
licsbas-plot-ts -i TS_GEOCml1/cum_filt.h5 &
```

![velocity quicklook](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/sample_vel.png) ![timeseries plot](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/sample_ts.png)

To improve the result, edit parameters in `batch_LiCSBAS.sh` and re-run it.

## Workflow overview

```
1. Identify a frame (2.1)
2. Steps 0-1 to 0-5: prepare stack of UNW data (2.2)
3. Steps 1-1 to 1-6: time series processing (2.3)
4. Batch processing (2.4)
5. For COMET users (2.5)
```

![workflow](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/workflow.png)

## 2.1. Identify frame ID

### On the COMET-LiCS web

First, you need to identify the frame to process which includes your area of interest.
LiCSAR products are provided on a predefined LiCSAR frame basis. You can see the area of
frames, frame IDs, and the number of available interferograms on the
[COMET-LiCS web portal](https://comet.nerc.ac.uk/comet-lics-portal/).

![frame overview](https://raw.githubusercontent.com/wiki/yumorishita/LiCSBAS/images/comet-lics-web_039A_053.png)

### Prepare the processing directory

Once you have identified the frame ID and confirmed that sufficient interferograms are
available, make a processing directory named after the frame ID:

```bash
mkdir 039A_05373_131313
cd 039A_05373_131313
```

## 2.2. Steps 0-1 to 0-5: prepare stack of UNW data

All steps can be run sequentially using the [batch script](#24-batch-processing).
Steps 0-3 to 0-5 are optional and can be run in no particular order.

### Step 0-1: download GeoTIFF from COMET-LiCS web portal

```
licsbas-get-geotiff [-f FRAME] [-s start_date] [-e end_date] [--get_gacos] [--n_para int]
```

Downloads GeoTIFF files of unw (unwrapped interferogram) and cc (coherence) in the
specified frame ID. The `-f` option is not necessary when the frame ID can be
automatically identified from the working directory name. GACOS data can also be
downloaded if available. Existing GeoTIFF files are not re-downloaded; only newly
available data are downloaded.

### Step 0-2: convert (and downsample)

```
licsbas-ml-prep -i GEOCdir [-o GEOCmldir] [-n nlook] [--freq float] [--n_para int]
```

Converts GeoTIFF unw/cc to float32/uint8 for time series analysis and optionally
downsamples (multilooks). `--freq` is the radar frequency in Hz (default 5.405e9 for
Sentinel-1; e.g. 1.27e9 for ALOS).

### Step 0-3: GACOS correction (optional)

```
licsbas-gacos -i in_dir -o out_dir [-g gacosdir] [--fillhole] [--n_para int]
```

Applies a tropospheric correction using [GACOS](http://www.gacos.net/) data, which may
be downloaded at step 0-1 or obtained from the GACOS web. The impact of the correction
can be checked with `GACOS_info.png` and `*/*.gacos.png`.

### Step 0-4: mask UNW (optional)

```
licsbas-mask-unw -i in_dir -o out_dir [-c coh_thre] [-r x1:x2/y1:y2] [-f txtfile]
```

Masks low-coherence or user-specified areas of the unw stack. Effective when the data
include areas with many unwrapping errors, and can improve step 1-2 (loop closure).

### Step 0-5: clip UNW (optional)

```
licsbas-clip-unw -i in_dir -o out_dir [-r x1:x2/y1:y2] [-g lon1/lon2/lat1/lat2]
```

Clips a rectangular area of interest from unw and cc data. Smaller data → faster
processing and better loop-closure results.

## 2.3. Steps 1-1 to 1-6: time series processing

### Step 1-1: quality check — `licsbas-check-unw`

```
licsbas-check-unw -d ifgdir [-t tsadir] [-c coh_thre] [-u unw_thre]
```

Checks quality of the unw data and identifies bad interferograms based on average
coherence and coverage of the unw data. Also prepares the time series working
directory `TS_GEOCml*` (overwritten if already exists).

### Step 1-1b (COMET extra): choose reference — `licsbas-choose-reference`

Identifies a preliminary reference point for the loop-closure check, stored in
`info/12ref.txt`.

### Step 1-2: loop closure — `licsbas-loop-closure`

```
licsbas-loop-closure -d ifgdir [-t tsadir] [-l loop_thre] [--multi_prime]
    [--rm_ifg_list file] [--n_para int]
```

Identifies bad unw by checking loop closure (default RMS threshold 1.5 rad).
A preliminary reference point with all valid unw data and the smallest RMS of loop
phases is also determined.

### Steps 1-3a (COMET extras): unwrapping corrections (130–133)

Before (or instead of) the plain inversion, the COMET pipeline can detect and correct
systematic unwrapping errors in the individual interferograms
(Lazecký et al., 2024; IGARSS 2021):

```
licsbas-residual-threshold        # 131: flag high-residual pixels/ifgs
licsbas-boi-absolute              # 131: absolute offset correction (RANSAC; extra "ml")
licsbas-bovl2abs                  # 131: convert relative offsets to absolute
licsbas-unwrapping-correction     # 132: re-unwrap corrected ifgs (extra "unwrap" + SNAPHU)
licsbas-133-write-h5             # 133: write corrected cumulative displacement
licsbas-sb-inv --keep_incfile     # 130: keep incremental files for inspection
licsbas-plot-corrections          # 17: plot the corrections for QC
```

These are optional; the original pipeline skips directly from 1-2 to 1-3.

### Step 1-3: small baseline inversion — `licsbas-sb-inv`

```
licsbas-sb-inv -d ifgdir [-t tsadir] [--inv_alg LS|WLS] [--mem_size float]
    [--gamma float] [--n_para int] [--n_unw_r_thre float] [--keep_incfile] [--gpu]
```

Inverts the SB network to obtain the time series and velocity using the NSBAS approach
(López-Quiroz et al., 2009; Doin et al., 2011). A stable reference point is determined
after the inversion: the point with minimum RMS of the time series wrt median and
minimum n_gap.

### Step 1-4: velocity std by bootstrap — `licsbas-vel-std`

```
licsbas-vel-std -t tsadir [--mem_size float] [--gpu]
```

Calculates the standard deviation of the velocity (bootstrap) and STC (spatio-temporal
consistency; Hanssen et al., 2008).

### Step 1-5: mask time series — `licsbas-mask-ts`

```
licsbas-mask-ts -t tsadir [-c coh_thre] [-u n_unw_r_thre] [-v vstd_thre] [-T maxTlen_thre]
    [-g n_gap_thre] [-s stc_thre] [-i n_ifg_noloop_thre] [-l n_loop_err_thre]
    [-r resid_rms_thre] [--vmin float] [--vmax float] [--keep_isolated] [--noautoadjust]
```

Makes a mask using several noise indices (coh_avg, n_unw, vstd, maxTlen, n_gap, stc,
n_ifg_noloop, n_loop_err, resid_rms). A pixel is masked if any index is worse than the
threshold. Default thresholds:

```
C-band: -c 0.05 -u 1.5 -v 100 -T 1 -g 10 -s 5 -i 50 -l 5 -r 2
L-band: -c 0.01 -u 1   -v 200 -T 1 -g 1  -s 10 -i 50 -l 1 -r 10
```

| Noise index | Meaning |
| --- | --- |
| coh_avg | Average interferometric coherence across the stack (0–1) |
| n_unw | Number of unwrapped data used (ratio to number of images) |
| vstd | Standard deviation of the velocity (mm/yr), from step 1-4 |
| maxTlen | Maximum time length of the connected network (years) |
| n_gap | Number of gaps in the network |
| stc | Spatio-temporal consistency (mm) |
| n_ifg_noloop | Number of ifgs with no loops (unchecked unwrapping errors possible) |
| n_loop_err | Number of unclosed loops after network refinement |
| resid_rms | RMS of residuals in the SB inversion (mm) |

### Step 1-6: filter (& deramp) time series — `licsbas-filt-ts`

```
licsbas-filt-ts -t tsadir [-s filtwidth_km] [-y filtwidth_yr] [-r deg]
    [--hgt_linear] [--hgt_min int] [--hgt_max int] [--nomask] [--n_para int]
    [--range x1:x2/y1:y2 | --range_geo lon1/lon2/lat1/lat2]
    [--ex_range ... | --ex_range_geo ...]
```

Applies a spatio-temporal filter (HP in time, LP in space with gaussian kernel, as in
StaMPS) to the displacement time series. Optional deramping (`-r 1|bl|2`) and
subtraction of the topography-correlated linear component (`--hgt_linear`). A stable
reference point is re-determined after filtering.

**Back to [installation](01_installation.md) · [visualization](03_visualization.md) ·
[file structure](file_structure.md)**

## 2.4. Batch processing

You can run all steps sequentially with `batch_LiCSBAS.sh`. Copy the template with
`copy_batch_LiCSBAS.sh` (or `cp batch_LiCSBAS.sh.batch batch_LiCSBAS.sh`), edit the
script to set starting/ending steps and optional parameters, then:

```bash
./batch_LiCSBAS.sh
```

## 2.5. For COMET users (JASMIN)

If you are working on JASMIN with `licsar_framebatch`, you don't need to install Python
or modules — activate the environment instead:

```bash
module load licsar_framebatch
source /gws/smf/j04/nceo_geohazards/software/condalics/load_condalics.rc
```

You can skip step 0-1 because the GeoTIFFs already exist in your framebatch processing
directory (after `framebatch_06_geotiffs.sh`): run `update_bperp_file.sh` to refresh the
baselines file, then **start from step 0-2** in your frame directory.

On JASMIN you may run the whole LiCSBAS procedure with the LiCSAR command:

```shell
licsar2licsbas.sh $FRAME
```

with optional re-unwrapping of multilooked data (Lazecký et al., IGARSS 2021), e.g.
towards 1×1 km resolution:

```shell
licsar2licsbas.sh -M 10 $FRAME
```

**Back to [quick start](#quick-start) · [workflow overview](#workflow-overview)**
