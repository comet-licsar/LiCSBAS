#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-epochs2cum``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._epochs2cum``.
"""
import sys

from licsbas.scripts._epochs2cum import main

sys.exit(main() or 0)
