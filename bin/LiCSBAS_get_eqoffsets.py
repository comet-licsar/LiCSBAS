#!/usr/bin/env python3
"""
ML, 2025
========
Overview
========
This script gets dates of earthquakes in the area (can be used further in LiCSBAS13_sb_inv.py or LiCSBAS_cum2vel.py)

=====
Usage
=====
LiCSBAS_get_eqoffsets.py -M minmag -t TSDIR -o eqoffsets.txt
    [--buffer 0.1] [--maxdepth 60] [--acq_time 12:00] [--frame 123D_01234_121212]

 -M  minmag        Get earthquakes above minmag (float) in the region (default: 6.5)
 -t TSDIR          Uses basic info in the TS Directory (after step 11)
 -o eqoffsets.txt  Store offset dates to the txt file
 --buffer 10       Use buffer around the area extents in the search for epicentre [km] (default: 0 km)
 --maxdepth 60     Change limit of max depth of the earthquake [km] (default: 60 km)
 --acq_time 12:00:00  Set (coarse) acquisition time [HH:MM] - default: 12:00 - recommended to use. Alternatively set LiCSAR frame:
 --frame 123D_01234_121212  If known, set LiCSAR frame ID to extract acq_time (default: not used)

"""
#%% Change log
'''
2024-12 ML, ULeeds:
 - Original implementation
'''

#%% Import
import getopt
import os
import sys
import numpy as np
import time
import datetime as dt
import LiCSBAS_tools_lib as tools_lib
import LiCSBAS_io_lib as io_lib
from LiCSBAS_meta import *
try:
    from libcomcat.search import search
except:
    print('ERROR, libcomcat not installed - cannot continue. Please install libcomcat, e.g. using mamba')
    exit()

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
    outfile = []
    tsdir = []
    minmag = 6.5
    maxdepth = 60
    buffer = 0 # km
    acq_time = '12:00'
    frame = []

    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hM:o:t:", ["help", "maxdepth=", "buffer=", "acq_time=", "frame="])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                return 0
            elif o == '-t':
                tsdir = a
            elif o == '-o':
                outfile = a
            elif o == '-M':
                minmag = float(a)
            elif o == '--maxdepth':
                maxdepth = float(a)
            elif o == '--buffer':
                buffer = float(a)
            elif o == '--acq_time':
                acq_time = str(a)
            elif o == '--frame':
                frame = str(a)

        if not os.path.exists(tsdir):
            raise Usage('No {} exists! Use -t option.'.format(tsdir))

    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2


    def _get_frametime(frame):
        ''' attempt to get frame time for better precision'''
        try:
            track = str(int(frame[:3]))
        except:
            return False
        web_path = 'https://gws-access.jasmin.ac.uk/public/nceo_geohazards/LiCSAR_products'
        fullwebpath_metadata = os.path.join(web_path, track, frame, 'metadata', 'metadata.txt')
        try:
            import pandas as pd
            a = pd.read_csv(fullwebpath_metadata, sep='=', header=None)
            center_time = a[a[0] == 'center_time'][1].values[0]
            center_time_dt = dt.datetime.strptime(center_time, '%H:%M:%S.%f').time()
        except:
            return False
        return center_time_dt

    center_time_dt = ''
    if not frame:
        # try get frame id from the folder name..
        frame = os.path.basename(os.path.dirname(os.path.abspath(tsdir)))
        center_time_dt = _get_frametime(frame)

    if frame:
        center_time_dt = _get_frametime(frame)

    if not center_time_dt:
        center_time_dt = dt.datetime.strptime(acq_time, '%H:%M').time()

    # extract the region and min/max time of the dataset - from the TSDIR:
    # lonlat from TS_GEOCml3GACOSmask/info/EQA.dem_par
    # imdates from TS_GEOCml3GACOSmask/info/11ifg_stats.txt
    dempar =  os.path.join(tsdir, 'info', 'EQA.dem_par')
    ifgstats = os.path.join(tsdir, 'info', '11ifg_stats.txt')
    if not os.path.exists(ifgstats):
        raise Usage('The '+ifgstats+' file does not exist - did you run step 11?')

    ifgdates = io_lib.read_ifg_list(ifgstats)
    imdates = tools_lib.ifgdates2imdates(ifgdates)
    datein = dt.datetime.strptime(imdates[0], '%Y%m%d')
    dateout = dt.datetime.strptime(imdates[-1], '%Y%m%d')

    print('assuming geographical coordinates in WGS-84 (other systems not implemented)')
    width_geo = int(io_lib.get_param_par(dempar, 'width'))
    length_geo = int(io_lib.get_param_par(dempar, 'nlines'))
    dlat = float(io_lib.get_param_par(dempar, 'post_lat'))  # negative
    dlon = float(io_lib.get_param_par(dempar, 'post_lon'))  # positive
    lat1 = float(io_lib.get_param_par(dempar, 'corner_lat'))
    lon1 = float(io_lib.get_param_par(dempar, 'corner_lon'))
    lon2 = lon1 + dlon * width_geo
    lat2 = lat1 + dlat * length_geo

    # assuming WGS-84 as input data coordinates
    buffer = buffer / 111.111

    print('searching for events')
    events = search(starttime=datein + dt.timedelta(days=1),
                    endtime=dateout - dt.timedelta(days=1),
                    minmagnitude=minmag, limit=2000, maxdepth=maxdepth,
                    maxlongitude=max(lon1, lon2)+buffer,
                    maxlatitude=max(lat1, lat2)+buffer,
                    minlatitude=min(lat1, lat2)-buffer,
                    minlongitude=min(lon1, lon2)-buffer)

    offsetdates = []
    # print('Setting offset dates')  # TODO - better to set the offsets at the centre time between the epochs
    for e in events:
        offdate = e.time.date()
        if e.time.strftime('%Y%m%d') in imdates:
            if e.time.time() < center_time_dt:
                #print('checking the event time, an event will be set towards previous epoch')
                offdate = offdate - dt.timedelta(days=1)
        offsetdates.append(offdate)

    #offsets = tools_lib.get_earthquake_dates(cumfile, minmag=minmag, maxdepth=60)
    offsetdates = list(set(offsetdates))
    offsetdates.sort()
    print('identified '+str(len(offsetdates))+' earthquake offsets') # to solve')
    print('')

    with open(outfile, 'w') as f:
        for i in offsetdates:
            print('{}'.format(i), file=f)

    #%% Finish
    elapsed_time = time.time()-start
    hour = int(elapsed_time/3600)
    minite = int(np.mod((elapsed_time/60),60))
    sec = int(np.mod(elapsed_time,60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour,minite,sec))

    print('\n{} Successfully finished!!\n'.format(os.path.basename(argv[0])))
    print('Output: {}'.format(outfile), flush=True)


#%% main
if __name__ == "__main__":
    sys.exit(main())
