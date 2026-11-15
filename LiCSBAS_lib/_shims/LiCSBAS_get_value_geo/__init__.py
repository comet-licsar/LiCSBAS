"""DEPRECATED compatibility shim: use ``_get_value_geo`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_get_value_geo")
