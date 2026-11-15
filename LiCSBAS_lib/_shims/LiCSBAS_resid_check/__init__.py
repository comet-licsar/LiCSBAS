"""DEPRECATED compatibility shim: use ``_resid_check`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_resid_check")
