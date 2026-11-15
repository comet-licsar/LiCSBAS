#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-plot-network``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _plot_network``.
"""
import sys

from _plot_network import main

sys.exit(main())
