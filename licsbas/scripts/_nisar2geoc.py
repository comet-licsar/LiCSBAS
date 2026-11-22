#!/usr/bin/env python3
"""

=========
Overview
=========
Convert **NISAR L2 PR GUNW** products (HDF5, as downloaded by
``licsbas-01-get-nisar-data``) into a LiCSBAS ``GEOC/`` layout.

This is the NISAR analogue of :mod:`licsbas.scripts._asf2geoc` (which converts
ASF / other pre-processed GeoTIFFs into ``GEOC/``). The *structure* and the
``metadata.txt`` produced here are the same as ``asf2geoc``; the *difference*
is the source and the corrections:

* The source of every IFG is a NISAR GUNW ``.h5`` file.
* The unwrapped phase is corrected the way ``earthquake_responder.py`` does it:
  the smooth **ionospheric** ramp and the **range-offset** (pixel-offset) ramp
  are removed before export (``nisar_data.load_gunw(..., iono_smooth_removal=True,
  offsets_deramping=True)``), then the usual coherence-threshold mask is applied.
  A 2-D quadratic ramp is removed too, unless range-offsets were already used
  (exactly as in ``earthquake_responder.py``).
* The WGS-84 conversion / GeoTIFF export uses the **rasterio (``rio``)**
  approach of ``nisar_data.py`` (``rio.write_crs`` → ``rio.to_raster`` →
  ``gdalwarp -t_srs EPSG:4326`` with ``COMPRESS=DEFLATE -co PREDICTOR=2``),
  rather than the pure-GDAL warp used by ``asf2geoc``.
* A LiCSBAS-compliant ``baselines`` file (per-IFG perpendicular baseline, read
  by ``io_lib.read_bperp_file``) is written.
* **All** exported GeoTIFFs (unw / cc of every IFG, plus the top-level
  E / N / U, hgt, mli) are written onto a **single shared WGS-84 grid**: the
  first IFG defines the grid and every other output is forced onto it (same
  dimensions and coordinates).

============
Output files
============
 - GEOC/
   - yyyymmdd_yyyymmdd/
     - yyyymmdd_yyyymmdd.geo.unw.tif   (iono + range-offset corrected, cc-masked)
     - yyyymmdd_yyyymmdd.geo.cc.tif
   - X.geo.E.tif / X.geo.N.tif / X.geo.U.tif   (if a NISAR GSLC is supplied)
   - X.geo.hgt.tif                            (if a DEM is available / downloaded)
   - X.geo.mli.tif                            (if a NISAR GSLC amplitude is supplied)
   - baselines                                (bperp per pair — LiCSBAS standard)
   - metadata.txt                             (center_time, radar_freq)

=====
Usage
=====
``licsbas-nisar2geoc --help`` for the full list. Typical::

   licbas-nisar2geoc -i NISAR_GUNW -o GEOC
                     [-c lonmin/lonmax/latmin/latmax] [-t 0.5]
                     [-f A|B] [--no_iono] [--no_offsets] [--no_deramp_quad]
                     [-E path_to_GSLC.h5] [-D] [-n N_WORKERS] [--dry_run]

 -i  Directory containing NISAR GUNW ``.h5`` files (searched recursively), or a
     single GUNW ``.h5`` file. (required)
 -o  Target GEOC directory (default: ./GEOC)
 -c  Crop outputs to a geographic bbox (lonmin/lonmax/latmin/latmax); this also
     fixes the shared grid.
 -t  Coherence threshold for masking unw (default: 0.5)
 -f  NISAR frequency band: A (1.27e9) or B (1.2215e9). Default: A
 --no_iono         Do not remove the smooth ionospheric ramp
 --no_offsets      Do not remove the range-offset (pixel-offset) ramp
 --no_deramp_quad  Do not remove a 2-D quadratic ramp on export
 -E  NISAR GSLC ``.h5`` used for ENU (E/N/U) + amplitude (mli) top-level files
 -D  Also try to fetch a NISAR DEM for ``X.geo.hgt.tif`` (needs earthaccess)
 -n  Number of parallel workers (default: usable CPUs - 1)
 --dry_run         List the GUNW files / pairs that would be processed; don't write
"""

