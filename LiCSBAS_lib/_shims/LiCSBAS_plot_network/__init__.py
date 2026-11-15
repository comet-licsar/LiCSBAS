"""DEPRECATED compatibility shim: use ``_plot_network`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_plot_network")
