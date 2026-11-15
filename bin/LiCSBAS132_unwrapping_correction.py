#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-132-unwrapping-correction``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _132_unwrapping_correction``.
"""
import sys

from _132_unwrapping_correction import main

sys.exit(main())
