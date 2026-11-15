#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-flt2geotiff``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _flt2geotiff``.
"""
import sys

from _flt2geotiff import main

sys.exit(main())
