#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-cum2vel-weighted``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _cum2vel_weighted``.
"""
import sys

from _cum2vel_weighted import main

sys.exit(main())
