#!/usr/bin/env python3
"""Legacy wrapper for the console entry point ``licsbas-02op-phasebias``.

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.steps._02op_phasebias``.

NOTE: requires the standalone ``phasebias`` package
(https://github.com/comet-licsar/InSAR_PhaseBias_Correction).
"""
import sys

from licsbas.steps._02op_phasebias import main

sys.exit(main() or 0)
