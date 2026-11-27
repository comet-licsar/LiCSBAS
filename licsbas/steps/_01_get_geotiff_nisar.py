#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

=========
Overview
=========
Downloads **NISAR GUNW** (unwrapped interferogram) CSL2 products from the
Alaska Satellite Facility (ASF) for a bounding-box region and makes them
available to LiCSBAS.  GUNW (unwrapped interferograms — the
LiCSBAS-compatible product) is the only data type used; GSLC products are
not needed.  This is the NISAR counterpart of ``licsbas-01-get-geotiff``
(COMET-LiCS) / ``licsbas-01-get-geotiff-alos`` (AIST) — together ``01 Get
geotiff`` for the three data sources.

Products are streamed scene-by-scene into **one subfolder per NISAR frame
(track)** (a region is usually covered by several frames, and each frame must
be processed as its own time series).  Existing files are re-used, i.e. a
re-run downloads only what is missing.  The download goes through the ASF
session (``asf_search`` / ``requests``); nothing is hard-imported at module
load, so ``-h`` works without the ``nisar`` extras.

============
Output files
============
 - NISAR_GUNW/                        (or -o <dir>)
   - <frame_id>/                      (one folder per NISAR frame, e.g. 018A_01234)
     - <scene>.h5                     (GSL2 GUNW products, one per pair)
   (the GeoTIFF structure below is produced by the next step,
   ``licsbas-nisar2geoc``, run once per frame -> GEOC/)
 - GEOC/                              (per frame; asf2geoc-compatible layout)
   - yyyymmdd_yyyymmdd/
     - yyyymmdd_yyyymmdd.geo.unw.tif
     - yyyymmdd_yyyymmdd.geo.cc.tif
   - <sat>geo.E.tif / <sat>geo.N.tif / <sat>geo.U.tif   (written once)
   [- <sat>geo.hgt.tif]              (if DEM requested)
   - slc.mli.par                      (radar_frequency + center_time)
   - baselines
   - metadata.txt                     (center_time, radar_freq)

=====
Usage
=====
LiCSBAS01_get_geotiff_NISAR.py -g lon1/lon2/lat1/lat2 [-o NISAR_GUNW] [--max 500] [-s 20250101 -e <date>]
    (list the available frames first with --list-frames)

 -g       Bounding box lon1/lon2/lat1/lat2 (deg)
 --list-frames   List the NISAR frames (tracks) in the bbox and exit (no download)
 --frame         Download only the given frame(s) FID[,FID2,...]
 -o         Output dir for the per-frame folders (Default: NISAR_GUNW)
 --max      Max product size in MB (0 = no limit, Default: 0)
 -s/-e      Start / end date YYYYMMDD (Default: 20250101 / today)
 --dry_run  Show the plan without downloading
