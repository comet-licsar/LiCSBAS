#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-get-value-geo``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _get_value_geo``.
"""
import sys

from _get_value_geo import main

sys.exit(main())
