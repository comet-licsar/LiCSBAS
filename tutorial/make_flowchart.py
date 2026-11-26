#!/usr/bin/env python3
"""Generate the landscape PNG flowcharts used in the tutorial notebooks.

Reads the JSON configs in ``tutorial/tutorial_cfg/`` and writes one PNG per
config (default: next to the config, named ``<config>.png`` in ``tutorial/``).

Each config is a JSON object:

    {
      "title": "...",
      "clusters": [
        {"label": "phase name",
         "steps": [
            {"name": "LiCSBAS01_get_geotiff.py",
             "details": "-f 022D_04826_121209",
             "active": true,      # false -> greyed out (optional, switched off)
             "note": "free-text",
             "alt": false}        # true -> alternative-route styling
         ]}
      ]
    }

Usage:
    python3 tutorial/make_flowchart.py            # build all configs in tutorial_cfg/
    python3 tutorial/make_flowchart.py 1_ts       # build a single config (with or without .json)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

from licsbas.flowchart import FlowStep, render_flowchart  # noqa: E402


def build(cfgdict: dict, out_png: str) -> str:
    steps = []
    for cl in cfgdict.get("clusters", []):
        for s in cl.get("steps", []):
            steps.append(FlowStep(
                name=s.get("name", "step"),
                details=s.get("details", ""),
                active=s.get("active", True),
                phase=cl.get("label", "Processing"),
                note=s.get("note", ""),
                alt=s.get("alt", False),
            ))
    # landscape by default; very long chains may set "rankdir": "TB" in the config
    return render_flowchart(steps, out_png,
                            title=cfgdict.get("title", "LiCSBAS processing chain"),
                            rankdir=cfgdict.get("rankdir", "LR"))


def main():
    cdir = os.path.join(HERE, "tutorial_cfg")
    sel = sys.argv[1:]
    built = []
    for fn in sorted(os.listdir(cdir)):
        if not fn.endswith(".json"):
            continue
        base = fn[:-5]
        if sel and base not in sel:
            continue
        cfgdict = json.load(open(os.path.join(cdir, fn)))
        out = os.path.join(HERE, fn[:-5] + ".png")
        p = build(cfgdict, out)
        print(f"[make_flowchart] {os.path.basename(fn)} -> {p}")
        built.append(p)
    if not built:
        print("nothing to build (no matching configs in tutorial_cfg/)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
