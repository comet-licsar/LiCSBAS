#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-01-get-geotiff``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._01_get_geotiff``.
"""
import sys

from licsbas.steps._01_get_geotiff import main

sys.exit(main() or 0)
