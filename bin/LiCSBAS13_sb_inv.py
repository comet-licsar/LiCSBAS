#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-13-sb-inv``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._13_sb_inv``.
"""
import sys

from licsbas.steps._13_sb_inv import main

sys.exit(main() or 0)
