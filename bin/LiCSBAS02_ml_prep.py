#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-02-ml-prep``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._02_ml_prep``.
"""
import sys

from licsbas.steps._02_ml_prep import main

sys.exit(main() or 0)
