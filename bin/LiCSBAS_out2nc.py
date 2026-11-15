#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-out2nc``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _out2nc``.
"""
import sys

from _out2nc import main

sys.exit(main())
