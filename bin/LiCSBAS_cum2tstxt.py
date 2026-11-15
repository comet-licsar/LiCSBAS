#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-cum2tstxt``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _cum2tstxt``.
"""
import sys

from _cum2tstxt import main

sys.exit(main())
