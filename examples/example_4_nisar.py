#!/usr/bin/env python3
"""Example 4: **NISAR GUNW processing chain** (v3 python batch, *experimental*).

Direct python replacement for the new NISAR route (see ``docs/05_nisar.md``
and the ``nisar`` predefined workflow):

    01-get-nisar-data (ASF search + download of NISAR CSL2 GUNW/GSLC .h5)
    -> nisar2geoc (-> GEOC layout, shared WGS-84 grid, baselines, metadata)
    -> 02 ml prep -> 11 check unw -> 120 choose ref (optional)
    -> 12 loop closure -> 13 sb inversion -> 14 velocity/std
    -> 15 mask ts -> 16 filter ts

Unlike the LiCSAR route the *data access* is by bounding box (there is no
frame id / start-end date for NISAR GUNW in the same sense).

Prereqs: the optional extras ``licsbas[nisar]`` and ``licsar_extra[nisar]``
(h5py, rasterio, rioxarray, xarray, pyproj, dask, statsmodels). The dry run
below works without them (imports are lazy).

By default nothing is executed (dry run); the chain is only *described* and a
PNG flowchart is written. Pass ``--execute`` to actually run it.

Usage:
    python3 examples/example_4_nisar.py --bbox 14.0/14.25/40.75/40.95   # dry run + PNG
    python3 examples/example_4_nisar.py --bbox ... --gslc --execute     # run for real
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from licsbas.batch import BatchConfig, run_batch, save_flowchart  # noqa: E402


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--execute", action="store_true",
                    help="actually run the chain (default: dry run / check only)")
    ap.add_argument("--bbox", "-g", default="14.00/14.25/40.75/40.95",
                    help="lon1/lon2/lat1/lat2 search area for the ASF NISAR search "
                         "(default: Campi Flegrei region)")
    ap.add_argument("--type", "-t", default="GUNW", help="GUNW (default) or GSLC")
    ap.add_argument("--gslc", action="store_true",
                    help="also download GSLC (builds E/N/U + mli in nisar2geoc)")
    ap.add_argument("--start-date", dest="start_date", default="",
                    help="start date e.g. 20250101 (optional)")
    ap.add_argument("--end-date", dest="end_date", default="",
                    help="end date e.g. 20251231 (optional)")
    ap.add_argument("--max", dest="max_n", type=int, default=0,
                    help="limit number of products (0 = all)")
    ap.add_argument("--start", type=int, default=1, help="first step (default 1)")
    ap.add_argument("--end", type=int, default=16, help="last step (default 16)")
    ap.add_argument("--nlook", type=int, default=10, help="multilook factor (default 10)")
    ap.add_argument("--no-iono", dest="no_iono", action="store_true",
                    help="nisar2geoc: do NOT remove the ionospheric ramp")
    ap.add_argument("--no-offsets", dest="no_offsets", action="store_true",
                    help="nisar2geoc: do NOT remove the range-offset ramp")
    ap.add_argument("--dem", action="store_true",
                    help="nisar2geoc: also write hgt (download DEM)")
    ap.add_argument("--cc-thre", dest="cc_thre", type=float, default=0.0,
                    help="nisar2geoc: coherence threshold (0 = default 0.5)")
    ap.add_argument("--out", default="flowchart_nisar.png",
                    help="flowchart output path (default flowchart_nisar.png)")
    a = ap.parse_args()

    # ---- chain definition: identical to the `nisar` predefined workflow ----
    cfg = BatchConfig(
        use_nisar=True,
        pNISAR_bbox=a.bbox,
        pNISAR_type=a.type,
        pNISAR_start_date=a.start_date,
        pNISAR_end_date=a.end_date,
        pNISAR_gslc=a.gslc,
        nisar2geoc_no_iono=a.no_iono,
        nisar2geoc_no_offsets=a.no_offsets,
        nisar2geoc_download_dem=a.dem,
        nlook=a.nlook,
        start_step=a.start,
        end_step=a.end,
    )
    if a.cc_thre:
        cfg.nisar2geoc_cc_thre = a.cc_thre
    if a.max_n:
        cfg.pNISAR_max = a.max_n

    # ---- flowchart (png) ------------------------------------------------------
    png = save_flowchart(cfg, a.out, title="LiCSBAS NISAR GUNW processing chain (example 4)")
    print(f"\n[example4] flowchart written to: {os.path.abspath(png)}")

    # ---- (dry run by default; --execute to run for real) ----------------------
    return run_batch(cfg, dry_run=not a.execute)


if __name__ == "__main__":
    sys.exit(main() or 0)
