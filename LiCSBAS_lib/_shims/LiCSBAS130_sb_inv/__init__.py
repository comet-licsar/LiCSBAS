"""DEPRECATED compatibility shim: use ``_130_sb_inv`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_130_sb_inv")
