"""DEPRECATED compatibility shim: use ``_01_get_geotiff_alos`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_01_get_geotiff_alos")
