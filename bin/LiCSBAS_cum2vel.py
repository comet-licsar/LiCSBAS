#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-cum2vel``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._cum2vel``.
"""
import sys

from licsbas.scripts._cum2vel import main

sys.exit(main() or 0)
