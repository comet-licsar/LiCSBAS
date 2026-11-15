"""DEPRECATED compatibility shim: use ``_12_loop_closure`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_12_loop_closure")
