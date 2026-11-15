"""DEPRECATED compatibility shim: use ``_color_geotiff`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_color_geotiff")
