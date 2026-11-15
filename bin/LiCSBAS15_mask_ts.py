#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-15-mask-ts``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _15_mask_ts``.
"""
import sys

from _15_mask_ts import main

sys.exit(main())
