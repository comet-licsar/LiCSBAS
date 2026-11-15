#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-14-vel-std``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _14_vel_std``.
"""
import sys

from _14_vel_std import main

sys.exit(main())
