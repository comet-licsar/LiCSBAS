#!/usr/bin/env python3
"""
This script applies tide, iono, and gacos corrections at cumulative level (all optional) and calculates STD reduction diagnostics
for LiCSBAS13 results.

===============
Input & output files
===============
Inputs in TS_GEOCml*/ :
 - cum.h5
 - results/
   - mask
 - info/
   - 13parameters.txt or parameters.txt
   - 13ref.txt
   - 12ref.txt

Outputs in TS_GEOCml*/ :
 - cum.h5
   - cum       : corrected cumulative displacement
   - cum_orig  : original uncorrected cumulative displacement

=====
Usage
=====
LiCSBAS131_corrections.py -t TS_GEOCml10 [--tide] [--iono] [--gacos] [--nomask]

 -t        Path to the TS_GEOCml* directory.
 --tide    Apply solid Earth tide correction.
 --iono    Apply ionospheric correction.
 --gacos   Apply GACOS/sltd correction if sltd exists in cum.h5.
 --nomask  Do not use results/mask for STD statistics.

Notes
=====
STD reduction is calculated as:

    reduction_rate = (STD_before - STD_after) / STD_before * 100

Positive value means the correction reduced spatial/temporal scatter.
Negative value means the correction increased scatter.

"""

#%% Change log
"""
20250211 Muhammet Nergizci, COMET-Uni of Leeds, 16/05/2026
 - original implementation

Updated:
 - preserve cum_orig
 - overwrite cum with corrected cumulative
 - calculate STD before/after correction and reduction rate
 - separate tide, iono, and total correction diagnostics
"""

#%% Import
from LiCSBAS_meta import *
import getopt
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"
import sys
import time
import numpy as np
import h5py as h5
import multiprocessing as multi
import LiCSBAS_io_lib as io_lib
import re
from scipy.interpolate import interp1d


class Usage(Exception):
    """Usage context manager"""
    def __init__(self, msg):
        self.msg = msg


#%% Helper functions

def plot_std_reduction_1x2(cum_before, cum_after, tsadir, label="Total correction", mask=None):
    """
    Make 1x2 STD reduction plot:
      left  = STD after vs STD before, with 1:1 line
      right = reduction rate vs STD before

    STD is calculated independently for each epoch.
    """

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    before = cum_before.copy()
    after = cum_after.copy()

    if mask is not None:
        before = before * mask[np.newaxis, :, :]
        after = after * mask[np.newaxis, :, :]

    # STD per epoch
    std_before = np.nanstd(before, axis=(1, 2))
    std_after = np.nanstd(after, axis=(1, 2))

    # Reduction rate per epoch
    reduction_rate = (std_before - std_after) / std_before * 100.0

    # Avoid invalid values
    valid = (
        np.isfinite(std_before)
        & np.isfinite(std_after)
        & np.isfinite(reduction_rate)
        & (std_before > 0)
    )

    std_before = std_before[valid]
    std_after = std_after[valid]
    reduction_rate = reduction_rate[valid]

    fig, axes = plt.subplots(1, 2, figsize=(8, 3.2), constrained_layout=True)

    # --------------------------------------------------
    # Panel 1: one-to-one STD before/after
    # --------------------------------------------------
    ax = axes[0]

    ax.scatter(std_before, std_after, s=8, c="k", alpha=0.8)

    max_std = np.nanmax([std_before.max(), std_after.max()])
    min_std = 0

    ax.plot(
        [min_std, max_std],
        [min_std, max_std],
        color="0.7",
        lw=1.5,
        zorder=0
    )

    ax.set_xlim(min_std, max_std * 1.05)
    ax.set_ylim(min_std, max_std * 1.05)

    ax.set_xlabel(f"STD before {label}")
    ax.set_ylabel(f"STD after {label}")
    ax.grid(True, alpha=0.5)

    # --------------------------------------------------
    # Panel 2: reduction rate vs before STD
    # --------------------------------------------------
    ax = axes[1]

    ax.scatter(std_before, reduction_rate, s=8, c="k", alpha=0.8)
    ax.axhline(0, color="0.5", lw=1.0)

    ax.set_xlabel(f"STD before {label}")
    ax.set_ylabel("STD reduction rate (%)")
    ax.grid(True, alpha=0.5)

    # --------------------------------------------------
    # Save
    # --------------------------------------------------
    safe_label = label.lower().replace(" ", "_").replace("/", "_")
    outfile = os.path.join(tsadir, f"{safe_label}_std_reduction_1x2.png")

    fig.savefig(outfile, dpi=300)
    plt.close(fig)

    print(f"Saved STD reduction plot: {outfile}", flush=True)

    return std_before, std_after, reduction_rate


