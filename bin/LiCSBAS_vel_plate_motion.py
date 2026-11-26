#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-vel-plate-motion``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._vel_plate_motion``.
"""
import sys

from licsbas.scripts._vel_plate_motion import main

sys.exit(main() or 0)
