"""DEPRECATED compatibility shim: use ``_mask_flt`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_mask_flt")
