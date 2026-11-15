"""DEPRECATED compatibility shim: use ``_03op_gacos`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_03op_gacos")
