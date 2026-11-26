#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-133-write-h5``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._133_write_h5``.
"""
import sys

from licsbas.steps._133_write_h5 import main

sys.exit(main() or 0)
