#!/usr/bin/env python3

"""
v1.0 20250731 Muhammet Nergizci, Uni of Leeds 

========
Overview
========
This script interpolates the inSAR epoch regarding the given csv file by applying linear interpolation.

=====
Usage
=====
LiCSBAS_cum_interpolate.py -t TS_folder --csv csv.file

  -t  Path to the folder. Default: TS_GEOCml10GACOSmask.
  --csv  Path to the CSV file
"""


#%% Import
import pandas as pd
from LiCSBAS_meta import *
import getopt
import os
import sys
import time
import numpy as np
import datetime as dt
import h5py as h5
import cmcrameri.cm as cmc
import xarray as xr


class Usage(Exception):
    """Usage context manager"""
    def __init__(self, msg):
        self.msg = msg


#%% Main
def main(argv=None):

    #%% Check argv
    if argv == None:
        argv = sys.argv

    start = time.time()
    print("\n{} ver{} {} {}".format(os.path.basename(argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(argv[0]), ' '.join(argv[1:])), flush=True)

    #%% Set default
    tsadir = []
    cumname = 'cum_filt.h5'
    csvfile = []
    csv = None
    cmap_wrap = cmc.romaO
    compress = 'gzip'
    modelfile = ''
    nopngs = False

    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "ht:",
                           ["help", "csv="])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                return 0
            elif o == '-t':
                tsadir = a
            elif o == '--csv':
                csv = a
        
        #%%file
        if not tsadir:
            raise Usage('No tsa directory given, -t is not optional!')
        elif not os.path.isdir(tsadir):
            raise Usage('No {} dir exists!'.format(tsadir))
        elif not os.path.exists(os.path.join(tsadir, cumname)):
            raise Usage('No {} exists in {}!'.format(cumname, tsadir))
        
        ###This is needed for          
        if not csv:
            raise Usage('No CSV file given, --csv is not optional!, this is needed for interseismic analysis')
        elif not os.path.exists(csv):
            raise Usage('No {} exists!'.format(csv))

    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2

    #%%Directory and file setting
    tsadir = os.path.abspath(tsadir)
    cumfile = os.path.join(tsadir, cumname)
    csvfile = os.path.abspath(csv)
    
    #%%cumfile
    cumfile_xr = xr.load_dataset(cumfile)
    cum_xr = cumfile_xr["cum"]
    imdates = cumfile_xr["imdates"].values
    # breakpoint()
    time_idx = pd.to_datetime(imdates.astype(str), errors='coerce')
    if pd.isna(time_idx).any():
        bad = np.where(pd.isna(time_idx))[0][:5]
        raise ValueError(f"Bad date format in imdates: {imdates[bad]}")
      
    # attach time; rename phony dims if present
    da = cum_xr  # <— use the loaded variable
    da = da.assign_coords({da.dims[0]: time_idx}).rename({da.dims[0]: "time"})
    ren = {d: ("y" if i==1 else "x") for i, d in enumerate(da.dims[1:], 1) if d.startswith("phony_dim")}
    if ren: 
        da = da.rename(ren)
    da = da.sortby("time")  # ensure ascending
    
    
    #%%csv file
    csv_dt = (
        pd.read_csv(csvfile)["date"]
          .astype(str)
          .pipe(pd.to_datetime, errors="coerce")
          .dropna()
          .sort_values()
          .unique()
    )
    
    #%%linear interpolation
    interp= da.interp(time=csv_dt, method="linear")  ##TODO: the method can be changed later if needed, e.g. quadratic but I get some issues with that now.

    ##Linear extrapolation
    t_days = da.time.values.astype("datetime64[D]").astype(int)
    g_days = interp.time.values.astype("datetime64[D]").astype(int)
    t0, tN = int(t_days[0]), int(t_days[-1])
    
    # slopes from first and last segments
    dt0 = float(t_days[1] - t_days[0])
    dtN = float(t_days[-1] - t_days[-2])
    if dt0 == 0 or dtN == 0:
        raise ValueError("Duplicate timestamps in InSAR time axis.")

    slope_start = (da.isel(time=1)  - da.isel(time=0))  / dt0     # (y,x)
    slope_end   = (da.isel(time=-1) - da.isel(time=-2)) / dtN     # (y,x)
    
    # masks and time offsets (as DataArrays for clean broadcasting)
    time_idx_interp = interp["time"]
    before = xr.DataArray(g_days <  t0, dims=["time"], coords={"time": time_idx_interp})
    after  = xr.DataArray(g_days >  tN, dims=["time"], coords={"time": time_idx_interp})
    d_before = xr.DataArray((g_days - t0).astype(float), dims=["time"], coords={"time": time_idx_interp})
    d_after  = xr.DataArray((g_days - tN).astype(float), dims=["time"], coords={"time": time_idx_interp})

    # predicted values outside span (broadcast: (time) with (y,x))
    pred_before = da.isel(time=0)  + slope_start * d_before
    pred_after  = da.isel(time=-1) + slope_end   * d_after

    # fill only outside
    interp = interp.where(~before, pred_before)
    interp = interp.where(~after,  pred_after)
    
   #%% Saving results
    cumfh5 = h5.File(cumfile, 'r+')  # source (for copying datasets)
    cumifile = os.path.join(tsadir, 'cum_filt_interpolate.h5')
    if os.path.exists(cumifile):
        os.remove(cumifile)
    cumih5 = h5.File(cumifile, 'w')
    
    # copy datasets if present
    indices = ['coh_avg', 'hgt', 'n_loop_err', 'n_unw', 'slc.mli',
               'maxTlen', 'n_gap', 'n_ifg_noloop', 'resid_rms',
               'E.geo', 'N.geo', 'U.geo', 'filtwidth_yr', 'filtwidth_km', 'deramp_flag', 'hgt_linear_flag', 'demerr_flag', 'masked', 'vel', 'vintercept', 'corner_lat', 'corner_lon',
               'post_lat', 'post_lon', 'refarea']
    
    for index in indices:
        if index in list(cumih5.keys()):
            del cumih5[index]
        if index in list(cumfh5.keys()):
            # read array content
            data_in = cumfh5[index][...]
            cumih5.create_dataset(index, data=data_in)
        else:
            print('  No {} field found in {}. Skip.'.format(index, cumname))
          
    ##interp_time
    interp_time = interp.assign_coords(
        time = pd.to_datetime(interp.time.values).strftime("%Y%m%d").astype(np.int32)
    )
    if 'imdates' in cumih5:
        del cumih5['imdates']
    cumih5.create_dataset('imdates', data=interp_time.time.values, dtype=np.int32)
    if 'cum' in cumih5:
        del cumih5['cum']
    cumih5.create_dataset('cum', data=interp.values.astype(np.float32), dtype=np.float32, compression=compress)
    cumih5.close()
    cumfh5.close()

    #%% Finish
    elapsed_time = time.time()-start
    hour = int(elapsed_time/3600)
    minite = int(np.mod((elapsed_time/60),60))
    sec = int(np.mod(elapsed_time,60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour,minite,sec))

#%% main
if __name__ == "__main__":
    sys.exit(main())
