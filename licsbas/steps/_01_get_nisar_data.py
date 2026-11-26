#!/usr/bin/env python3
"""

=========
Overview
=========
Search and **download NISAR** Level-2 GUNW products for a geographic bounding box
from ASF (asf.alaska.edu), using the `asf_search` package. (GUNW — unwrapped
interferograms — are the only product type LiCSBAS needs; GSLC is not used.)

This is the NISAR analogue of `licsbas-01get-geotiff` (which downloads LiCSAR
data from the COMET-LiCS portal): that step is left untouched; this step is a
separate, optional NISAR data-acquisition step.

Products are grouped by NISAR *frame* id (the NISAR naming convention, i.e. the
track/frame identification, naming ``<line><pass>_<beam>``, e.g. ``018A_01234`` — computed with
``nisar_data.get_frameid``) and written to a per-frame subfolder:

    NISAR_GUNW/
        018A_01234/
            NISAR_L2_PR_GUNW_..._018_A_01234_....h5
            NISAR_L2_PR_GUNW_..._....h5
        019A_01235/...

A geographic region is usually covered by **several frames (tracks)**. Each
downloaded frame subfolder is a self-contained, independent dataset: you can
(and should) process each frame on its own — GUNW interferograms from
different frames **cannot** be combined in a single time series. Use
``--list-frames`` to inspect what is available and ``--frame`` to download
only the frame(s) you want.

The ASF download uses the ASF session (streamed over HTTP with optional user
authentication) instead of a shell `wget`. If ASF credentials exist they are
used; otherwise public (anonymous) URLs are fetched. Existing, non-empty files
are not re-downloaded.

The NISAR search/download code lives in `licsar_extra/python/nisar_data.py`
(functions `get_nisar_data`, `get_frameid`, `get_asf_session`) and
`licsar_extra/python/lics_proc_tools.py` (function `cliparea_geo2coords`).
Those are imported lazily and only used when actually downloading, so that
simply importing this module (or the rest of `licsbas`) never requires the
NISAR dependencies.

===========
Requirements
===========
  licsar_extra   (provides nisar_data + lics_proc_tools)
  asf_search, geopandas, shapely, pyproj, requests
  (install with: pip install licsar_extra[nisar])
  ASF credentials (optional) in ~/.asf_credentials or
  $LiCSAR_configpath/asf_credentials

=====
Usage
=====
licsbas-01-get-nisar-data -g lon1/lon2/lat1/lat2 [-s yyyymmdd] [-e yyyymmdd]
                           [-o outdir] [--max N] [--dry_run]

 -g  Geographic extent, LiCSBAS convention lon1/lon2/lat1/lat2 (required)
 -s  Start date yyyymmdd (Default: 20250101, first NISAR L2 releases)
 -e  End   date yyyymmdd (Default: today)
 -o  Output directory (Default: ./NISAR_GUNW)
 --frame <FID[,FID2,...]>   Download only the selected NISAR frame(s)
 --list-frames          Show the available frames + per-frame GUNW scene count, then exit
                        without downloading
 --max  Maximum number of scenes to fetch (Default: 500)
 --dry_run     Perform the ASF search and print the selection; do NOT download
"""

import os
import re
import sys
import time
import datetime as dt
import getopt

ver = "1.0.0"
date = 20261112
author = "Milan Lazecky"


class Usage(Exception):
    """Usage context manager"""
    def __init__(self, msg):
        self.msg = msg


def _parse_date(s, field):
    try:
        return dt.datetime.strptime(str(s), "%Y%m%d").date()
    except ValueError:
        raise Usage("{} must be yyyymmdd, got '{}'".format(field, s))


def _import_nisar():
    """Lazily import the NISAR helpers. Raise Usage() with a clear message
    on any missing dependency so the caller can exit cleanly."""
    try:
        import licsar_extra  # noqa: F401  (only to give a helpful hint)
    except Exception:
        pass
    try:
        import nisar_data as nd
    except ImportError:
        try:
            from licsar_extra import nisar_data as nd
        except ImportError:
            raise Usage(
                "nisar_data not found. Install licsar_extra and make its "
                "'python/' directory importable (or 'pip install licsar_extra[nisar]').")
    try:
        import lics_proc_tools as lp
    except ImportError:
        try:
            from licsar_extra import lics_proc_tools as lp
        except ImportError:
            raise Usage("lics_proc_tools not found (part of licsar_extra).")
    try:
        import requests
    except ImportError:
        raise Usage("'requests' is required to download from ASF (pip install requests).")
    return nd, lp, requests


