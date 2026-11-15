#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-check-install``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _check_install``.
"""
import sys

from _check_install import main

sys.exit(main())
