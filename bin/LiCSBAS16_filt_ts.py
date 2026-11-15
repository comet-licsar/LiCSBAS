#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-16-filt-ts``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _16_filt_ts``.
"""
import sys

from _16_filt_ts import main

sys.exit(main())
