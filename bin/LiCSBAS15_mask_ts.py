#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-15-mask-ts``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._15_mask_ts``.
"""
import sys

from licsbas.steps._15_mask_ts import main

sys.exit(main() or 0)
