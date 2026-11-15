#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-resid-check``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _resid_check``.
"""
import sys

from _resid_check import main

sys.exit(main())
