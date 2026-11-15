#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-cum2vel``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _cum2vel``.
"""
import sys

from _cum2vel import main

sys.exit(main())
