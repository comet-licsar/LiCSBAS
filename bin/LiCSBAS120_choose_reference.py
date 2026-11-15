#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-120-choose-reference``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _120_choose_reference``.
"""
import sys

from _120_choose_reference import main

sys.exit(main())
