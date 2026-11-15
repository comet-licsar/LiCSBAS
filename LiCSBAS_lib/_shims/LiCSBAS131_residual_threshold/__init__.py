"""DEPRECATED compatibility shim: use ``_131_residual_threshold`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_131_residual_threshold")
