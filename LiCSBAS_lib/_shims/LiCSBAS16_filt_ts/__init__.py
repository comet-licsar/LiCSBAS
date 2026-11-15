"""DEPRECATED compatibility shim: use ``_16_filt_ts`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_16_filt_ts")
