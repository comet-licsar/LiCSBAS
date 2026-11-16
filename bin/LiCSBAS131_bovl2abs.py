#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-131-bovl2abs``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._131_bovl2abs``.
"""
import sys

from licsbas.steps._131_bovl2abs import main

sys.exit(main() or 0)
