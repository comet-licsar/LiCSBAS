#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-profile``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _profile``.
"""
import sys

from _profile import main

sys.exit(main())
