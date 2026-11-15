"""DEPRECATED compatibility shim: use ``_133_write_h5`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_133_write_h5")
