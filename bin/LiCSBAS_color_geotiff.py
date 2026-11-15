#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-color-geotiff``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _color_geotiff``.
"""
import sys

from _color_geotiff import main

sys.exit(main())
