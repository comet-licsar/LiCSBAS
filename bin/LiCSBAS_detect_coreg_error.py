#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-detect-coreg-error``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._detect_coreg_error``.
"""
import sys

from licsbas.steps._detect_coreg_error import main

sys.exit(main() or 0)
