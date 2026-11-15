"""DEPRECATED compatibility shim: use ``_11_check_unw`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_11_check_unw")
