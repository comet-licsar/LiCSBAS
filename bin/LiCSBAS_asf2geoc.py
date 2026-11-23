#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-asf2geoc``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._asf2geoc``.
"""
import sys

from licsbas.scripts._asf2geoc import cli_main

sys.exit(cli_main() or 0)
