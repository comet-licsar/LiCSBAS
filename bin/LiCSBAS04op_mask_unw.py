#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-04op-mask-unw``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _04op_mask_unw``.
"""
import sys

from _04op_mask_unw import main

sys.exit(main())
