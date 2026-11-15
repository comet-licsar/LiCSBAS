#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-cum2flt``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _cum2flt``.
"""
import sys

from _cum2flt import main

sys.exit(main())