import os
import re
import sys
import glob
import time
import shutil
import datetime
import argparse
import multiprocessing as mp

import numpy as np
from osgeo import gdal

gdal.UseExceptions()

ver = "1.1.0"
date = 20261121
author = "E. Spiritozzi (based on asf2geoc, Y. Morishita, and licsar_extra/earthquake_responder)"

# NISAR L-band centre frequencies (mirrors licsar_extra/nisar_data.py)
NISAR_FREQ_HZ = {"A": 1270000000.0, "B": 1221500000.0}

# GeoTIFF compression used for every export (same as nisar_data.py / LiCSBAS2)
TIFF_OPTIONS = ["COMPRESS=DEFLATE", "PREDICTOR=2", "TILED=YES"]


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


# --------------------------------------------------------------------------- #
# licsar_extra (NISAR) import helpers — lazy so the module imports without the
# optional NISAR dependencies (see Hard rule 1 in .agents/skills/licsbas/SKILL.md)
# --------------------------------------------------------------------------- #
def _get_nds():
    """Return the licsar_extra ``nisar_data`` module, raising a helpful
    Usage() if it (or a hard NISAR dependency) is missing."""
    try:
        import nisar_data as nd
    except ImportError:
        try:
            from licsar_extra import nisar_data as nd
        except ImportError:
            raise Usage(
                "nisar_data (from licsar_extra) not found. "
                "Install with: pip install licsar_extra[nisar] (needs asf_search, "
                "h5py, dask, xarray, rasterio, geopandas, shapely, pyproj).")
    return nd


def _pair_from_name(name):
    """Return (yyyymmdd, yyyymmdd) for a NISAR GUNW scene name, or None."""
    b = os.path.basename(name)
    m = re.search(r"(\d{8})T\d{6}.*?(\d{8})T\d{6}", b)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"(\d{8})[_-](\d{8})", b)
    if m:
        return m.group(1), m.group(2)
    return None


def _first_time_from_name(name):
    """Time-of-day 'HH:MM:SS' of the first acquisition in a NISAR scene name
    (handles both 'T22:50:55' and 'T225055')."""
    b = os.path.basename(name)
    m = re.search(r"\d{8}T(\d{2}):(\d{2}):(\d{2})", b)
    if m:
        return m.group(1) + ":" + m.group(2) + ":" + m.group(3)
    m = re.search(r"\d{8}T(\d{2})(\d{2})(\d{2})", b)
    if m:
        return m.group(1) + ":" + m.group(2) + ":" + m.group(3)
    return None


def _center_time_seconds(first_time, second_time=None):
    """Turn a 'HH:MM:SS[.ffffff]' string into seconds since midnight (or None)."""
    def to_sec(s):
        if not s:
            return None
        s = str(s)
        if re.fullmatch(r"\d{4,6}(\.\d+)?", s):
            return float(s) % 86400
        m = re.match(r"(\d{1,2}):(\d{2}):(\d{2})(?:\.(\d+))?", s)
        if not m:
            return None
        frac = float("0." + m.group(4)) if m.group(4) else 0.0
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + frac
    t = to_sec(first_time)
    return t if t is not None else to_sec(second_time)


