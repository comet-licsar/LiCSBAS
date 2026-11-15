"""DEPRECATED compatibility shim: use ``_densify_ifgs`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_densify_ifgs")
