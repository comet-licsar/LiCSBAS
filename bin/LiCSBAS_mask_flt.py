#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-mask-flt``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._mask_flt``.
"""
import sys

from licsbas.steps._mask_flt import main

sys.exit(main() or 0)
