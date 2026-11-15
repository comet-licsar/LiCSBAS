"""DEPRECATED compatibility shim: use ``_130_remove_noloops`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_130_remove_noloops")
