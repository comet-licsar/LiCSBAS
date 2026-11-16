#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-color-geotiff``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._color_geotiff``.
"""
import sys

from licsbas.steps._color_geotiff import main

sys.exit(main() or 0)
