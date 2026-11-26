#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-get-value-geo``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._get_value_geo``.
"""
import sys

from licsbas.scripts._get_value_geo import main

sys.exit(main() or 0)
