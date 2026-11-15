"""DEPRECATED compatibility shim: use ``_14_vel_std`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_14_vel_std")
