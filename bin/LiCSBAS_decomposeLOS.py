#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-decomposelos``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _decomposelos``.
"""
import sys

from _decomposelos import main

sys.exit(main())
