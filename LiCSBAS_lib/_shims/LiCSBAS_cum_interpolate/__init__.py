"""DEPRECATED compatibility shim: use ``_cum_interpolate`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_cum_interpolate")
