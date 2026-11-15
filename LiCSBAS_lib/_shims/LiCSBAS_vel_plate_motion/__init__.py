"""DEPRECATED compatibility shim: use ``_vel_plate_motion`` instead.
"""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("_vel_plate_motion")
