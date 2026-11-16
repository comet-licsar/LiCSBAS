#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-contour``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._contour``.
"""
import sys

from licsbas.steps._contour import main

sys.exit(main() or 0)
