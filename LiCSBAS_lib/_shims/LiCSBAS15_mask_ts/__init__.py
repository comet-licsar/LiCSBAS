"""DEPRECATED compatibility shim: use ``_15_mask_ts`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_15_mask_ts")
