#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-cum2vel-weighted``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._cum2vel_weighted``.
"""
import sys

from licsbas.steps._cum2vel_weighted import main

sys.exit(main() or 0)
