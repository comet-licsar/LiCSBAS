"""DEPRECATED compatibility shim: use ``_02_ml_prep`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_02_ml_prep")
