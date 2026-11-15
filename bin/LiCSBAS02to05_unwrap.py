#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-02to05-unwrap``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _02to05_unwrap``.
"""
import sys

from _02to05_unwrap import main

sys.exit(main())
