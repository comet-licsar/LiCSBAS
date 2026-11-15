#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-133-write-h5``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _133_write_h5``.
"""
import sys

from _133_write_h5 import main

sys.exit(main())
