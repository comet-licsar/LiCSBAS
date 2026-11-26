#!/usr/bin/env python3
"""Example 3: **SBOI processing chain** using the ``--sbovl`` options (v3 python batch).

SBOI (SBoi: sBoVl-based inversion of LiCSAR data) chain, i.e. the old
``batch_LiCSBAS.sh`` with ``sbovl="y"``. The difference to the standard
chain:

  * ``--sbovl`` is passed to steps 01, 02, 11, 13, 15, 16 (and 131 corrections);
  * step 120 (choose reference) is used automatically and step 12 is *skipped*
    (sbovl data is referenced in a different way);
  * step 13 runs the sbovl inversion (mm + coherence values);
  * optionally ``--sbovl-abs`` (old ``sbovl_abs="y"``): closes the referencing
    in steps 12/13/16, adds ICC+ESD offset and applies absolute SET/Iono
    corrections via ``LiCSBAS131_boi_absolute.py``.

By default nothing is executed (dry run); pass ``--execute`` to run.

Usage:
    python3 examples/example_3_sbovl.py
    python3 examples/example_3_sbovl.py --abs --tide --iono --execute
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
    ap.add_argument("--nlook", type=int, default=10,
                    help="multilook factor (default 10 for sbovl here)")
    ap.add_argument("--start-date", dest="start_date", default="", help="step 01 start date")
    ap.add_argument("--end-date", dest="end_date", default="", help="step 01 end date")
    ap.add_argument("--abs", action="store_true",
                    help="sbovl_abs chain: close referencing, ICC+ESD + absolute corr (SBOI abs)")
    ap.add_argument("--tide", action="store_true", help="post-13 tide correction")
    ap.add_argument("--iono", action="store_true", help="post-13 iono correction")
    ap.add_argument("--gacos", action="store_true", help="post-13 GACOS correction")
    ap.add_argument("--nullify", action="store_true",
                    help="step 12: --nullify (not used when sbovl is active)")
    ap.add_argument("--out", default="flowchart_sbovl.png",
                    help="flowchart output path")
    a = ap.parse_args()

    # ---- chain definition: sbovl="y" in the old batch script ---------------
    cfg = BatchConfig(
        start_step=a.start,
        end_step=a.end,
        nlook=a.nlook,
        sbovl=True,                            # <- the --sbovl chain
        sbovl_abs=a.abs,                       # old sbovl_abs="y"
        p01_start_date=a.start_date,
        p01_end_date=a.end_date,
        p01_get_iono=True,                     # needed for the iono correction
        p01_get_tides=True,                    # needed for the tide correction
        p120_use=True,                         # forced by sbovl (automatic)
        p12_nullify=a.nullify,
        # post-13 corrections
        p131_tide=a.tide,
        p131_iono=a.iono,
        p131_gacos=a.gacos,
        p131_sbovl_model=True,                 # use RANSAC model directly (default 'y')
    )

    # ---- flowchart (png) -----------------------------------------------------
    png = save_flowchart(cfg, a.out,
                         title="LiCSBAS SBOI chain (--sbovl options, example 3)")
    print(f"\n[example3] flowchart written to: {os.path.abspath(png)}")

    return run_batch(cfg, dry_run=not a.execute)


if __name__ == "__main__":
    sys.exit(main() or 0)
