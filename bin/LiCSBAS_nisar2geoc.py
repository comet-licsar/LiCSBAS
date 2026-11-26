#!/usr/bin/env python3
"""Wrapper for the console entry point ``licsbas-nisar2geoc``.

Converts NISAR L2 PR GUNW .h5 files into a LiCSBAS GEOC/ layout
(iono + range-offset corrections; rasterio WGS84 export; baselines + metadata;
all GeoTIFFs on one shared grid).
Needs licsar_extra[nisar] (h5py, dask, xarray, rasterio, ...).

Kept for the traditional PATH-based workflow (see bashrc_LiCSBAS.sh).
Prefer the entry point, or ``python -m licsbas.scripts._nisar2geoc``.
"""
import sys

from licsbas.scripts._nisar2geoc import cli_main

sys.exit(cli_main() or 0)
