#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-cum-plate-motion``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _cum_plate_motion``.
"""
import sys

from _cum_plate_motion import main

sys.exit(main())
