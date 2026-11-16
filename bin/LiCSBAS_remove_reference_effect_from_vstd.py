#!/usr/bin/env python3
"""DEPRECATED wrapper for the console entry point ``licsbas-remove-reference-effect-from-vstd``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._remove_reference_effect_from_vstd``.
"""
import sys

from licsbas.steps._remove_reference_effect_from_vstd import main

sys.exit(main() or 0)
