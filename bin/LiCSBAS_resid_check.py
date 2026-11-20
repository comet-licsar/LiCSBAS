#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-resid-check``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._resid_check``.
"""
import sys

from licsbas.scripts._resid_check import main

sys.exit(main() or 0)
