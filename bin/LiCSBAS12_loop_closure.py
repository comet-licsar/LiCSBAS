#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-12-loop-closure``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._12_loop_closure``.
"""
import sys

from licsbas.steps._12_loop_closure import main

sys.exit(main() or 0)
