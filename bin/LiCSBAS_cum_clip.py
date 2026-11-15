#!/usr/bin/env python3
"""

This script clips a specified rectangular area of interest from cum h5.

=====
Usage
=====
LiCSBAS_cum_clip.py [-i cum.h5] [-o cum_clipped.h5] [-r x1:x2/y1:y2] [-g lon1/lon2/lat1/lat2] [--origtsdir TS_GEOCml10] [--outtsdir clipped/TS_GEOCml10]

 -i  orig cum.h5 (if not provided, it will clip both cum.h5 and cum_filt.h5 in --origtsdir)
 -o  clipped output (not used if without -i)
 -r  Range to be clipped. Index starts from 0.
     0 for x2/y2 means all. (i.e., 0:0/0:0 means whole area).
 -g  Range to be clipped in geographical coordinates (deg).
 --origtsdir  Only used if --outtsdir provided as well.
 --outtsdir   If provided, some additional files will be clipped (towards data2json.py)

 Note the extra clipping checks for landmask.nc inside the current folder, not inside origtsdir - but will save it inside outtsdir
 Note 2: You can set just --origtsdir and --outtsdir and it will clip both cum.h5 and cum_filt.h5 -- for this, please do NOT provide -i, -o

"""
#%% Change log
'''
20260325 Milan Lazecky, Uni of Leeds
 - created from LiCSBAS05op_clip.py
'''

#%% Import
from LiCSBAS_meta import *
import LiCSBAS_tools_lib as tools_lib
import getopt
import os
import re
import sys
import glob
import shutil
import time
import numpy as np
import xarray as xr

class Usage(Exception):
    """Usage context manager"""
    def __init__(self, msg):
        self.msg = msg


