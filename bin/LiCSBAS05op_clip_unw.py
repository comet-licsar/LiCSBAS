#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-05op-clip-unw``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _05op_clip_unw``.
"""
import sys

from _05op_clip_unw import main

sys.exit(main())
