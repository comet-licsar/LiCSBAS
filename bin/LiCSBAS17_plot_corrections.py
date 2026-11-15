#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-17-plot-corrections``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _17_plot_corrections``.
"""
import sys

from _17_plot_corrections import main

sys.exit(main())
