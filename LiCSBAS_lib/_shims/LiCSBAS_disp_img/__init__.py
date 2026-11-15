"""DEPRECATED compatibility shim: use ``_disp_img`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_disp_img")
