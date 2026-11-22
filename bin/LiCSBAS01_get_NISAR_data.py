#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-01-get-nisar-data``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._01_get_nisar_data``.
"""
import sys

from licsbas.steps._01_get_nisar_data import main

sys.exit(main() or 0)
