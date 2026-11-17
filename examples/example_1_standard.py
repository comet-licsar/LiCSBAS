#!/usr/bin/env python3
"""Example 1: **standard LiCSBAS processing chain** (v3 python batch).

This is the direct python replacement for the historical
``batch_LiCSBAS.sh`` defaults:

    01 get geotiff -> 02 ml prep -> 11 check unw -> 120 choose ref (optional)
    -> 12 loop closure -> 13 sb inversion -> 14 velocity/std
    -> 15 mask ts -> 16 filter ts

By default nothing is executed (dry run, identical to the old
``check_only="y"``); the chain is only *described* and a PNG flowchart is
written. Pass ``--execute`` to actually run the chain in-process through
the ``licsbas.steps`` package.

Usage:
    python3 examples/example_1_standard.py                 # dry run + PNG
    python3 examples/example_1_standard.py --execute       # run for real
    python3 examples/example_1_standard.py --start 11 --end 16
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
    ap.add_argument("--nlook", type=int, default=1, help="multilook factor (default 1)")
    ap.add_argument("--start-date", dest="start_date", default="",
                    help="e.g. 20141001 (step 01)")
    ap.add_argument("--end-date", dest="end_date", default="",
                    help="e.g. 20191231 (step 01)")
    ap.add_argument("--no-multi-prime", dest="multi_prime", action="store_false",
                    help="turn OFF step 12: --multi_prime (on by default)")
    ap.add_argument("--nullify", action="store_true",
                    help="step 12: --nullify")
    ap.add_argument("--out", default="flowchart_standard.png",
                    help="flowchart output path (default flowchart_standard.png)")
    a = ap.parse_args()

    # ---- chain definition: identical to the old batch_LiCSBAS.sh defaults ----
    cfg = BatchConfig(
        start_step=a.start,
        end_step=a.end,
        nlook=a.nlook,
        # n_para=None  -> use all usable CPUs
        # gpu=False
        p01_start_date=a.start_date,
        p01_end_date=a.end_date,
        p12_multi_prime=a.multi_prime,
        p12_nullify=a.nullify,
    )

    # ---- flowchart (png) ------------------------------------------------------
    png = save_flowchart(cfg, a.out, title="LiCSBAS standard processing chain (example 1)")
    print(f"\n[example1] flowchart written to: {os.path.abspath(png)}")

    # ---- (dry run by default; --execute to run for real) ----------------------
    return run_batch(cfg, dry_run=not a.execute)


if __name__ == "__main__":
    sys.exit(main() or 0)
