"""DEPRECATED compatibility shim: use ``_17_plot_corrections`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_17_plot_corrections")