#%%
def main(argv=None):

    #%% Check argv
    if argv == None:
        argv = sys.argv

    start = time.time()
    #ver='1.14.1'; date=20230804; author="Yu Morishita and COMET dev team"
    print("\n{} ver{} {} {}".format(os.path.basename(argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(argv[0]), ' '.join(argv[1:])), flush=True)

    #%% Set default
    inh5 = []
    outh5 = []
    range_str = []
    range_geo_str = []
    origtsdir = []
    cliptsdir = []
    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hi:o:r:g:", ["help", "origtsdir=", "cliptsdir=", "outtsdir="])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                return 0
            elif o == '-i':
                inh5 = a
            elif o == '-o':
                outh5 = a
            elif o == '-r':
                range_str = a
            elif o == '-g':
                range_geo_str = a
            elif o == '--cliptsdir' or o == '--outtsdir':
                cliptsdir = a
            elif o == '--origtsdir':
                origtsdir = a

        if (not inh5) and (not origtsdir):
            raise Usage('You need to provide either input h5 or origtsdir')
        if (not outh5) and (not cliptsdir):
            raise Usage('You need to provide either output h5 or output dir')
        if not range_str and not range_geo_str:
            raise Usage('No clip area given, use either-g or -r')
        if range_str and range_geo_str:
            raise Usage('Both -r and -g given, use either -r or -g not both!')
        if (cliptsdir and (not origtsdir)) or (origtsdir and (not cliptsdir)):
            raise Usage('You need to provide both orig/output directories - or use -i -o for clipping only the h5 file')
        if origtsdir:
            if not os.path.exists(origtsdir):
                raise Usage('Provided --origtsdir does not exist (you can still clip the cum.h5 without this directory..)')
            elif not os.path.exists(os.path.join(origtsdir, 'results')):
                raise Usage('The original TS folder does not contain folder with results - this will not work')

    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2
    #
    if cliptsdir:
        if not os.path.exists(cliptsdir):
            os.makedirs(cliptsdir, exist_ok=True)
        else:
            print('WARNING - the output directory already exists - we will not overwrite existing clipped data')
        if not os.path.exists(cliptsdir):
            print('WARNING - cannot create the output directory (permissions?) - clipping procedure will finish now')
            return 2
    elif not os.path.exists(inh5):
        print('ERROR: No '+inh5+' file exists')
        return 2
    #
    if not inh5:
        inh5s = []
        outh5s = []
        for aa in ['cum.h5', 'cum_filt.h5']:
            fullaa = os.path.join(origtsdir, aa)
            if os.path.exists(fullaa):
                inh5s.append(fullaa)
                outh5s.append(os.path.join(cliptsdir, aa))
        if not inh5s:
            print('ERROR - there are no cum files inside '+origtsdir)
            return 2
    else:
        inh5s = [inh5]
        outh5s = [outh5]
    #
    for i in range(len(inh5s)):
        inh5 = inh5s[i]
        outh5 = outh5s[i]
        print('Clipping '+inh5+' into '+outh5)
        # Reading the file
        a = xr.open_dataset(inh5)
        length, width = a['coh_avg'].shape
        postlat = float(a.data_vars['post_lat'].values)
        postlon = float(a.data_vars['post_lon'].values)
        lat1 = float(a.data_vars['corner_lat'].values)
        lon1 = float(a.data_vars['corner_lon'].values)
        # %% Check and set range to be clipped
        ### Read -r or -g option
        if range_str:  ## -r
            if not tools_lib.read_range(range_str, width, length):
                print('\nERROR in {}\n'.format(range_str), file=sys.stderr)
                return 1
            else:
                x1, x2, y1, y2 = tools_lib.read_range(range_str, width, length)
        elif range_geo_str:  ## -g
            if not tools_lib.read_range_geo(range_geo_str, width, length, lat1, postlat, lon1, postlon):
                print('\nERROR in {}\n'.format(range_geo_str), file=sys.stderr)
                return 1
            else:
                x1, x2, y1, y2 = tools_lib.read_range_geo(range_geo_str, width, length, lat1, postlat, lon1, postlon)
                range_str = '{}:{}/{}:{}'.format(x1, x2, y1, y2)
        #
        # dtype = a.refarea.values.dtype  # .replace('159','333')
        # now.. it is weird but phony_dim_X differs in meaning! -- very fast ugly workaround (only assuming position 0 or 2+ for time):
        dim_l, dim_w = a.coh_avg.dims
        for dimc in a.cum.dims:
            if dimc not in [dim_l, dim_w]:
                dim_t = dimc
        # refering to the mean of the scene...
        if dim_t == 'phony_dim_0':
            b = a.sel(phony_dim_1=slice(y1, y2), phony_dim_2=slice(x1, x2))
            b['cum'].values = b['cum'].values - b['cum'].mean(dim=['phony_dim_1', 'phony_dim_2']).values[:, np.newaxis,
                                                np.newaxis]
        else:
            b = a.sel(phony_dim_0=slice(y1, y2), phony_dim_1=slice(x1, x2))
            b['cum'].values = b['cum'].values - b['cum'].mean(dim=['phony_dim_0', 'phony_dim_1']).values[:, np.newaxis,
                                                np.newaxis]
        b.vel.values = b.vel.values - b.vel.mean().values
        b.vintercept.values = b.vintercept.values - b.vintercept.mean().values
        b['refarea'].values = np.array('0:' + str(x2 - x1) + '/0:' + str(y2 - y1), dtype='<U15')
        cornerlon = np.min([float(range_geo_str.split('/')[0]), float(range_geo_str.split('/')[1])])
        cornerlat = np.max([float(range_geo_str.split('/')[2]), float(range_geo_str.split('/')[3])])
        # probably not, but there is a chance we need to do
        # cornerlon = cornerlon - postlon/2
        # cornerlat = cornerlat - postlat/2
        # again. most probably not... but didn't double check the tools_lib.read_range_geo etc.
        b['corner_lon'].values = np.array(cornerlon)
        b['corner_lat'].values = np.array(cornerlat)
        outh5dir = os.path.dirname(outh5)
        if not os.path.exists(outh5dir):
            os.makedirs(outh5dir, exist_ok=True)
        b.to_netcdf(outh5)  # , engine="h5netcdf")
    #
    # optionally clip the other files needed for data2json.py script
    if cliptsdir:
        origresdir = os.path.join(origtsdir, 'results')
        clipresdir = os.path.join(cliptsdir, 'results')
        if not os.path.exists(clipresdir):
            os.mkdir(clipresdir)
        landmask = 'landmask.nc'
        if os.path.exists(landmask) and range_geo_str:
            outfile = os.path.join(cliptsdir, landmask)
            if not os.path.exists(outfile):
                print('clipping landmask.nc to '+outfile)
                lm = xr.open_dataset(landmask)
                # clip it
                lon_w, lon_e, lat_s, lat_n = [float(s) for s in range_str.split('/')]
                if 'lon' in lm.coords:
                    lm = lm.sel(lon=slice(lon_w, lon_e), lat=slice(lat_n, lat_s))
                else:
                    lm = lm.sel(x=slice(lon_w, lon_e), y=slice(lat_n, lat_s))
                if lm.shape != (y2-y1, x2-x1):
                    print('WARNING - after clipping, the landmask has different shape - expect issue, ask Milan if something..')
                lm.to_netcdf(outfile)
        #
        for toclip in ['coh_avg', 'mask', 'hgt']:
            infile = os.path.join(origresdir, toclip)
            outfile = os.path.join(clipresdir, toclip)
            if not os.path.exists(outfile):
                print('clipping '+toclip)
                data = np.fromfile(infile, dtype=np.float32).reshape((length, width))
                data = data[y1:y2, x1:x2]
                data.tofile(outfile)
        #
        #
        if not os.path.exists(cliptsdir+'/info'):
            print('copying info folder')
            os.system('cp -r {0}/info {1}/.'.format(origtsdir, cliptsdir))


#%% main
if __name__ == "__main__":
    sys.exit(main())
