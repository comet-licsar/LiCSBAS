#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-vel-plate-motion``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _vel_plate_motion``.
"""
import sys

from _vel_plate_motion import main

sys.exit(main())
