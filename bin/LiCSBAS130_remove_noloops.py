#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-130-remove-noloops``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _130_remove_noloops``.
"""
import sys

from _130_remove_noloops import main

sys.exit(main())
