#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-remove-reference-effect-from-vstd``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._remove_reference_effect_from_vstd``.
"""
import sys

from licsbas.scripts._remove_reference_effect_from_vstd import main

sys.exit(main() or 0)
