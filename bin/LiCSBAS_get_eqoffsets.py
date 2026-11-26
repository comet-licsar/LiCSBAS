#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-get-eqoffsets``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._get_eqoffsets``.
"""
import sys

from licsbas.scripts._get_eqoffsets import main

sys.exit(main() or 0)
