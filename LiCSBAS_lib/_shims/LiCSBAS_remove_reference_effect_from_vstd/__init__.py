"""DEPRECATED compatibility shim: use ``_remove_reference_effect_from_vstd`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_remove_reference_effect_from_vstd")
