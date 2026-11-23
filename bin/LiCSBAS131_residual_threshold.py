#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-131-residual-threshold``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._131_residual_threshold``.
"""
import sys

from licsbas.steps._131_residual_threshold import main

sys.exit(main() or 0)
