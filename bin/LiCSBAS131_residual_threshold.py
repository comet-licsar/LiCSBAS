#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-131-residual-threshold``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _131_residual_threshold``.
"""
import sys

from _131_residual_threshold import main

sys.exit(main())
