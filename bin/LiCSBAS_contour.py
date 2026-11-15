#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-contour``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _contour``.
"""
import sys

from _contour import main

sys.exit(main())
