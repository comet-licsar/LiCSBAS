#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-profile``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._profile``.
"""
import sys

from licsbas.scripts._profile import main

sys.exit(main() or 0)
