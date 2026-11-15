#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-03op-gacos``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _03op_gacos``.
"""
import sys

from _03op_gacos import main

sys.exit(main())
