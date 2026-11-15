#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-11-check-unw``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _11_check_unw``.
"""
import sys

from _11_check_unw import main

sys.exit(main())
