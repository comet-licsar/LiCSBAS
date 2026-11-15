#!/usr/bin/env python3
"""
========
Overview
========
This script takes a vstd.tif and removes the reference effect from the line-of-sight
vstd maps by fitting a spherical, exponential or linear model to the scatter between
uncertainty and distance away from the reference center.

Input:
    vstd.tif
Output:
    vstd_scaled.tif
    vstd_scaled.png
    vstd_rescaling_parameters.txt
"""
####################

import pyproj
import utm
import argparse
from scipy import stats
from scipy.optimize import curve_fit
import random
import os
import time
import numpy as np

import matplotlib.pyplot as plt
import sys
from osgeo import gdal
from mpl_toolkits.axes_grid1.axes_divider import make_axes_locatable

# changelog
ver = "1.0"; date = 20220501; author = "Qi Ou, University of Oxford"
    # removes the reference effect from the line-of-sight vstd maps by fitting a spherical model
    # to the scatter between uncertainty and distance away from the reference center.
ver = "1.1"; date = 20230815; author = "Qi Ou, University of Leeds"
    # choose a better model between spherical and exponential judging from the residuals
    # iteratively reduce the distance over which to fit the model to tackle difficult cases
    # generalise utm zone determination
ver = '1.2'; date = 20250217; author = 'Yuan Gao, Dehua Wang, Uni of Leeds'
    # Linear model has beed added by Yuan Gao and output of modeling parameters has been added
    # by Dehua Wang, University of Leeds, 20250217
ver = '1.3'; date = 20260329; author = 'Fengnian Chang, Uni of Leeds'
    # remove lmfit dependency; use scipy.optimize.curve_fit instead
    # fix invalid escape warnings and tf/tif variable bug
    # improve fallback logic and exception safety


# define global variable
plot_variogram = True


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """
    Use a multiple inheritance approach to use features of both classes.
    The ArgumentDefaultsHelpFormatter class adds argument default values to the usage help message.
    The RawDescriptionHelpFormatter class keeps the indentation and line breaks in the __doc__.
    """
    pass


def init_args():
    global args
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=CustomFormatter)
    parser.add_argument('-i', dest='infile', default="vstd.tif", type=str, help="input .tif file")
    parser.add_argument('-o', dest='outfile', default="vstd_scaled.tif", type=str, help="output .tif file")
    parser.add_argument('-p', dest='png', default="vstd_scaled.png", type=str, help="output .png file")
    args = parser.parse_args()