def fill_nan_timeseries(ref_ts, label="refpoint"):
    """
    Replace/interpolate NaNs in a 1D reference time series.
    """

    if np.any(np.isnan(ref_ts)):
        print(f"Still NaNs in {label} — interpolating over time.", flush=True)

        time_idx = np.arange(ref_ts.shape[0])
        valid = ~np.isnan(ref_ts)

        if np.sum(valid) >= 2:
            f_interp = interp1d(
                time_idx[valid],
                ref_ts[valid],
                kind="linear",
                bounds_error=False,
                fill_value="extrapolate"
            )
            ref_ts = f_interp(time_idx)
        else:
            print(f"WARNING: Not enough valid points in {label} to interpolate. Setting to zero.", flush=True)
            ref_ts[:] = 0.0

    return ref_ts


def get_refpoint_ts(data, refy1, refy2, refx1, refx2, label="data"):
    """
    Get epoch-wise reference value from a reference window.
    If the reference window is NaN for some epochs, use whole-image nanmedian.
    If still NaN, interpolate over time.
    """

    ref_ts = np.nanmean(data[:, refy1:refy2, refx1:refx2], axis=(1, 2))

    if np.any(np.isnan(ref_ts)):
        print(f"Some NaNs detected in {label} reference window — replacing with nanmedian across all pixels.", flush=True)

        whole_median = np.nanmedian(data, axis=(1, 2))
        ref_ts = np.where(np.isnan(ref_ts), whole_median, ref_ts)

    ref_ts = fill_nan_timeseries(ref_ts, label=label)

    return ref_ts


def calc_std_reduction(cum_before, cum_after, mask=None, label="correction"):
    """
    Calculate STD before/after correction and percentage reduction.

    Positive rate = STD reduced after correction.
    Negative rate = STD increased after correction.
    """

    before = cum_before.copy()
    after = cum_after.copy()

    if mask is not None:
        before = before * mask[np.newaxis, :, :]
        after = after * mask[np.newaxis, :, :]

    std_before = np.nanstd(before)
    std_after = np.nanstd(after)

    if std_before == 0 or np.isnan(std_before):
        rate = np.nan
    else:
        rate = (std_before - std_after) / std_before * 100.0

    print(
        f"{label}: STD before = {std_before:.4f}, "
        f"STD after = {std_after:.4f}, "
        f"reduction = {rate:.2f}%",
        flush=True
    )

    return std_before, std_after, rate


def save_std_report(tsadir, stats_rows):
    """
    Save STD reduction diagnostics to a text file.
    """

    outfile = os.path.join(tsadir, "correction_std_reduction.txt")

    with open(outfile, "w") as f:
        f.write("# Correction STD diagnostics\n")
        f.write("# Positive reduction means STD decreased after correction.\n")
        f.write("# label  std_before  std_after  reduction_percent\n")

        for row in stats_rows:
            label, std_before, std_after, rate = row
            f.write(f"{label:25s} {std_before:12.5f} {std_after:12.5f} {rate:10.3f}\n")

    print(f"STD reduction report saved: {outfile}", flush=True)


