#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-epochs2cum``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _epochs2cum``.
"""
import sys

from _epochs2cum import main

sys.exit(main())
