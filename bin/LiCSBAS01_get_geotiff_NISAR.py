#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-01-get-geotiff-nisar``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._01_get_geotiff_nisar``.
"""
import sys

from licsbas.steps._01_get_geotiff_nisar import main

sys.exit(main() or 0)
