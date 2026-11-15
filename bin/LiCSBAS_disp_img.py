#!/usr/bin/env python3
"""DEPRECATED wrapper for the new console entry point ``licsbas-disp-img``.

This thin shim keeps the legacy ``PATH`` workflow (e.g. ``bashrc_LiCSBAS.sh``)
working. Prefer the entry point, or ``python -m _disp_img``.
"""
import sys

from _disp_img import main

sys.exit(main())
