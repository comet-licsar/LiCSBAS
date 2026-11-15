#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-131-corrections``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _131_corrections``.
"""
import sys

from _131_corrections import main

sys.exit(main())
