#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-detect-coreg-error``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _detect_coreg_error``.
"""
import sys

from _detect_coreg_error import main

sys.exit(main())
