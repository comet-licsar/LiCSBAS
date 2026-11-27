#!/usr/bin/env python3
"""
Phase bias correction (02op, optional)
======================================

Wrapper for the standalone ``phasebias`` package
(https://github.com/comet-licsar/InSAR_PhaseBias_Correction, pip name
``insar-phasebias``), which estimates and corrects temporal phase biases
using the loop-closure (phase network) method.

The correction operates on the wrapped interferogram stack
(``geo.diff_pha.tif`` + ``geo.cc.tif`` per pair) and writes the corrected
interferograms to ``out/GEOC/<pair>/<pair>.geo.diff_pha.tif`` (+ ``.geo.cc.tif``).

Steps executed (sequentially, in separate processes):

  1. phasebias-01-read-data          read ifgs + coherence, write pickles
  2. phasebias-02-loop-closures      compute loop closures
  3. phasebias-03-calibration-pars   estimate a1, a2 (+ plots, saved as PNGs)
  4. phasebias-04-inversion          invert for phase biases
  5. phasebias-05-correction         apply the correction, write GeoTIFFs

=====
Usage
=====

    LiCSBAS02op_phasebias.py -i in_dir -o out_dir [options]

 -i  Path to the directory containing the interferograms
     (e.g. <frame>/interferograms, i.e. the phasebias ``root_path``)
 -o  Output directory (phasebias ``output_path``)

Options (default in parentheses, overridable as in the standalone tool):
 --config path   Use an existing phasebias config.txt instead of generating one
 --frame name    LiCSAR frame (default: basename of -i's parent dir)
 --start date    First acquisition date, yyyymmdd (default: derived from the
                 first date of the first pair in -i, e.g. first pair
                 20200505_20210101 -> start 20200505)
 --end date      Last acquisition date, yyyymmdd (default: derived from the
                 last date of the last pair in -i, e.g. last pair
                 20241230_20250120 -> end 20250120)
 --interval n    Interferogram time span (days; default: 6)
 --nlook n       Multilooking factor (default: 1)
 --coh-thresh f  Coherence threshold (default: 0.5)
 --num_a n       Number of a-coefficients (default: 2)
 --estimate_an yes|no   Estimate a1, a2 from data (default: yes)
 --LiCSAR_data yes|no   Apply LiCSAR a-coefficients to long baselines (default: yes)
 --filtered_ifgs yes|no Include only ifgs meeting coherence criterion (default: yes)
 --landmask 0|1         Apply landmask (default: 1)
 --uncor_only 0|1       1: skip correction, only identify (default: 0)
 --steps 1,2,3,4,5  Which of the five steps to run (default: all)
 --dry-run        Print the steps that would be run, without running them

The standalone ``phasebias`` package must be installed in the same Python
environment, e.g.::

    pip install git+https://github.com/comet-licsar/InSAR_PhaseBias_Correction.git

=====
"""
import argparse
import os
import subprocess
import sys

STEPS = [
    (1, "phasebias-01-read-data", "PhaseBias_01: read data (interferograms + coherence)"),
    (2, "phasebias-02-loop-closures", "PhaseBias_02: compute loop closures"),
    (3, "phasebias-03-calibration-pars", "PhaseBias_03: estimate calibration coefficients"),
    (4, "phasebias-04-inversion", "PhaseBias_04: invert for phase biases"),
    (5, "phasebias-05-correction", "PhaseBias_05: apply correction and write GeoTIFFs"),
]

CONFIG_TEMPLATE = """[DEFAULT]
root_path = {root_path}
output_path = {output_path}
LiCSAR_data={LiCSAR_data}
filtered_ifgs={filtered_ifgs}
frame={frame}
landmask={landmask}
start={start}
end={end}
interval={interval}
nlook={nlook}

coherence_threshold={coh_thresh}
uncorrected_only={uncor_only}
num_a={num_a}
estimate_an_values={estimate_an}
"""


def _derive_dates_from_pairs(dirpath):
    """Derive (start, end) acquisition dates from the interference-pair names
    found in *dirpath* (GEOC-style layout: pair subfolders and/or
    ``<pair>.<ext>`` files named ``yyyymmdd_yyyymmdd...``).

    start = first date of the first (earliest) pair
    end   = last date of the last (latest) pair

    Returns ``(start, end, n_pairs)`` or ``(None, None, 0)`` if no pair-like
    names are present.
    """
    import re
    pairs = set()
    try:
        names = os.listdir(dirpath)
    except OSError:
        return None, None, 0
    for name in names:
        m = re.match(r"^(\d{8})_(\d{8})", name)
        if m:
            pairs.add((m.group(1), m.group(2)))
    if pairs:
        pairs = sorted(pairs)
        return pairs[0][0], pairs[-1][1], len(pairs)
    # one level deeper (e.g. in_dir/interferograms/<pair>/...)
    found = None
    for name in names:
        sub = os.path.join(dirpath, name)
        if not os.path.isdir(sub):
            continue
        found2 = _derive_dates_from_pairs(sub)
        if found2[0] is not None:
            if found is None or found2[2] > found[2]:
                found = found2
    return found if found else (None, None, 0)


