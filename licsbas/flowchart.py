"""Flowchart generation for LiCSBAS processing chains.

Renders a processing chain (e.g. the steps planned by :mod:`licsbas.batch`)
to a PNG file using the Graphviz ``dot`` binary (install ``graphviz`` from
your package manager; no Python-level dependency is required).
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from typing import List

__all__ = ["FlowStep", "render_flowchart", "save_flowchart"]


@dataclass
class FlowStep:
    """One node of the chain.

    name:    display name of the step script, e.g. ``LiCSBAS12_loop_closure.py``
    details: small annotation shown under the name (key options, ...)
    active:  False marks an optional step that is switched off (drawn grey)
    phase:   phase name for clustering, e.g. "Pre-processing (01-06)"
    note:    free-text note, e.g. "re-run on failure if step 12 nullified"
    """

    name: str
    details: str = ""
    active: bool = True
    phase: str = ""
    note: str = ""


def _shquote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _dot_source(steps: List[FlowStep], title: str) -> str:
    lines = [
        "digraph licsbas {",
        "  rankdir=TB;",
        f"  label={_shquote(title)};",
        "  labelloc=t;",
        '  fontname="Helvetica";',
        '  node [shape=box, fontname="Helvetica", fontsize=11,',
        '        style="filled,rounded", fillcolor="#e8f0fe", color="#345a8d"];',
        '  edge [color="#5b7b9e", arrowsize=0.8];',
    ]

    # cluster steps by phase, preserving first-appearance order
    phases: list = []
    for s in steps:
        p = s.phase or "Processing"
        if p not in phases:
            phases.append(p)

    # node ids are assigned in global order, per phase
    n = 0
    for ci, p in enumerate(phases):
        members = [s for s in steps if (s.phase or "Processing") == p]
        lines.append(f"  subgraph cluster_{ci} {{")
        lines.append(f"    label={_shquote(p)};")
        lines.append('    fontsize=13; color="#8aa4c4"; style="rounded";')
        for s in members:
            nid = f"n{n}"
            n += 1
            text = [s.name]
            if s.details:
                text.append(s.details)
            if not s.active:
                text.append("(optional - switched off)")
            if s.note:
                text.append(f"note: {s.note}")
            lines.append(f"    {nid} [label={_shquote(chr(10).join(text))};")
            if s.active:
                lines.append(f'      fontcolor="#1a2e4a"];')
            else:
                lines.append(f'      fontcolor="#8a8f98"; fillcolor="#f2f3f5";')
                lines.append('      color="#b6bac2"; style="filled,rounded,dashed"];')
        lines.append("  }")

    # edges: sequential within each phase, chain phases head-to-tail
    i = 0
    prev_tail = None
    for p in phases:
        nmem = sum(1 for s in steps if (s.phase or "Processing") == p)
        ids = list(range(i, i + nmem))
        i += nmem
        for a, b in zip(ids, ids[1:]):
            lines.append(f"  n{a} -> n{b};")
        if prev_tail is not None:
            lines.append(f"  n{prev_tail} -> n{i - nmem};")
        prev_tail = i - 1

    lines.append("}")
    return "\n".join(lines)


def render_flowchart(steps: List[FlowStep], out_png: str,
                     title: str = "LiCSBAS processing chain") -> str:
    """Render ``steps`` to ``out_png`` using the Graphviz ``dot`` binary.

    Raises ``RuntimeError`` if ``dot`` is unavailable or fails.
    """
    if not steps:
        raise ValueError("no steps to render")
    out_png = os.path.abspath(os.path.expanduser(out_png))
    out_dir = os.path.dirname(out_png)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="licsbas_flowchart_") as td:
        dotfile = os.path.join(td, "flowchart.dot")
        with open(dotfile, "w") as f:
            f.write(_dot_source(steps, title))
        r = subprocess.run(
            ["dot", "-Tpng", "-Gdpi=120", "-o", out_png, dotfile],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            raise RuntimeError(f"graphviz 'dot' failed:\n{r.stderr}")
    return out_png


def save_flowchart(steps: List[FlowStep], out_png: str,
                   title: str = "LiCSBAS processing chain") -> str:
    """Alias of :func:`render_flowchart` (nicer name for user scripts)."""
    return render_flowchart(steps, out_png, title=title)
