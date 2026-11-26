#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-disp-img``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._disp_img``.
"""
import sys

from licsbas.scripts._disp_img import main

sys.exit(main() or 0)
