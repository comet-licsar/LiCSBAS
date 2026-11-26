#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-04op-mask-unw``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._04op_mask_unw``.
"""
import sys

from licsbas.steps._04op_mask_unw import main

sys.exit(main() or 0)
