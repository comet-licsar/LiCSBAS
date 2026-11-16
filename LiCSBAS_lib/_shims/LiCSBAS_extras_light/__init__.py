"""DEPRECATED compatibility shim: use ``licsbas.extras_light`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("licsbas.extras_light")
