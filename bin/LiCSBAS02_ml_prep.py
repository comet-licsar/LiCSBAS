#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-02-ml-prep``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _02_ml_prep``.
"""
import sys

from _02_ml_prep import main

sys.exit(main())
