#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-03op-gacos``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._03op_gacos``.
"""
import sys

from licsbas.steps._03op_gacos import main

sys.exit(main() or 0)
