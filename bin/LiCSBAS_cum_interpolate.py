#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-cum-interpolate``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._cum_interpolate``.
"""
import sys

from licsbas.scripts._cum_interpolate import main

sys.exit(main() or 0)