def _first_url(prod):
    """Return a single absolute https URL for an asf_search product, whichever
    of the (version-dependent) property/attribute layouts it uses."""
    p = getattr(prod, "properties", {}) or {}
    for key in ("url", "sceneURL", "URL", "sceneUrl"):
        u = p.get(key)
        if isinstance(u, (list, tuple)) and u:
            u = u[0]
        if isinstance(u, str) and u.startswith("http"):
            return u
    for attr in ("url",):
        u = getattr(prod, attr, None)
        if isinstance(u, (list, tuple)) and u:
            u = u[0]
        if isinstance(u, str) and u.startswith("http"):
            return u
    return None


def _scene_to_filename(scene):
    """Return the on-disk name for an ASF sceneName (add .h5 if missing)."""
    s = str(scene).strip()
    return s if s.lower().endswith(".h5") else s + ".h5"


def _download_url(url, dest, session, timeout=120):
    """Stream *url* to *dest* using the (possibly authenticated) ASF session."""
    with session.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        tmp = dest + ".part"
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
    os.replace(tmp, dest)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    start = time.time()
    print("\n{} ver{} {} {}".format(os.path.basename(argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(argv[0]), ' '.join(argv[1:])), flush=True)

    #%% Default
    bbox = None            # lon1/lon2/lat1/lat2
    dtype = "GUNW"         # fixed: LiCSBAS runs only on GUNW products
    startdate = dt.date(2025, 1, 1)
    enddate = dt.date.today()
    outdir = None
    max_results = 500
    framesel = None        # --frame  FID[,FID2,...] (optional restriction)
    list_frames = False    # --list-frames: show frame inventory and exit
    dry_run = False

    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(
                argv[1:], "g:s:e:o:h",
                ["help", "max=", "dry_run", "frame=", "list-frames"])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o in ("-h", "--help"):
                print(__doc__)
                return 0
            elif o == "-g":
                bbox = a
            elif o == "-s":
                startdate = _parse_date(a, "-s")
            elif o == "-e":
                enddate = _parse_date(a, "-e")
            elif o == "-o":
                outdir = a
            elif o == "--max":
                max_results = int(a)
            elif o == "--frame":
                framesel = a
            elif o == "--list-frames":
                list_frames = True
            elif o == "--dry_run":
                dry_run = True
    except Usage as e:
        print(__doc__, file=sys.stderr)
        print("ERROR: {}".format(e.msg), file=sys.stderr)
        return 1

    if not bbox:
        print("ERROR: -g lon1/lon2/lat1/lat2 is required", file=sys.stderr)
        return 1
    if outdir is None:
        outdir = os.path.join(".", "NISAR_GUNW")

    #%% Import NISAR helpers (lazy; clear error if deps missing)
    try:
        nd, lp, requests = _import_nisar()
    except Usage as e:
        print("ERROR: " + e.msg, file=sys.stderr)
        return 2

    #%% Build WKT polygon from LiCSBAS bbox and search ASF
    try:
        wkt = lp.cliparea_geo2coords(bbox, outputaswkt=True)
    except Exception as e:
        print("ERROR: could not build WKT from -g '{}': {}".format(bbox, e), file=sys.stderr)
        return 1

    print("\nSearching ASF for {} [{} .. {}] within bbox '{}'".format(
        dtype, startdate.isoformat(), enddate.isoformat(), bbox), flush=True)
    try:
        # outAspd=False -> asf_search product collection (each has .download()
        # / properties); we also cap the result set with --max via a re-search.
        results = nd.get_nisar_data(wkt, dtype=dtype,
                                   startdate=startdate, enddate=enddate,
                                   outAspd=False)
    except Exception as e:
        print("ERROR: ASF search failed: {}".format(e), file=sys.stderr)
        return 3

    try:
        products = list(results)[:max_results]
    except TypeError:
        products = [results]

    print("  Found {} product(s) (showing first {})".format(
        len(results) if isinstance(results, (list, tuple)) else "?", len(products)), flush=True)
    if not products:
        print("  Nothing to do.", flush=True)
        return 0

    #%% Group by NISAR frame id
    frames = {}
    for prod in products:
        scene = prod.properties.get("sceneName") or getattr(prod, "sceneName", "")
        try:
            fid = nd.get_frameid(scene)
        except Exception:
            fid = "unknown"
        frames.setdefault(fid, []).append(prod)

    print("\n  {} frame(s):".format(len(frames)), flush=True)
    allfids = []
    for fid in sorted(frames):
        prods = frames[fid]
        allfids.append(fid)
        dates = sorted((p.properties.get("acquisitionTime", "") for p in prods))
        print("    {0:12}  {1:4} scene(s)   {2} .. {3}".format(
            fid, len(prods), dates[0][:10] if dates else "?", dates[-1][:10] if dates else "?"),
            flush=True)

    if list_frames:
        print("\n--list-frames: no download performed.", flush=True)
        show = ", ".join(allfids[:6]) + (" ..." if len(allfids) > 6 else "")
        print("  Download with:  --frame {}".format(show), flush=True)
        print("  (each frame is a self-contained dataset - process frames separately)", flush=True)
        return 0

    if framesel:
        wanted = [x.strip().upper() for x in re.split(r"[,:\s]+", framesel) if x.strip()]
        av = {f.strip().upper(): f for f in frames}
        chosen = [av[f] for f in wanted if f in av]
        missing = [f for f in wanted if f not in av]
        if missing:
            print("  WARNING: requested frame(s) not found in this search: {}".format(
                ", ".join(missing)), file=sys.stderr, flush=True)
        if not chosen:
            print("ERROR: none of the requested frame(s) have GUNW scenes in this search. "
                  "Available: {}".format(", ".join(sorted(av.values()))), file=sys.stderr)
            return 1
        frames = {fid: prods for fid, prods in frames.items() if fid in chosen}
        print("  -> restricting download to {} frame(s): {}".format(
            len(frames), ", ".join(sorted(frames))), flush=True)

    if dry_run:
        print("\n--dry_run: not downloading. Set a real -o and drop --dry_run to fetch.")
        print("  would write into: " + os.path.abspath(outdir))
        return 0

    #%% Download (ASF session; stream over HTTP)
    try:
        session = nd.get_asf_session()          # authenticated asf.ASFSession()
        print("\nUsing authenticated ASF session.", flush=True)
    except Exception:
        try:
            import asf_search as asf
            session = asf.ASFSession()
            print("\nNo ASF credentials found; using anonymous ASF session.", flush=True)
        except Exception as e:
            print("ERROR: could not create an ASF session: {}".format(e), file=sys.stderr)
            return 4

    outdir = os.path.abspath(outdir)
    n_ok = n_skip = n_fail = 0
    for fid, prods in sorted(frames.items()):
        fdir = os.path.join(outdir, fid)
        os.makedirs(fdir, exist_ok=True)
        for prod in prods:
            scene = prod.properties.get("sceneName") or ""
            dest = os.path.join(fdir, _scene_to_filename(scene))
            if os.path.exists(dest) and os.path.getsize(dest) > 0:
                print("  = {} (exists)".format(scene), flush=True)
                n_skip += 1
                continue
            url = _first_url(prod)
            if not url:
                print("  ! no download URL for {}".format(scene), file=sys.stderr, flush=True)
                n_fail += 1
                continue
            print("  > {}  ({} MB)".format(scene,
                  round(prod.properties.get("sizeMB", 0) or 0, 1)), flush=True)
            try:
                _download_url(url, dest, session)
                n_ok += 1
            except Exception as e:
                print("    download failed: {}".format(e), file=sys.stderr, flush=True)
                n_fail += 1

    print("\nDone in {:.1f}s: {} new, {} skipped, {} failed".format(
        time.time() - start, n_ok, n_skip, n_fail), flush=True)
    print("  output: {}".format(outdir), flush=True)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
