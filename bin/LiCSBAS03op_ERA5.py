#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-03op-era5``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _03op_era5``.
"""
import sys

from _03op_era5 import main

sys.exit(main())
