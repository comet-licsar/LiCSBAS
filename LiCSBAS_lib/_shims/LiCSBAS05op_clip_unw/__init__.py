"""DEPRECATED compatibility shim: use ``licsbas.steps._05op_clip_unw`` instead.

Kept for backwards compatibility; will be removed a few releases after the
v3.0 series.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("licsbas.steps._05op_clip_unw")