The full GeoTIFF chain: ``licsbas-batch --workflow nisar`` = 01getgeotiff_NISAR
-> nisar2geoc -> 02 -> 03gacos -> 04mask -> 05clip (one frame per run).
"""

import argparse
import datetime as dt
import os
import sys

ver = "1.0.0"
date = 20261112
author = "Milan Lazecky"


def _import_nisar():
    """Lazy import of the ``lisar_extra`` helpers so that ``-h`` works without
    them installed.  They are used as top-level modules (``nisar_data`` and
    ``lics_proc_tools``), see licsar_extra (comet-licsar)."""
    try:
        import lics_proc_tools
        import nisar_data as nd
    except ImportError:
        print("\nERROR: this step needs the 'nisar' dependencies "
              "(``lisar_extra``): nisar_data + lics_proc_tools.\n"
              "Install with:\n"
              "  pip install 'licsbas[nisar]'   (or git clone + pip install -e "
              "lisar_extra)", file=sys.stderr)
        raise SystemExit(2)
    return lics_proc_tools, nd


def main(argv=None):
    if argv is None:
        argv = sys.argv

    print("\n{} ver{} {} {}".format(os.path.basename(sys.argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(sys.argv[0]), ' '.join(argv[1:])), flush=True)

    #%% Parse arguments
    _doc = __doc__ or ""
    _out_section = "============\nOutput files\n============"
    if "Output files\n============" in _doc:
        _out_section += _doc.split("Output files\n============", 1)[1].split("Usage", 1)[0].split("=====", 1)[0].rstrip()

    parser = argparse.ArgumentParser(
        description="Download NISAR GUNW CSL2 scenes from ASF into one "
                    "per-frame subfolder (NISAR_GUNW/<frame>/).",
        epilog=_out_section,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-g", dest="bbox", type=str, default=None,
                        help="Bounding box lon1/lon2/lat1/lat2 (deg)")
    parser.add_argument("--list-frames", dest="list_frames", action="store_true",
                        default=False,
                        help="List the NISAR frames (tracks) in the bbox and exit "
                             "(no download)")
    parser.add_argument("--frame", dest="frames", type=str, default=None,
                        help="Download only the given NISAR frame(s): FID[,FID2,...]")
    parser.add_argument("-o", dest="outdir", type=str, default="NISAR_GUNW",
                        help="Output dir for the per-frame folders (Default: NISAR_GUNW)")
    parser.add_argument("--max", dest="max_mb", type=float, default=0.0,
                        help="Max product size in MB (0 = no limit)")
    parser.add_argument("-s", dest="startdate", type=str, default="20250101",
                        help="Start date YYYYMMDD (Default: 20250101)")
    parser.add_argument("-e", dest="enddate", type=str,
                        default=dt.date.today().strftime('%Y%m%d'),
                        help="End date YYYYMMDD (Default: today)")
    parser.add_argument("--dry_run", dest="execute", action="store_false",
                        default=True, help="Show the plan without downloading")
    # argparse treats values starting with '-' (negative bboxes like
    # '-118.4/-118.2/33.8/33.7') as options; join -g and its value explicitly.
    _a = list(argv[1:])
    _j, _i = [], 0
    while _i < len(_a):
        if _a[_i] == "-g" and _i + 1 < len(_a) and _a[_i+1].startswith("-")                 and not _a[_i+1].startswith("--") and _a[_i+1] != "-h":
            _j.append("-g=" + _a[_i+1]); _i += 2
            continue
        _j.append(_a[_i]); _i += 1

    try:
        args = parser.parse_args(_j)
    except SystemExit as e:
        # keep the conventional LiCSBAS return codes (0 ok, 1 error)
        return 1 if (e.code or 1) != 0 else 0

    if args.bbox is None:
        print("ERROR: -g (bounding box) is required.", file=sys.stderr)
        return 1

    lpt, nd = _import_nisar()

    #%% Convert bbox to WKT (lisar_extra helper)
    wkt = lpt.cliparea_geo2coords(args.bbox, outputaswkt=True)
    if "POLYGON" not in wkt:
        print("ERROR: could not convert bbox {} to WKT.".format(args.bbox),
              file=sys.stderr)
        return 1

    startd = dt.datetime.strptime(args.startdate, "%Y%m%d").date()
    endd = dt.datetime.strptime(args.enddate, "%Y%m%d").date()

    #%% Ask for the product collection (GUNW only — GSLC is not used)
    prods = nd.get_nisar_data(wkt, dtype="GUNW", startdate=startd, enddate=endd,
                              outAspd=False, shortpd=True)
    if not prods:
        print("No NISAR GUNW products found for the bounding box / dates.")
        return 1

    #%% Group by NISAR frame (track)
    frames = {}
    for p in prods:
        name = p.properties["sceneName"]
        fid = nd.get_frameid(name)
        frames.setdefault(fid, []).append(p)

    if args.list_frames:
        print("\nAvailable NISAR frames: {} frame(s), {} GUNW product(s).".format(
            len(frames), len(prods)))
        for fid in sorted(frames):
            print("  {:<14} {} product(s)".format(fid, len(frames[fid])))
        print('\nDownload a frame with:  --frame '
              "'<FID[,FID2,...]>'   (or all frames without --frame)")
        return 0

    #%% Frame selection
    if args.frames:
        sel = [f.strip() for f in args.frames.split(",") if f.strip()]
        unknown = [f for f in dict.fromkeys(sel) if f not in frames]
        if unknown:
            print("ERROR: frame(s) {} not available.".format(unknown), file=sys.stderr)
            print("Available frames: {}".format(", ".join(sorted(frames))), file=sys.stderr)
            return 1
        frames = {f: frames[f] for f in dict.fromkeys(sel)}
    if len(frames) > 1:
        print("NOTE: {} frames selected. LiCSBAS processes each frame as its own "
              "time series (run nisar2geoc per frame).".format(len(frames)),
              file=sys.stderr)

    #%% Download (existing files are reused; dry_run only reports)
    n_dl = n_skip = n_big = 0
    for fid in sorted(frames):
        for p in frames[fid]:
            name = p.properties["sceneName"]
            fn = os.path.basename(name)
            dst = os.path.join(args.outdir, fid, fn)
            if os.path.exists(dst):
                n_skip += 1
                continue
            size_mb = 0.0
            try:
                size_mb = float(p.properties.get("sizeMB", 0.0) or 0.0)
            except (TypeError, ValueError):
                size_mb = 0.0
            if args.max_mb and size_mb and size_mb > args.max_mb:
                print("  skip {}: {} MB > --max {} MB".format(fn, size_mb,
                                                              args.max_mb),
                      file=sys.stderr)
                n_big += 1
                continue
            if not args.execute:
                print("  [dry_run] would download {} -> {}/".format(fn, fid))
                n_dl += 1
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            url = p.properties.get("url") or p.properties.get("downloadURL")
            with nd.get_asf_session().get(url, stream=True) as resp:
                resp.raise_for_status()
                with open(dst, "wb") as out:
                    for chunk in resp.iter_content(chunk_size=8192 * 1024):
                        if chunk:
                            out.write(chunk)
            print("  downloaded {} -> {}/ ({} MB)".format(fn, fid, size_mb or "?"),
                  flush=True)
            n_dl += 1

    print("\nSummary: {} to download, {} already present, {} skipped (size)".format(
        n_dl, n_skip, n_big))
    if args.execute and n_dl:
        print("\nNext: run licsbas-nisar2geoc per frame:  -i {}/<frame>  -o GEOC/"
              .format(args.outdir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
