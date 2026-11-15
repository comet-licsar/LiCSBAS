#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-densify-ifgs``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _densify_ifgs``.
"""
import sys

from _densify_ifgs import main

sys.exit(main())
