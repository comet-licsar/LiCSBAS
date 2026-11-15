"""DEPRECATED compatibility shim: use ``_04op_mask_unw`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_04op_mask_unw")