def start():
    global start_time
    start_time = time.time()
    print("\n{} ver{} {} {}".format(os.path.basename(sys.argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(sys.argv[0]), ' '.join(sys.argv[1:])), flush=True)


def finish():
    elapsed_time = time.time() - start_time
    hour = int(elapsed_time / 3600)
    minute = int(np.mod((elapsed_time / 60), 60))
    sec = int(np.mod(elapsed_time, 60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour, minute, sec))
    print("\n{} {}".format(os.path.basename(sys.argv[0]), ' '.join(sys.argv[1:])), flush=True)
    print('Output: \n{}\n{}\n{}'.format(
        os.path.relpath(args.outfile),
        os.path.relpath(args.png),
        os.path.relpath('vstd_rescaling_parameters.txt')
    ))


class OpenTif:
    """A class that stores the band array and metadata of a GeoTIFF file."""
    def __init__(self, filename, sigfile=None, incidence=None, heading=None, N=None, E=None, U=None):
        self.ds = gdal.Open(filename)
        if self.ds is None:
            raise FileNotFoundError(f"Cannot open input file: {filename}")

        self.basename = os.path.splitext(os.path.basename(filename))[0]
        self.band = self.ds.GetRasterBand(1)
        self.data = self.band.ReadAsArray().astype(np.float64)
        self.xsize = self.ds.RasterXSize
        self.ysize = self.ds.RasterYSize
        self.left = self.ds.GetGeoTransform()[0]
        self.top = self.ds.GetGeoTransform()[3]
        self.xres = self.ds.GetGeoTransform()[1]
        self.yres = self.ds.GetGeoTransform()[5]
        self.right = self.left + self.xsize * self.xres
        self.bottom = self.top + self.ysize * self.yres
        self.projection = self.ds.GetProjection()

        pix_lin, pix_col = np.indices((self.ds.RasterYSize, self.ds.RasterXSize))
        self.lat = self.top + self.yres * pix_lin
        self.lon = self.left + self.xres * pix_col

        # convert 0 to NaN
        self.data[self.data == 0.] = np.nan


def spherical(d, p, n, r):
    """
    Compute spherical variogram model.
    d: distance array
    p: partial sill
    n: nugget
    r: range
    """
    ####limitation for large range value, Dehua Wang, 20250701
    d = np.asarray(d, dtype=float)
    r = max(float(r), 1e-6)
    return np.where(d > r, p + n, p * (1.5 * d / r - 0.5 * d**3 / r**3) + n)


def exponential(d, p, n, r):
    """
    Compute exponential variogram model.
    """
    d = np.asarray(d, dtype=float)
    r = max(float(r), 1e-6)
    return n + p * (1 - np.exp(-d * 3.0 / r))


def linear(d, p, n, r):
    """
    Compute linear variogram model.
    """
    d = np.asarray(d, dtype=float)
    r = max(float(r), 1e-6)
    return np.where(d > r, p + n, n + p * (d / r))


def define_UTM(opentif):
    """
    Define UTM zone based on the centre of the OpenTif object.
    """
    center_lat = (opentif.top + opentif.bottom) / 2.0
    center_lon = (opentif.left + opentif.right) / 2.0
    _, _, zone, _ = utm.from_latlon(center_lat, center_lon)
    UTM = pyproj.Proj(proj='utm', zone=zone)
    return UTM


def find_median_index_of_lowest_values(opentif):
    """
    Define the reference point of an uncertainty map based on the median indices
    of pixels with the lowest 1% uncertainties.
    """
    dat = opentif.data
    valid = np.isfinite(dat)
    if not np.any(valid):
        raise ValueError("Input raster contains no valid data.")

    threshold = np.nanpercentile(dat, 1)
    ref_locs = np.nonzero(dat < threshold)

    if len(ref_locs[0]) == 0:
        # fallback: absolute minimum pixel
        idx = np.nanargmin(dat)
        ref_loc = np.array(np.unravel_index(idx, dat.shape), dtype=float)
    else:
        ref_loc = np.median(ref_locs, axis=1)

    return ref_loc


def get_profile_data(tf):
    """
    Find reference point and turn sigma map to uncertainty/distance profiles
    relative to reference location.

    Returns:
        nonnan_mask: 1D boolean mask for flattened raster
        dat_nonnan: valid sigma values
        dist_nonnan: distances (km) of valid pixels from reference
    """
    tf.ref_loc = find_median_index_of_lowest_values(tf)
    ref_lat = tf.top + tf.yres * tf.ref_loc[0]
    ref_lon = tf.left + tf.xres * tf.ref_loc[1]

    UTM = define_UTM(tf)
    ref_east, ref_north = UTM(ref_lon, ref_lat)
    east, north = UTM(tf.lon, tf.lat)

    print(tf.basename)

    sig = tf.data.flatten()
    e = east.flatten()
    n = north.flatten()
    mask = np.isfinite(sig)

    dat_nonnan = sig[mask]
    e_nonnan = e[mask]
    n_nonnan = n[mask]
    dist_nonnan = np.sqrt((e_nonnan - ref_east) ** 2 + (n_nonnan - ref_north) ** 2) / 1000.0

    return mask, dat_nonnan, dist_nonnan


def calc_median_std(x, y, bin_num=50):
    """
    Calculate binned statistics (median and std) of y scatter along x axis.
    """
    median_array, binedges, _ = stats.binned_statistic(x, y, statistic='median', bins=bin_num)
    std_array, _, _ = stats.binned_statistic(x, y, statistic='std', bins=bin_num)
    bincenter_array = (binedges[:-1] + binedges[1:]) / 2.0
    return median_array, std_array, bincenter_array


def clean_binned_data(median, std, bincenters):
    """
    Remove invalid bins and ensure positive sigma for fitting.
    """
    mask = np.isfinite(median) & np.isfinite(std) & np.isfinite(bincenters)
    median = median[mask]
    std = std[mask]
    bincenters = bincenters[mask]

    if len(median) < 5:
        raise ValueError("Too few valid bins for model fitting.")

    return median, std, bincenters


def fit_model_scipy(func, dat, x, sigma, model_name):
    """
    Fit variogram model using scipy.optimize.curve_fit.
    Returns a result dictionary mimicking the key fields used later.
    """
    dat = np.asarray(dat, dtype=float)
    x = np.asarray(x, dtype=float)
    sigma = np.asarray(sigma, dtype=float)

    if len(dat) < 5:
        raise ValueError(f"Too few points to fit {model_name} model.")

    # initial guesses
    n0 = max(float(dat[0]), 1e-6)
    sill0 = max(float(dat[-1]), n0 + 1e-6)
    p0 = max(sill0 - n0, 1e-6)
    dmax = float(np.nanmax(x))
    r0 = max(float(x[len(x)//2]), 0.01)

    # bounds
    lower_bounds = [0.0, 0.0, 0.01]
    upper_bounds = [max(np.nanmax(dat) * 5.0, 10.0), max(np.nanmax(dat) * 5.0, 10.0), max(dmax * 0.95, 1.0)]

    popt, pcov = curve_fit(
        func,
        x,
        dat,
        p0=[p0, n0, r0],
        sigma=sigma,
        absolute_sigma=False,
        bounds=(lower_bounds, upper_bounds),
        maxfev=50000
    )

    best_fit = func(x, *popt)
    residual = dat - best_fit
    chisqr = np.nansum((residual / sigma) ** 2)

    result = {
        'name': model_name,
        'best_values': {'p': popt[0], 'n': popt[1], 'r': popt[2]},
        'best_fit': best_fit,
        'chisqr': chisqr,
        'pcov': pcov
    }
    return result


def try_fit_all_models(median, std, bincenters):
    """
    Try fitting spherical, exponential and linear models.
    Use progressively smaller distance windows if needed.
    """
    thresholds = [150, 120, 100]
    fitted_results = None
    used_bincenters = None
    used_median = None
    used_std = None

    last_error = None

    for th in thresholds:
        try:
            mask = bincenters < th
            bc = bincenters[mask]
            md = median[mask]
            sd = std[mask]

            md, sd, bc = clean_binned_data(md, sd, bc)

            # weight nearer points more heavily
            fit_sigma = sd + np.power(bc / max(bc), 3)
            fit_sigma = np.where(fit_sigma <= 0, np.nanmedian(fit_sigma[fit_sigma > 0]), fit_sigma)
            fit_sigma = np.where(~np.isfinite(fit_sigma), 1.0, fit_sigma)

            result_spherical = fit_model_scipy(spherical, md, bc, fit_sigma, 'spherical')
            result_exponential = fit_model_scipy(exponential, md, bc, fit_sigma, 'exponential')
            result_linear = fit_model_scipy(linear, md, bc, fit_sigma, 'linear')

            fitted_results = [result_spherical, result_exponential, result_linear]
            used_bincenters = bc
            used_median = md
            used_std = sd
            break

        except Exception as e:
            last_error = e
            continue

    if fitted_results is None:
        raise RuntimeError(f"All model fits failed. Last error: {last_error}")

    return fitted_results, used_median, used_std, used_bincenters


def choose_best_model(results):
    """
    Choose the model with the smallest chi-square.
    """
    results_sorted = sorted(results, key=lambda x: x['chisqr'])
    best = results_sorted[0]
    print(f"Choosing {best['name']} model")
    return best, best['name']


def scale_value_by_variogram_ratio(y, x, model_result, model):
    """
    Scale values of y by theoretical ratio of y at x and y at sill.
    """
    best = model_result['best_values']
    sill = best['p'] + best['n']

    if model == 'spherical':
        theoretical_y = spherical(x, best['p'], best['n'], best['r'])
    elif model == 'exponential':
        theoretical_y = exponential(x, best['p'], best['n'], best['r'])
    elif model == 'linear':
        theoretical_y = linear(x, best['p'], best['n'], best['r'])
    else:
        raise ValueError(f"Unknown model: {model}")

    theoretical_y = np.where(theoretical_y <= 0, np.nan, theoretical_y)
    scaling_factor = sill / theoretical_y
    y_scaled = y * scaling_factor
    return y_scaled


def write_output_tif(outfile, tif, new_map):
    """
    Export scaled uncertainty map to GeoTIFF format.
    """
    driver = gdal.GetDriverByName("GTiff")
    outdata = driver.Create(outfile, tif.xsize, tif.ysize, 1, gdal.GDT_Float32)
    outdata.SetGeoTransform([tif.left, tif.xres, 0, tif.top, 0, tif.yres])
    outdata.SetProjection(tif.projection)
    outband = outdata.GetRasterBand(1)
    outband.WriteArray(new_map.astype(np.float32))
    outband.SetNoDataValue(np.nan)
    outband.FlushCache()
    outdata.FlushCache()
    outdata = None


def safe_random_subset(n, max_points=50000):
    """
    Return a random subset of indices for plotting.
    """
    if n <= 1:
        return np.array([0], dtype=int)
    k = min(max(n // 2, 1), max_points)
    idx = random.sample(range(n), k)
    return np.array(idx, dtype=int)


if __name__ == "__main__":
    start()
    init_args()

    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Nimbus Sans"]

    tif = OpenTif(args.infile)

    result = None
    model = None

    try:
        # prepare profile data
        nonnan_mask, sig_nonnan, dist = get_profile_data(tif)

        if len(sig_nonnan) < 10:
            raise ValueError("Too few valid pixels in input raster.")

        # calc stats along profile
        median, std, bincenters = calc_median_std(dist, sig_nonnan)

        # fit variogram models
        results, median_used, std_used, bincenters_used = try_fit_all_models(median, std, bincenters)
        result, model = choose_best_model(results)

        # scale sig_nonnan based on variogram model
        sig_nonnan_scaled = scale_value_by_variogram_ratio(sig_nonnan, dist, result, model)

        # populate scaled uncertainty map
        new_map = np.ones(nonnan_mask.shape, dtype=float) * np.nan
        new_map[nonnan_mask] = sig_nonnan_scaled
        new_map = new_map.reshape(tif.data.shape)

        fit_scaled = scale_value_by_variogram_ratio(result['best_fit'], bincenters_used, result, model)

        # output modeling parameters
        parameters_ifgfile = 'vstd_rescaling_parameters.txt'
        model_str = (
            f"{model} "
            f"nugget={result['best_values']['n']:.3f} "
            f"sill={result['best_values']['p'] + result['best_values']['n']:.3f} "
            f"range={result['best_values']['r']:.3f}"
        )
        print(model_str)
        with open(parameters_ifgfile, 'w') as f:
            print(model_str, file=f)

        # plotting
        fig, [[ax1, ax2], [ax3, ax4]] = plt.subplots(2, 2, figsize=(6.4, 4.8))

        subset = safe_random_subset(len(dist), max_points=50000)

        vmax1 = np.percentile(sig_nonnan[subset], 95) if len(subset) > 0 else np.nanpercentile(sig_nonnan, 95)
        vmax1 = max(vmax1, 1e-6)

        ax1.scatter(
            dist[subset], sig_nonnan[subset],
            c=sig_nonnan[subset], s=0.1, vmin=0, vmax=vmax1
        )
        ax1.plot(bincenters_used, median_used, linewidth=2, c="gold")
        ax1.plot(bincenters_used, median_used + std_used, linewidth=1, c="gold")
        ax1.plot(bincenters_used, median_used - std_used, linewidth=1, c="gold")
        ax1.plot(
            bincenters_used, result['best_fit'], linewidth=2, c="red",
            label='n={:.2f}, s={:.2f}, r={:.1f}'.format(
                result['best_values']['n'],
                result['best_values']['p'] + result['best_values']['n'],
                result['best_values']['r']
            )
        )
        ax1.set_xlim((0, bincenters_used[-1]))
        ax1.set_ylim((0, min(2, np.nanmax(median_used + 3 * std_used))))
        ax1.tick_params(labelbottom=False)
        ax1.set_ylabel(r"$\sigma$(LOS), mm/yr")
        ax1.set_title("Uncertainty Profile")
        ax1.legend(loc=4)

        vmax3 = np.percentile(sig_nonnan_scaled[subset], 95) if len(subset) > 0 else np.nanpercentile(sig_nonnan_scaled, 95)
        vmax3 = max(vmax3, 1e-6)

        ax3.scatter(
            dist[subset], sig_nonnan_scaled[subset],
            c=sig_nonnan_scaled[subset], s=0.1, vmin=0, vmax=vmax3
        )
        ax3.plot(bincenters_used, fit_scaled, linewidth=2, c="red")
        ax3.set_ylim((0, vmax3))
        ax3.set_xlabel("Distance to reference, km")
        ax3.set_ylabel(r"$\sigma$(LOS), mm/yr")
        ax3.set_title("Scaled Uncertainty Profile")
        ax3.set_xlim((0, bincenters_used[-1]))

        im = ax2.imshow(tif.data, vmin=0, vmax=vmax1, interpolation='nearest')
        ax2.plot(tif.ref_loc[1], tif.ref_loc[0], marker="o", markersize=5, c='gold')
        divider = make_axes_locatable(ax2)
        cax = divider.append_axes('right', size='5%', pad=0.05)
        fig.colorbar(im, cax=cax, label="mm/yr")
        ax2.set_title("Uncertainty Map")

        im = ax4.imshow(new_map, vmin=0, vmax=vmax3, interpolation='nearest')
        divider = make_axes_locatable(ax4)
        cax = divider.append_axes('right', size='5%', pad=0.05)
        fig.colorbar(im, cax=cax, label="mm/yr")
        ax4.set_title("Scaled Uncertainty Map")
        ax4.set_xlabel(tif.basename[:17], labelpad=15)

        for ax in [ax2, ax4]:
            ax.set_xticks([])
            ax.set_yticks([])

        plt.tight_layout()
        fig.savefig(args.png, format='PNG', dpi=150, bbox_inches='tight')

        # export tif
        write_output_tif(args.outfile, tif, new_map)

    except Exception as e:
        print(f"entering exception, plot till before scaling only: {e}")

        # prepare profile data
        nonnan_mask, sig_nonnan, dist = get_profile_data(tif)
        median, std, bincenters = calc_median_std(dist, sig_nonnan)

        valid = np.isfinite(median) & np.isfinite(std) & np.isfinite(bincenters)
        median = median[valid]
        std = std[valid]
        bincenters = bincenters[valid]

        fig, [[ax1, ax2], [ax3, ax4]] = plt.subplots(2, 2, figsize=(6.4, 4.8))

        subset = safe_random_subset(len(dist), max_points=50000)
        vmax = np.percentile(sig_nonnan[subset], 95) if len(subset) > 0 else np.nanpercentile(sig_nonnan, 95)
        vmax = max(vmax, 1e-6)

        ax1.scatter(dist[subset], sig_nonnan[subset], c=sig_nonnan[subset], s=0.1, vmin=0, vmax=vmax)
        if len(bincenters) > 0:
            ax1.plot(bincenters, median, linewidth=2, c="gold")
            ax1.plot(bincenters, median + std, linewidth=1, c="gold")
            ax1.plot(bincenters, median - std, linewidth=1, c="gold")
            ax1.set_xlim((0, bincenters[-1]))
            ax1.set_ylim((0, min(2, np.nanmax(median + 3 * std))))

        ax1.tick_params(labelbottom=False)
        ax1.set_ylabel(r"$\sigma$(LOS), mm/yr")
        ax1.set_title("Uncertainty Profile")

        im = ax2.imshow(tif.data, vmin=0, vmax=vmax, interpolation='nearest')
        ax2.plot(tif.ref_loc[1], tif.ref_loc[0], marker="o", markersize=5, c='gold')
        divider = make_axes_locatable(ax2)
        cax = divider.append_axes('right', size='5%', pad=0.05)
        fig.colorbar(im, cax=cax, label="mm/yr")
        ax2.set_title("Uncertainty Map")

        ax3.axis('off')
        ax4.axis('off')

        ax2.set_xticks([])
        ax2.set_yticks([])

        plt.tight_layout()
        fig.savefig(args.png, format='PNG', dpi=150, bbox_inches='tight')

    finish()
