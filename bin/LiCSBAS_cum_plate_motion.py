#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-cum-plate-motion``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._cum_plate_motion``.
"""
import sys

from licsbas.steps._cum_plate_motion import main

sys.exit(main() or 0)
