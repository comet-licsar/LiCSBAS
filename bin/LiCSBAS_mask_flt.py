#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-mask-flt``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _mask_flt``.
"""
import sys

from _mask_flt import main

sys.exit(main())