#%% Main

def main(argv=None):

    #%% Check argv
    if argv is None:
        argv = sys.argv

    start = time.time()

    print("\n{} ver{} {} {}".format(os.path.basename(argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(argv[0]), " ".join(argv[1:])), flush=True)

    #%% Set default
    tsadir = []
    cumname = "cum.h5"

    tide = False
    iono = False
    gacos = False
    maskflag = True

    try:
        n_para = len(os.sched_getaffinity(0))
    except Exception:
        n_para = multi.cpu_count()

    os.environ["OMP_NUM_THREADS"] = "1"

    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(
                argv[1:],
                "ht:ieg",
                ["help", "tide", "iono", "gacos", "nomask"]
            )
        except getopt.error as msg:
            raise Usage(msg)

        for o, a in opts:
            if o == "-h" or o == "--help":
                print(__doc__)
                return 0
            elif o == "-t":
                tsadir = a
            elif o == "-i" or o == "--iono":
                iono = True
            elif o == "-e" or o == "--tide":
                tide = True
            elif o == "-g" or o == "--gacos":
                gacos = True
            elif o == "--nomask":
                maskflag = False

        if not tsadir:
            raise Usage("No tsa directory given, -t is not optional!")
        elif not os.path.isdir(tsadir):
            raise Usage("No {} dir exists!".format(tsadir))
        elif not os.path.exists(os.path.join(tsadir, cumname)):
            raise Usage("No {} exists in {}!".format(cumname, tsadir))

    except Usage as err:
        print("\nERROR:", file=sys.stderr, end="")
        print("  " + str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2

    #%% Directory and file setting
    tsadir = os.path.abspath(tsadir)
    cumfile = os.path.join(tsadir, cumname)
    resultsdir = os.path.join(tsadir, "results")
    infodir = os.path.join(tsadir, "info")

    inparmfile = os.path.join(infodir, "13parameters.txt")
    if not os.path.exists(inparmfile):
        inparmfile = os.path.join(infodir, "parameters.txt")

    ref13file = os.path.join(infodir, "13ref.txt")
    ref12file = os.path.join(infodir, "12ref.txt")

    if not os.path.exists(ref13file):
        raise Usage(f"No 13ref.txt exists in {infodir}")
    if not os.path.exists(ref12file):
        raise Usage(f"No 12ref.txt exists in {infodir}")

    #%% Read cum.h5
    print(f"Reading cumulative file: {cumfile}", flush=True)

    cumh5 = h5.File(cumfile, "r")

    imdates = cumh5["imdates"][()].astype(str).tolist()

    # Use cum_orig if it already exists, so repeated runs always start from original data
    if "cum_orig" in cumh5:
        print("cum_orig already exists in cum.h5; using existing original cumulative.", flush=True)
        cum_org = cumh5["cum_orig"][()]
        cum_org_backup = cum_org.copy()
    else:
        print("cum_orig does not exist; using current cum as original cumulative.", flush=True)
        cum_org = cumh5["cum"][()]
        cum_org_backup = cum_org.copy()

    # Check correction datasets safely
    if tide:
        if "tide" not in cumh5:
            cumh5.close()
            raise Usage("Option --tide was given, but dataset 'tide' does not exist in cum.h5")
        tide_org = cumh5["tide"][()]
    else:
        tide_org = None

    if iono:
        if "iono" not in cumh5:
            cumh5.close()
            raise Usage("Option --iono was given, but dataset 'iono' does not exist in cum.h5")
        iono_org = cumh5["iono"][()]
    else:
        iono_org = None

    if gacos:
        if "sltd" not in cumh5:
            cumh5.close()
            raise Usage("Option --gacos was given, but dataset 'sltd' does not exist in cum.h5")
        gacos_org = cumh5["sltd"][()]
    else:
        gacos_org = None

    cumh5.close()

    n_im, length, width = cum_org.shape

    #%% Handle all-NaN correction epochs

    if tide:
        tide_allnan = np.all(np.isnan(tide_org), axis=(1, 2))
        if np.any(tide_allnan):
            bad_ix = np.where(tide_allnan)[0]
            bad_dates = [imdates[i] for i in bad_ix]
            print(
                f"WARNING: Tide is full-NaN for {len(bad_ix)} epochs. "
                f"Skipping tide by setting to 0 on: {bad_dates}",
                flush=True
            )
            tide_org[tide_allnan, :, :] = 0.0

    if iono:
        iono_allnan = np.all(np.isnan(iono_org), axis=(1, 2))
        if np.any(iono_allnan):
            bad_ix = np.where(iono_allnan)[0]
            bad_dates = [imdates[i] for i in bad_ix]
            print(
                f"WARNING: Iono is full-NaN for {len(bad_ix)} epochs. "
                f"Skipping iono by setting to 0 on: {bad_dates}",
                flush=True
            )
            iono_org[iono_allnan, :, :] = 0.0

    if gacos:
        gacos_allnan = np.all(np.isnan(gacos_org), axis=(1, 2))
        if np.any(gacos_allnan):
            bad_ix = np.where(gacos_allnan)[0]
            bad_dates = [imdates[i] for i in bad_ix]
            print(
                f"WARNING: GACOS/sltd is full-NaN for {len(bad_ix)} epochs. "
                f"Skipping GACOS by setting to 0 on: {bad_dates}",
                flush=True
            )
            gacos_org[gacos_allnan, :, :] = 0.0

    #%% Mask for STD diagnostics
    if maskflag:
        maskfile = os.path.join(resultsdir, "mask")

        if os.path.exists(maskfile):
            mask = io_lib.read_img(maskfile, length, width)
            mask[mask == 0] = np.nan
            print("Using results/mask for STD diagnostics.", flush=True)
        else:
            print("WARNING: mask file does not exist. STD diagnostics use finite pixels from first epoch.", flush=True)
            mask = np.ones((length, width), dtype=np.float32)
            mask[np.isnan(cum_org[0, :, :])] = np.nan
    else:
        print("No mask used for STD diagnostics except NaNs in data.", flush=True)
        mask = np.ones((length, width), dtype=np.float32)
        mask[np.isnan(cum_org[0, :, :])] = np.nan

    #%% Read reference windows
    with open(ref13file, "r") as f:
        ref13area = f.read().split()[0]

    with open(ref12file, "r") as f:
        ref12area = f.read().split()[0]

    ref13x1, ref13x2, ref13y1, ref13y2 = [int(s) for s in re.split("[:/]", ref13area)]
    ref12x1, ref12x2, ref12y1, ref12y2 = [int(s) for s in re.split("[:/]", ref12area)]

    print(f"Using 13ref area: x={ref13x1}:{ref13x2}, y={ref13y1}:{ref13y2}", flush=True)

    #%% Reference cumulative and correction datasets

    refpoint_cum_org = get_refpoint_ts(
        cum_org,
        ref13y1,
        ref13y2,
        ref13x1,
        ref13x2,
        label="cum_org"
    )

    if tide:
        refpoint_tide = get_refpoint_ts(
            tide_org,
            ref13y1,
            ref13y2,
            ref13x1,
            ref13x2,
            label="tide"
        )
    else:
        refpoint_tide = None

    if iono:
        refpoint_iono = get_refpoint_ts(
            iono_org,
            ref13y1,
            ref13y2,
            ref13x1,
            ref13x2,
            label="iono"
        )
    else:
        refpoint_iono = None

    if gacos:
        refpoint_gacos = get_refpoint_ts(
            gacos_org,
            ref13y1,
            ref13y2,
            ref13x1,
            ref13x2,
            label="gacos/sltd"
        )
    else:
        refpoint_gacos = None

    # Reference each epoch
    for i in range(n_im):
        cum_org[i, :, :] -= refpoint_cum_org[i]

        if tide:
            tide_org[i, :, :] -= refpoint_tide[i]

        if iono:
            iono_org[i, :, :] -= refpoint_iono[i]

        if gacos:
            gacos_org[i, :, :] -= refpoint_gacos[i]

    # This is referenced cumulative before correction
    cum_before_correction = cum_org.copy()

    #%% Apply corrections and calculate STD reduction

    stats_rows = []

    print("\nSTD reduction diagnostics:", flush=True)

    # Tide correction
    if tide:
        cum_before_tide = cum_org.copy()
        cum_after_tide = cum_org - tide_org

        std_before, std_after, rate = calc_std_reduction(
            cum_before_tide,
            cum_after_tide,
            mask=mask,
            label="Tide correction"
        )
        stats_rows.append(("Tide_correction", std_before, std_after, rate))

        plot_std_reduction_1x2(
            cum_before_tide,
            cum_after_tide,
            tsadir,
            label="Tide correction",
            mask=mask
        )
        
        cum_org = cum_after_tide

    # Iono correction
    if iono:
        cum_before_iono = cum_org.copy()

        cum_after_iono = cum_org - iono_org

        std_before, std_after, rate = calc_std_reduction(
            cum_before_iono,
            cum_after_iono,
            mask=mask,
            label="Iono correction"
        )
        stats_rows.append(("Iono_correction", std_before, std_after, rate))
        
        plot_std_reduction_1x2(
            cum_before_iono,
            cum_after_iono,
            tsadir,
            label="Iono correction",
            mask=mask
        )       

        cum_org = cum_after_iono

    # GACOS/sltd correction
    if gacos:
        cum_before_gacos = cum_org.copy()

        # Usually sltd is a delay correction to remove.
        cum_after_gacos = cum_org - gacos_org

        std_before, std_after, rate = calc_std_reduction(
            cum_before_gacos,
            cum_after_gacos,
            mask=mask,
            label="GACOS/sltd correction"
        )
        stats_rows.append(("GACOS_sltd_correction", std_before, std_after, rate))

        cum_org = cum_after_gacos

    # Total correction effect
    std_before, std_after, rate = calc_std_reduction(
        cum_before_correction,
        cum_org,
        mask=mask,
        label="Total correction"
    )
    stats_rows.append(("Total_correction", std_before, std_after, rate))
    
    plot_std_reduction_1x2(
        cum_before_correction,
        cum_org,
        tsadir,
        label="Total correction",
        mask=mask
    )
    

    save_std_report(tsadir, stats_rows)

    #%% Save original and corrected cumulative into cum.h5

    print(f"\nWriting original and corrected cumulative datasets to {cumfile} ...", flush=True)

    with h5.File(cumfile, "r+") as f:

        # Save original LiCSBAS cumulative before correction
        if "cum_orig" not in f:
            f.create_dataset(
                "cum_orig",
                data=cum_org_backup.astype("float32"),
                compression="gzip"
            )
            print("Created cum_orig = original uncorrected cumulative", flush=True)
        else:
            print("cum_orig already exists; keeping existing original cumulative", flush=True)

        # Replace cum with corrected cumulative
        if "cum" in f:
            del f["cum"]

        f.create_dataset(
            "cum",
            data=cum_org.astype("float32"),
            compression="gzip"
        )

        print("Updated cum = corrected cumulative", flush=True)

    #%% Finish
    elapsed_time = time.time() - start
    hour = int(elapsed_time / 3600)
    minute = int(np.mod((elapsed_time / 60), 60))
    sec = int(np.mod(elapsed_time, 60))

    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour, minute, sec))
    print("\n{} Successfully finished!!\n".format(os.path.basename(argv[0])))
    print("Output file: {}\n".format(cumfile))

    return 0


#%% main
if __name__ == "__main__":
    sys.exit(main())