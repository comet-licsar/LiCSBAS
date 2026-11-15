"""DEPRECATED compatibility shim: use ``_132_unwrapping_correction`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_132_unwrapping_correction")
