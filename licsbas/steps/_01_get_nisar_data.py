#!/usr/bin/env python3
"""

=========
Overview
=========
Search and **download NISAR** Level-2 products (GUNW or GSLC) for a geographic
bounding box from ASF (asf.alaska.edu), using the `asf_search` package.

This is the NISAR analogue of `licsbas-01get-geotiff` (which downloads LiCSAR
data from the COMET-LiCS portal): that step is left untouched; this step is a
separate, optional NISAR data-acquisition step.

Products are grouped by NISAR *frame* (a persistent track+frame compatibility
group) and written to a per-frame subfolder:

    NISAR_GUNW/
        18_A_01234/
            NISAR_L2_PR_GUNW_..._A_01234_....h5
            NISAR_L2_PR_GUNW_....h5
        18_A_05678/...

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
licsbas-01get-nisar-data -g lon1/lon2/lat1/lat2 [-t GUNW|GSLC]
                           [-s yyyymmdd] [-e yyyymmdd]
                           [-o outdir] [--max N] [--dry_run]

 -g  Geographic extent, LiCSBAS convention lon1/lon2/lat1/lat2 (required)
 -t  Product type: GUNW (interferograms, default) or GSLC (single looks)
 -s  Start date yyyymmdd (Default: 20250101, first NISAR L2 releases)
 -e  End   date yyyymmdd (Default: today)
 -o  Output directory (Default: ./NISAR_<type>)
 --max  Maximum number of scenes to fetch (Default: 500)
 --dry_run     Perform the ASF search and print the selection; do NOT download
"""

import os
import sys
import time
import datetime as dt
import getopt

ver = "1.0.0"
date = 20261112
author = "E. Spiritozzi (based on M. Lazecky's nisar_data)"


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
    dtype = "GUNW"
    startdate = dt.date(2025, 1, 1)
    enddate = dt.date.today()
    outdir = None
    max_results = 500
    dry_run = False

    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(
                argv[1:], "g:t:s:e:o:h",
                ["help", "max=", "dry_run"])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o in ("-h", "--help"):
                print(__doc__)
                return 0
            elif o == "-g":
                bbox = a
            elif o == "-t":
                dtype = a.upper()
            elif o == "-s":
                startdate = _parse_date(a, "-s")
            elif o == "-e":
                enddate = _parse_date(a, "-e")
            elif o == "-o":
                outdir = a
            elif o == "--max":
                max_results = int(a)
            elif o == "--dry_run":
                dry_run = True
    except Usage as e:
        print(__doc__, file=sys.stderr)
        print("ERROR: {}".format(e.msg), file=sys.stderr)
        return 1

    if not bbox:
        print("ERROR: -g lon1/lon2/lat1/lat2 is required", file=sys.stderr)
        return 1
    if dtype not in ("GUNW", "GSLC"):
        print("ERROR: -t must be GUNW or GSLC (got {})".format(dtype), file=sys.stderr)
        return 1
    if outdir is None:
        outdir = os.path.join(".", "NISAR_" + dtype)

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
    for fid, prods in sorted(frames.items()):
        dates = sorted((p.properties.get("acquisitionTime", "") for p in prods))
        print("    {0:8}  {1:3} scene(s)   {2} .. {3}".format(
            fid, len(prods), dates[0][:10] if dates else "?", dates[-1][:10] if dates else "?"),
            flush=True)

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
