#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-01-get-geotiff``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _01_get_geotiff``.
"""
import sys

from _01_get_geotiff import main

sys.exit(main())
