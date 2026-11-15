#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-remove-reference-effect-from-vstd``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _remove_reference_effect_from_vstd``.
"""
import sys

from _remove_reference_effect_from_vstd import main

sys.exit(main())