def parse_args(argv):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--in_dir", required=True,
                    help="Path to the interferograms directory (phasebias root_path)")
    ap.add_argument("-o", "--out_dir", required=True, help="Output directory")
    ap.add_argument("--config", default=None,
                    help="Existing phasebias config.txt to use (overrides all other options)")
    ap.add_argument("--frame", default=None, help="LiCSAR frame")
    ap.add_argument("--start", default=None,
                    help="First acquisition date (yyyymmdd); default: derived from the "
                         "first date of the first pair in -i")
    ap.add_argument("--end", default=None,
                    help="Last acquisition date (yyyymmdd); default: derived from the "
                         "last date of the last pair in -i")
    ap.add_argument("--interval", type=int, default=6, help="Interferogram span (days)")
    ap.add_argument("--nlook", type=int, default=1, help="Multilooking factor")
    ap.add_argument("--coh-thresh", type=float, default=0.5, help="Coherence threshold")
    ap.add_argument("--num_a", type=int, default=2, help="Number of a-coefficients")
    ap.add_argument("--estimate_an", default="yes", choices=["yes", "no"],
                    help="Estimate a1, a2 from data")
    ap.add_argument("--LiCSAR_data", default="yes", choices=["yes", "no"],
                    help="Apply LiCSAR a-coefficients to long baselines")
    ap.add_argument("--filtered_ifgs", default="yes", choices=["yes", "no"],
                    help="Use only interferograms meeting the coherence criterion")
    ap.add_argument("--landmask", default="1", choices=["0", "1"], help="Apply landmask")
    ap.add_argument("--uncor_only", default="0", choices=["0", "1"],
                    help="1: only identify which ifgs are to be corrected")
    ap.add_argument("--steps", default="1,2,3,4,5",
                    help="Comma-separated list of steps to run (default: 1,2,3,4,5)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the steps that would be run, then exit")
    return ap.parse_args(argv)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    # accept both `main()`, `main(["prog", ...])` and `main(["-i", ...])`
    if argv and not argv[0].startswith("-") and len(argv) > 1:
        argv = argv[1:]
    args = parse_args(argv)

    try:
        import phasebias  # noqa: F401
    except ImportError:
        print("ERROR: the 'phasebias' package is not installed in this environment.",
              file=sys.stderr)
        print("Install it with e.g.:", file=sys.stderr)
        print("  pip install git+https://github.com/comet-licsar/InSAR_PhaseBias_Correction.git",
              file=sys.stderr)
        return 1

    in_dir = os.path.abspath(args.in_dir)
    out_dir = os.path.abspath(args.out_dir)
    if not os.path.isdir(in_dir):
        print(f"ERROR: in_dir does not exist: {in_dir}", file=sys.stderr)
        return 1
    os.makedirs(out_dir, exist_ok=True)

    frame = args.frame or os.path.basename(os.path.dirname(in_dir))
    if not frame:
        frame = os.path.basename(in_dir)

    # start/end: explicit values win; otherwise derive from the pair list in -i
    start, end = args.start, args.end
    if args.config is None:
        if not start or not end:
            d_start, d_end, n_pairs = _derive_dates_from_pairs(in_dir)
            if d_start is None:
                print("ERROR: could not find pair folders/files (yyyymmdd_yyyymmdd) in "
                      f"{in_dir}; cannot derive start/end dates. "
                      "Use --start/--end (or --config) to specify them.", file=sys.stderr)
                return 1
            print(f"Derived start/end from {n_pairs} pair(s) in {in_dir}")
        if not start:
            start = d_start
        if not end:
            end = d_end
        print(f"  start={start}  end={end}")

    if args.config:
        config_path = os.path.abspath(args.config)
        if not os.path.isfile(config_path):
            print(f"ERROR: --config file not found: {config_path}", file=sys.stderr)
            return 1
    else:
        config_path = os.path.join(out_dir, "phasebias_config.txt")
        with open(config_path, "w") as f:
            f.write(CONFIG_TEMPLATE.format(
                root_path=in_dir + os.sep,
                output_path=out_dir,
                LiCSAR_data=args.LiCSAR_data,
                filtered_ifgs=args.filtered_ifgs,
                frame=frame,
                landmask=args.landmask,
                end=end,
                start=start,
                interval=args.interval,
                nlook=args.nlook,
                coh_thresh=args.coh_thresh,
                uncor_only=args.uncor_only,
                num_a=args.num_a,
                estimate_an=args.estimate_an,
            ))
        print(f"Generated phasebias config: {config_path}")

    try:
        steps = sorted({int(s) for s in args.steps.split(",") if s.strip()})
    except ValueError:
        print("ERROR: --steps must be a comma-separated list of 1-5", file=sys.stderr)
        return 1
    unknown = [s for s in steps if s not in (1, 2, 3, 4, 5)]
    if unknown:
        print(f"ERROR: invalid step(s) in --steps: {unknown}", file=sys.stderr)
        return 1

    selected = [s for s in STEPS if s[0] in steps]
    workdir = os.path.dirname(config_path)

    print("\nPhase bias correction — %d step(s) to run" % len(selected))
    for num, cmd, desc in selected:
        print(f"  [{num}] {cmd}  ({desc})")
    if args.dry_run:
        return 0

    # Run each step in the directory containing the config file, as a
    # subprocess, so failures do not corrupt in-process state.
    for num, cmd, desc in selected:
        print(f"\n===== Step {num}/5: {desc} =====")
        proc = subprocess.run([cmd], cwd=workdir)
        if proc.returncode != 0:
            print(f"\nERROR: step {num} ({cmd}) failed "
                  f"(exit code {proc.returncode}). Aborting.", file=sys.stderr)
            print("Re-run with --steps %d,... to resume from this step." % num,
                  file=sys.stderr)
            return proc.returncode

    print("\nPhase bias correction completed successfully.")
    print(f"Corrected interferograms: {os.path.join(out_dir, 'GEOC')}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