def _fmt_seconds(sec):
    if sec is None:
        return None
    sec = float(sec) % 86400
    h = int(sec // 3600)
    rem = sec - h * 3600
    mi = int(rem // 60)
    se = rem - mi * 60
    return "{0}:{1:02d}:{2:09.6f}".format(h, mi, se)


# --------------------------------------------------------------------------- #
# GeoTIFF grid helpers (GDAL) — used to read a reference grid and force every
# export onto the same dimensions / coordinates.
# --------------------------------------------------------------------------- #
def _tif_grid(path):
    """(west, south, east, north, nx, ny) of a GeoTIFF."""
    d = gdal.Open(path)
    gt = d.GetGeoTransform()
    nx, ny = d.RasterXSize, d.RasterYSize
    d = None
    w = gt[0]; e = gt[0] + gt[1] * nx
    n = gt[3]; s = gt[3] + gt[5] * ny
    return w, s, e, n, nx, ny


def _tiff_flags():
    return " ".join("-co " + o for o in TIFF_OPTIONS)


def _warp_wgs84(src, dst, alg="near"):
    """gdalwarp *src* to WGS84 with compression (nisar_data.py style)."""
    os.system("gdalwarp -t_srs EPSG:4326 -r {a} {f} {s} {d}".format(
        a=alg, f=_tiff_flags(), s=src, d=dst))


def _warp_to_ref(src, dst, ref, alg="near"):
    """Re-project *src* to WGS84 and force it onto the exact grid (extent + size)
    of the reference GeoTIFF *ref*, so *dst* matches *ref* in dimensions and
    coordinates."""
    w, s, e, n, nx, ny = _tif_grid(ref)
    rc = os.system("gdalwarp -t_srs EPSG:4326 -te {w} {s} {e} {n} -ts {nx} {ny} "
                   "-r {a} {f} {src} {dst}".format(
                       w=w, s=s, e=e, n=n, nx=nx, ny=ny, a=alg,
                       f=_tiff_flags(), src=src, dst=dst))
    if rc not in (0, None):
        raise RuntimeError("gdalwarp failed for {0}".format(os.path.basename(dst)))
    return dst


# --------------------------------------------------------------------------- #
# NISAR-specific: load one corrected IFG (the earthquake_responder approach)
# --------------------------------------------------------------------------- #
def _load_nisar_ifg(h5path, freq_code="A", iono=True, offsets=True):
    """Load a NISAR GUNW and apply the earthquake_responder.py corrections
    (iono + range-offset ramp removal). Returns the ``nisar_data`` xarray
    ``Dataset`` (``unw``, ``coh``, ``x``, ``y``, ``crs``, plus attrs
    ``bperp``, ``polarization``, ``unw corrections``).

    This is the *only* point that needs licsar_extra; everything downstream is
    rasterio/GDAL/numpy. Overridable in tests (no HDF5/rasterio required)."""
    nd = _get_nds()
    return nd.load_gunw(
        h5path,
        freq_code=freq_code,
        add_iono=False,
        add_offsets=False,
        offsets_deramping=bool(offsets),
        iono_smooth_removal=bool(iono),
        add_enu=False,
    )


def _prepare_corrections(ds, cc_thresh, do_quad, corrections):
    """Apply the earthquake_responder correction logic to the xarray ``unw``:
    (1) optional 2-D quadratic deramp (skipped if range-offsets were already
    removed), (2) coherence-threshold mask. Returns (ds, corrections)."""
    vals = np.asarray(ds["unw"].values, dtype=np.float64)
    if do_quad:
        valid = np.isfinite(vals) & (vals != 0)
        if int(valid.sum()) > 100:
            try:
                Y, X = np.mgrid[0:vals.shape[0], 0:vals.shape[1]]
                yv, xv = Y[valid], X[valid]
                A = np.c_[np.ones_like(xv), xv, yv, xv * xv, yv * yv, xv * yv]
                coef, *_ = np.linalg.lstsq(A, vals[valid], rcond=None)
                ramp = A @ coef
                vals[valid] = vals[valid] - ramp
                corrections = list(corrections) if corrections else []
                corrections.append("quadratic ramp removal")
            except Exception as e:
                print("    quad-deramp skipped: {0}".format(e))
    try:
        coh = np.asarray(ds["coh"].values, dtype=np.float64)
    except (KeyError, AttributeError):
        coh = np.ones_like(vals)
    bad = ~np.isfinite(coh) | (coh < cc_thresh)
    vals[bad] = 0.0
    ds["unw"].values = vals.astype(np.float32)
    return ds, corrections


def _export_ifg(ds, pair, out_geoc, cc_thresh, do_quad, tmpdir, corrections, ref=None):
    """Export one corrected IFG to ``GEOC/<pair>/<pair>.geo.{unw,cc}.tif`` using
    the nisar_data rasterio approach, on the shared grid (``ref`` if given, else
    this IFG defines the grid). Returns ``{"ifgdir", "ref", "skipped"}``."""
    import xarray as xr  # noqa: F401  (registers the rioxarray accessor)
    crs = ds.attrs.get("crs") or ds.get("crs")
    ds = _prepare_corrections(ds, cc_thresh, do_quad, corrections)

    d1, d2 = pair
    ifgdir = "{0}_{1}".format(d1, d2)
    itarget = os.path.join(out_geoc, ifgdir)
    os.makedirs(itarget, exist_ok=True)
    out_unw = os.path.join(itarget, "{0}.geo.unw.tif".format(ifgdir))
    out_cc = os.path.join(itarget, "{0}.geo.cc.tif".format(ifgdir))
    if os.path.exists(out_unw) and os.path.exists(out_cc) and ref is not None:
        print("    skip {0} (already exists)".format(ifgdir))
        return {"ifgdir": ifgdir, "ref": ref, "skipped": True}

    tmp_unw = os.path.join(tmpdir, ifgdir + ".unw.tif")
    tmp_unw_wgs = os.path.join(tmpdir, ifgdir + ".unw.wgs.tif")
    tmp_cc = os.path.join(tmpdir, ifgdir + ".coh.tif")
    tmp_cc_wgs = os.path.join(tmpdir, ifgdir + ".coh.wgs.tif")

    # rasterio export in the source (UTM) CRS  (nisar_data.py style)
    ds["unw"] = ds["unw"].rio.write_crs(crs)
    ds["unw"].rio.to_raster(tmp_unw)
    if "coh" in ds:
        ds["coh"] = ds["coh"].rio.write_crs(crs)
        ds["coh"].rio.to_raster(tmp_cc)
    else:
        tmp_cc = tmp_unw

    # WGS84 re-projection
    _warp_wgs84(tmp_unw, tmp_unw_wgs, alg="near")
    _warp_wgs84(tmp_cc, tmp_cc_wgs, alg="average")

    if ref is None:
        # this IFG defines the shared grid
        os.replace(tmp_unw_wgs, out_unw)
        _warp_to_ref(tmp_cc_wgs, out_cc, out_unw, alg="average")
        final_ref = out_unw
    else:
        _warp_to_ref(tmp_unw_wgs, out_unw, ref, alg="near")
        _warp_to_ref(tmp_cc_wgs, out_cc, ref, alg="average")
        final_ref = ref

    print("    wrote {0} / {1}".format(os.path.basename(out_unw), os.path.basename(out_cc)))
    return {"ifgdir": ifgdir, "ref": final_ref, "skipped": False}


# --------------------------------------------------------------------------- #
# Per-IFG worker
# --------------------------------------------------------------------------- #
def _process_one(args):
    (h5path, out_geoc, cc_thresh, freq_code,
     do_iono, do_offsets, do_deramp_quad, tmpdir, ref) = args
    pair = _pair_from_name(h5path)
    rec = {"h5": h5path, "pair": pair, "ok": False}
    if pair is None:
        print("  ! could not parse a pair from {0}; skip".format(os.path.basename(h5path)))
        return rec

    d1, d2 = pair
    if int(d2) < int(d1):
        d1, d2 = d2, d1
    pair = (d1, d2)

    print("  processing {0}".format(os.path.basename(h5path)))
    ds = _load_nisar_ifg(h5path, freq_code=freq_code, iono=do_iono, offsets=do_offsets)
    corrections = list(ds.attrs.get("unw corrections", []))
    do_quad = do_deramp_quad and ("range offsets" not in corrections)

    exp = _export_ifg(ds, pair, out_geoc, cc_thresh, do_quad, tmpdir,
                      corrections, ref=ref)

    try:
        btemp = abs((datetime.datetime.strptime(d2, "%Y%m%d")
                     - datetime.datetime.strptime(d1, "%Y%m%d")).days)
    except Exception:
        btemp = 0

    rec.update(ok=True, ifgdir=exp["ifgdir"], d1=d1, d2=d2,
               bperp=float(ds.attrs.get("bperp", float("nan"))),
               btemp=btemp,
               polarization=ds.attrs.get("polarization"),
               freq_code=ds.attrs.get("freq", freq_code),
               corrections=corrections,
               ref=exp.get("ref"),
               first_time=_first_time_from_name(h5path))
    return rec


# --------------------------------------------------------------------------- #
# Top-level files + baselines + metadata.txt  (same layout as asf2geoc)
# --------------------------------------------------------------------------- #
def _write_baselines(out_geoc, records):
    """Write the LiCSBAS ``baselines`` file (new format: smdate sdate bp dt)."""
    bpfile = os.path.join(out_geoc, "baselines")
    rows = set()
    for r in records:
        if not r.get("ok"):
            continue
        d1, d2 = r.get("d1"), r.get("d2")
        if d1 and d2 is not None:
            rows.add((d1, d2, float(r.get("bperp", 0.0) or 0.0),
                      int(r.get("btemp", 0) or 0)))
    rows = sorted(rows, key=lambda t: (t[0], t[1]))
    with open(bpfile, "w") as f:
        for (d1, d2, bperp, btemp) in rows:
            f.write("{0} {1} {2:.4f} {3:.1f}\n".format(d1, d2, bperp, btemp))
    return len(rows)


def _xr_to_tif_on_grid(xrvar, crs, dst, ref, tmpdir, tag, alg="near"):
    """Export an xarray data variable (UTM) to WGS84 on the exact grid of *ref*
    (nisar_data rasterio approach + gdalwarp + TIFF compression)."""
    import xarray as xr  # noqa: F401
    tmp = os.path.join(tmpdir, tag + ".tif")
    xrvar = xrvar.rio.write_crs(crs)
    xrvar.rio.to_raster(tmp)
    _warp_wgs84(tmp, os.path.join(tmpdir, tag + ".wgs.tif"), alg=alg)
    _warp_to_ref(os.path.join(tmpdir, tag + ".wgs.tif"), dst, ref, alg=alg)
    return dst


def _write_enu(out_geoc, gslc_h5, ref, tmpdir):
    """Best-effort E/N/U from a NISAR GSLC (nisar_data.get_ENU), on the shared grid."""
    if not gslc_h5 or not os.path.exists(gslc_h5):
        print("  no GSLC provided; skipping E/N/U top-level files (-E ...)")
        return False
    nd = _get_nds()
    enu = nd.get_ENU(gslc_h5)
    crs = enu.attrs.get("crs")
    wrote = False
    for dv in ("E", "N", "U"):
        if dv not in enu.data_vars:
            continue
        dst = os.path.join(out_geoc, "X.geo.{0}.tif".format(dv))
        if os.path.exists(dst):
            wrote = True
            continue
        _xr_to_tif_on_grid(enu[dv], crs, dst, ref, tmpdir, "enu_" + dv)
        print("  wrote {0}".format(os.path.basename(dst)))
        wrote = True
    return wrote


def _write_mli(out_geoc, gslc_h5, ref, tmpdir):
    """Best-effort amplitude/MLI from a NISAR GSLC, on the shared grid."""
    dst = os.path.join(out_geoc, "X.geo.mli.tif")
    if not gslc_h5 or not os.path.exists(gslc_h5) or os.path.exists(dst):
        return False
    try:
        nd = _get_nds()
        slc = nd.load_gslc(gslc_h5, freq_code="A", polarization="HH")
        crs = slc.attrs.get("crs")
        for dv in slc.data_vars:
            if dv in ("amp", "magnitude", "amplitude", "intensity"):
                _xr_to_tif_on_grid(slc[dv], crs, dst, ref, tmpdir, "mli")
                print("  wrote {0}".format(os.path.basename(dst)))
                return True
    except Exception as e:
        print("  MLI/amp skipped: {0}".format(e))
    return False


def _write_hgt(out_geoc, ref, wsen):
    """Best-effort DEM (needs earthaccess + network), on the shared grid."""
    dst = os.path.join(out_geoc, "X.geo.hgt.tif")
    if os.path.exists(dst):
        return True
    if not wsen:
        print("  no DEM; skipping X.geo.hgt.tif")
        return False
    try:
        nd = _get_nds()
        raw = os.path.join(out_geoc, "_dem_raw.tif")
        nd.get_nisar_dem(wsen, outfile=raw, tmpfolder=os.path.join(out_geoc, "_dem_tmp"))
        _warp_to_ref(raw, dst, ref, alg="average")
        return True
    except Exception as e:
        print("  DEM download skipped: {0}".format(e))
        return False


def _write_metadata(out_geoc, records, freq_code):
    """Write metadata.txt in the asf2geoc style: center_time + radar_freq."""
    center_time = None
    for r in records:
        if r.get("ok") and r.get("first_time"):
            tsec = _center_time_seconds(r["first_time"])
            if tsec is not None:
                center_time = _fmt_seconds(tsec)
                break
    if center_time is None:
        center_time = "11:30:00.000000"
        print("  WARN: centre time not derivable; using nominal 11:30:00")
    radar_freq = NISAR_FREQ_HZ.get(freq_code, NISAR_FREQ_HZ["A"])
    lines = [
        "center_time={0}".format(center_time),
        "radar_freq={0:.6e}".format(radar_freq),
    ]
    metadata = os.path.join(out_geoc, "metadata.txt")
    with open(metadata, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return metadata


def _wgs84_bounds_from_geoc(out_geoc):
    """(west, south, east, north) of the first WGS84 unw GeoTIFF (for DEM)."""
    hits = sorted(glob.glob(os.path.join(out_geoc, "*", "*.geo.unw.tif")))
    if not hits:
        return None
    try:
        w, s, e, n, nx, ny = _tif_grid(hits[0])
        return (w, s, e, n)
    except Exception:
        return None


def _establish_ref(h5path, out_geoc, cc_thresh, freq_code, do_iono, do_offsets,
                   do_deramp_quad, tmpdir):
    """Process the first IFG to establish the shared grid; return its ref path
    (or None on failure)."""
    rec = _process_one((h5path, out_geoc, cc_thresh, freq_code,
                        do_iono, do_offsets, do_deramp_quad, tmpdir, None))
    return (rec.get("ref") if rec.get("ok") else None), rec


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(indir=".", outdir="GEOC", crop_geo=None, cc_thresh=0.5,
         freq_code="A", iono=True, offsets=True, deramp_quad=True,
         gslc_h5=None, download_dem=False, n_workers=None, dry_run=False):

    indir = os.path.abspath(indir)
    if os.path.isfile(indir):
        if indir.lower().endswith(".h5"):
            h5files = [indir]
        else:
            raise Usage("-i must be a NISAR GUNW .h5 file or a directory")
    elif os.path.isdir(indir):
        h5files = sorted(glob.glob(os.path.join(indir, "**", "*GUNW*.h5"), recursive=True))
        if not h5files:
            h5files = sorted(glob.glob(os.path.join(indir, "**", "*.h5"), recursive=True))
    else:
        raise Usage("-i path does not exist: {0}".format(indir))

    if not h5files:
        raise Usage("no NISAR GUNW .h5 files found under {0}".format(indir))

    unique = []
    seen = set()
    for h in h5files:
        ab = os.path.abspath(h)
        if ab not in seen:
            seen.add(ab)
            unique.append(ab)
    h5files = unique

    out_geoc = os.path.abspath(outdir)
    os.makedirs(out_geoc, exist_ok=True)

    if isinstance(crop_geo, str):
        parts = crop_geo.split("/")
        if len(parts) != 4:
            raise Usage("crop_geo must be lonmin/lonmax/latmin/latmax")
        crop_geo = tuple(float(v) for v in parts)
    print("\n{0}: found {1} NISAR GUNW product(s)".format(os.path.basename(out_geoc), len(h5files)))
    for h in h5files:
        p = _pair_from_name(h)
        print("    {0}   ({1})".format(os.path.basename(h), p[0] + "_" + p[1] if p else "??"))

    if dry_run:
        print("\n--dry_run: not writing anything. Drop --dry_run to convert.")
        print("  would write into: " + out_geoc)
        return 0

    tmpdir = os.path.join(out_geoc, "_nisar_tmp")
    os.makedirs(tmpdir, exist_ok=True)

    # 1) first IFG establishes the shared grid
    ref, rec0 = _establish_ref(h5files[0], out_geoc, cc_thresh, freq_code,
                               iono, offsets, deramp_quad, tmpdir)
    records = [rec0]
    if ref is None:
        print("\nERROR: could not process the first product; aborting.")
        return 1

    # 2) remaining IFGs on the same grid (parallel if >1)
    rest = h5files[1:]
    if rest:
        if (n_workers is not None and n_workers > 1) and len(rest) > 1:
            ctx = mp.get_context("fork")
            wl = min(len(rest), int(n_workers))
            args_list = [(h, out_geoc, cc_thresh, freq_code, iono, offsets,
                          deramp_quad, tmpdir, ref) for h in rest]
            with ctx.Pool(wl) as pool:
                records += pool.map(_process_one, args_list)
        else:
            for h in rest:
                records.append(_process_one((h, out_geoc, cc_thresh, freq_code,
                                             iono, offsets, deramp_quad, tmpdir, ref)))

    n_ok = sum(1 for r in records if r.get("ok"))
    print("\nunw/cc done: {0}/{1} IFG(s) processed".format(n_ok, len(records)))

    # 3) top-level files (all on the shared grid) + baselines + metadata.txt
    nbl = _write_baselines(out_geoc, records)
    print("wrote baselines ({0} pair(s))".format(nbl))
    _write_enu(out_geoc, gslc_h5, ref, tmpdir)
    if download_dem:
        _write_hgt(out_geoc, ref, _wgs84_bounds_from_geoc(out_geoc))
    _write_mli(out_geoc, gslc_h5, ref, tmpdir)
    _write_metadata(out_geoc, records, freq_code)

    shutil.rmtree(tmpdir, ignore_errors=True)
    print("\nGEOC layout written to: " + out_geoc)
    return 0


def cli_main(argv=None):
    if argv is None:
        argv = sys.argv
    prog = os.path.basename(argv[0]) if argv else "nisar2geoc"
    print("\n{0} ver{1} {2} {3}".format(prog, ver, date, author))
    print("{0} {1}\n".format(prog, " ".join(argv[1:])))

    p = argparse.ArgumentParser(
        description="Convert NISAR L2 PR GUNW .h5 files into a LiCSBAS GEOC/ layout "
                    "(iono + range-offset corrected; rasterio WGS84 export; writes baselines, "
                    "E/N/U, hgt, mli, metadata.txt — all on one shared grid)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("-i", "--indir", default=".", help="NISAR GUNW .h5 file or directory (recursive)")
    p.add_argument("-o", "--outdir", default="GEOC", help="Target GEOC directory")
    p.add_argument("-c", "--crop", default=None, help="Crop: lonmin/lonmax/latmin/latmax")
    p.add_argument("-t", "--cc", type=float, default=0.5, help="Coherence threshold to mask unw")
    p.add_argument("-f", "--freq", default="A", choices=["A", "B"], help="NISAR frequency band")
    p.add_argument("--no_iono", action="store_true", help="Do not remove the smooth iono ramp")
    p.add_argument("--no_offsets", action="store_true", help="Do not remove the range-offset ramp")
    p.add_argument("--no_deramp_quad", action="store_true", help="Do not remove a 2-D quadratic ramp")
    p.add_argument("-E", "--gslc", default=None, help="NISAR GSLC .h5 for E/N/U + mli")
    p.add_argument("-D", "--download_dem", action="store_true", help="Try to fetch a NISAR DEM")
    p.add_argument("-n", "--n_workers", type=int, default=None, help="Parallel workers")
    p.add_argument("--dry_run", action="store_true", help="List products; do not write")
    a = p.parse_args(argv[1:])

    return main(
        indir=a.indir, outdir=a.outdir, crop_geo=a.crop, cc_thresh=a.cc,
        freq_code=a.freq, iono=not a.no_iono, offsets=not a.no_offsets,
        deramp_quad=not a.no_deramp_quad, gslc_h5=a.gslc,
        download_dem=a.download_dem, n_workers=a.n_workers, dry_run=a.dry_run)


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(cli_main())
