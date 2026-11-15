#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-reset-nulls``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _reset_nulls``.
"""
import sys

from _reset_nulls import main

sys.exit(main())
