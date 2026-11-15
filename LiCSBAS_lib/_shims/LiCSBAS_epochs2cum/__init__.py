"""DEPRECATED compatibility shim: use ``_epochs2cum`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_epochs2cum")
