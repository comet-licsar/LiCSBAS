#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-130-sb-inv``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._130_sb_inv``.
"""
import sys

from licsbas.steps._130_sb_inv import main

sys.exit(main() or 0)
