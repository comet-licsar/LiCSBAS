"""DEPRECATED compatibility shim: use ``_flt2geotiff`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_flt2geotiff")
