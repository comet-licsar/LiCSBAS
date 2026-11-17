#!/usr/bin/env python3
"""Example 2: **re-unwrapping chain using ``LiCSBAS02to05_unwrap.py``** (v3 python batch).

Updated pipeline (the old script's ``run_reunwrapping="y"`` mode):

    01 get geotiff (also downloads pha + mli for multilooking/weighting)
    02to05 LiCSBAS02to05_unwrap.py   (02 ml prep + 03 GACOS + 04 mask + 05 clip
                                       in one re-unwrapping step)
    11 check unw -> 120 choose ref -> 12 loop closure -> 13 sb inversion
    -> 14 velocity/std -> 15 mask ts -> 16 filter ts

The 02to05 options map to the old ``p02to05_*`` settings of
``batch_LiCSBAS.sh`` (``--gacos``, ``--hgtcorr``, ``--cascade``, ``--filter``,
``--thres``, ``-g`` geo clip box, ...).

By default nothing is executed (dry run); pass ``--execute`` to run.

Usage:
    python3 examples/example_2_reunw_02to05.py
    python3 examples/example_2_reunw_02to05.py --hgtcorr --gacos --execute
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
    ap.add_argument("--start", type=int, default=1, help="first step (default 1)")
    ap.add_argument("--end", type=int, default=16, help="last step (default 16)")
    ap.add_argument("--nlook", type=int, default=20,
                    help="multilook factor for the 02to05 step (default 20 here)")
    ap.add_argument("--start-date", dest="start_date", default="", help="step 01 start date")
    ap.add_argument("--end-date", dest="end_date", default="", help="step 01 end date")
    # 02to05 specific (old p02to05_* settings)
    ap.add_argument("--reunw-gacos", dest="reunw_gacos", action="store_true",
                    help="02to05: use GACOS data if available (default: dropped)")
    ap.add_argument("--hgtcorr", action="store_true",
                    help="02to05: height correction (recommended for high, varying terrain)")
    ap.add_argument("--cascade", action="store_true",
                    help="02to05: cascade unwrapping from higher ML factors")
    ap.add_argument("--filter", default="", choices=["", "gold", "gauss", "adf"],
                    help="02to05 spatial filter (default gold)")
    ap.add_argument("--thres", default="", help="02to05 consistency threshold (default 0.35)")
    ap.add_argument("--cliparea-geo", dest="cliparea_geo", default="",
                    help="02to05 geo clip box, e.g. 130.11/131.12/34.34/34.6")
    ap.add_argument("--geocdir", default="", help="02to05 input GEOC dir (default GEOC)")
    ap.add_argument("--nullify", action="store_true", help="step 12: --nullify")
    ap.add_argument("--out", default="flowchart_reunw_02to05.png",
                    help="flowchart output path")
    a = ap.parse_args()

    # ---- chain definition: run_reunwrapping=True in the old batch script ----
    cfg = BatchConfig(
        start_step=a.start,
        end_step=a.end,
        nlook=a.nlook,
        run_reunw=True,                        # <- uses LiCSBAS02to05_unwrap.py
        p01_start_date=a.start_date,
        p01_end_date=a.end_date,
        # 02to05 options (old p02to05_*)
        p02to05_op_GEOCdir=a.geocdir,
        p02to05_gacos=a.reunw_gacos,
        p02to05_hgtcorr=a.hgtcorr,
        p02to05_cascade=a.cascade,
        p02to05_filter=a.filter,
        p02to05_thres=a.thres,
        p02to05_cliparea_geo=a.cliparea_geo,
        # step 12
        p12_multi_prime=True,
        p12_nullify=a.nullify,
    )

    # ---- flowchart (png) -----------------------------------------------------
    png = save_flowchart(cfg, a.out,
                         title="LiCSBAS re-unwrapping chain via 02to05 (example 2)")
    print(f"\n[example2] flowchart written to: {os.path.abspath(png)}")

    return run_batch(cfg, dry_run=not a.execute)


if __name__ == "__main__":
    sys.exit(main() or 0)
