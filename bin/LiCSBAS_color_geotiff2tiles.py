#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-color-geotiff2tiles``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._color_geotiff2tiles``.
"""
import sys

from licsbas.steps._color_geotiff2tiles import main

sys.exit(main() or 0)
