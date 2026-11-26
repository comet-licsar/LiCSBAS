#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-130-remove-noloops``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._130_remove_noloops``.
"""
import sys

from licsbas.steps._130_remove_noloops import main

sys.exit(main() or 0)
