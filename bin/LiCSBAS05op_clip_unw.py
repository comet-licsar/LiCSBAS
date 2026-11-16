#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-05op-clip-unw``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._05op_clip_unw``.
"""
import sys

from licsbas.steps._05op_clip_unw import main

sys.exit(main() or 0)
