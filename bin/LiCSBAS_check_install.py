#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-check-install``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._check_install``.
"""
import sys

from licsbas.steps._check_install import main

sys.exit(main() or 0)
