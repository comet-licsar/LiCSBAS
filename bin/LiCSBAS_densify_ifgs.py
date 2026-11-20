#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-densify-ifgs``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._densify_ifgs``.
"""
import sys

from licsbas.scripts._densify_ifgs import main

sys.exit(main() or 0)
