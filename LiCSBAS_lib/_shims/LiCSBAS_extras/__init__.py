"""DEPRECATED compatibility shim: use ``licsbas.extras`` instead.

Removed in a future release once old import conventions are retired.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("licsbas.extras")
