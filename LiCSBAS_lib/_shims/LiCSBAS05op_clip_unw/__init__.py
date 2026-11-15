"""DEPRECATED compatibility shim: use ``_05op_clip_unw`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_05op_clip_unw")
