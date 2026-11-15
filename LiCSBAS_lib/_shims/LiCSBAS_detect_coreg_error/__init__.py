"""DEPRECATED compatibility shim: use ``_detect_coreg_error`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_detect_coreg_error")
