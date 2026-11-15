#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-131-bovl2abs``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _131_bovl2abs``.
"""
import sys

from _131_bovl2abs import main

sys.exit(main())
