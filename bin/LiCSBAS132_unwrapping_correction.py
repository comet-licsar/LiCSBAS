#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-132-unwrapping-correction``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._132_unwrapping_correction``.
"""
import sys

from licsbas.steps._132_unwrapping_correction import main

sys.exit(main() or 0)
