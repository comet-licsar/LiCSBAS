#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-12-loop-closure``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _12_loop_closure``.
"""
import sys

from _12_loop_closure import main

sys.exit(main())
