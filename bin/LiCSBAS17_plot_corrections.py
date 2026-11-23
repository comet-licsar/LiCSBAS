#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-17-plot-corrections``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._17_plot_corrections``.
"""
import sys

from licsbas.steps._17_plot_corrections import main

sys.exit(main() or 0)
