#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-flt2geotiff``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._flt2geotiff``.
"""
import sys

from licsbas.scripts._flt2geotiff import main

sys.exit(main() or 0)
