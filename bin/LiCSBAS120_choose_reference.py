#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-120-choose-reference``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._120_choose_reference``.
"""
import sys

from licsbas.steps._120_choose_reference import main

sys.exit(main() or 0)
