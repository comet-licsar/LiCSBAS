#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-color-geotiff``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._color_geotiff``.
"""
import sys

from licsbas.scripts._color_geotiff import main

sys.exit(main() or 0)
