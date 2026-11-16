#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-plot-network``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._plot_network``.
"""
import sys

from licsbas.steps._plot_network import main

sys.exit(main() or 0)
