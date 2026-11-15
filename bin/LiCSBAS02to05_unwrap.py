#!/usr/bin/env python3
"""

This script unwraps GeoTIFF files of wrapped interferograms, for further time series analysis.
It replaces the original LiCSBAS steps 02-05 (except for 04), as these are done in one go.

NOTE: If your input data are coming from the LiCSAR system, please make sure you did run LiCSBAS01 with parameter --get_pha

====================
Input & output files
====================
Inputs:
 - GEOC/    
   - yyyymmdd_yyyymmdd/
     - yyyymmdd_yyyymmdd.geo.diff_unfiltered_pha.tif
    [- yyyymmdd_yyyymmdd.geo.diff_pha.tif]
     - yyyymmdd_yyyymmdd.geo.cc.tif
  [- *.geo.mli.tif]
  [- *.geo.hgt.tif]
  [- *.geo.[E|N|U].tif]
  [- baselines]
  [- metadata.txt]
[- GEOC.MLI/]
  [- yyyymmdd/yyyymmdd.geo.mli.tif]
[- GACOS/]
  [- yyyymmdd/yyyymmdd.geo.sltd.tif]


Outputs in GEOCmlX[GACOS][clip]:
 - yyyymmdd_yyyymmdd/
   - yyyymmdd_yyyymmdd.unw[.png] (float32)
   - yyyymmdd_yyyymmdd.cc (uint8)
   - yyyymmdd_yyyymmdd.conncomp (uint8)
 - baselines (may be dummy)
 - EQA.dem_par
 - slc.mli.par
 - slc.mli[.png] (if input exists)
 - hgt[.png] (if input exists)
 - [E|N|U].geo (if input exists)

=====
Usage
=====
LiCSBAS02to05_unwrap.py -i WORKdir [-M nlook] [-g lon1/lon2/lat1/lat2] [--filter gold|gauss|adf] [--gacos] [--hgtcorr] [--cascade/--cascade_full] [--thres float] [--freq float] [--n_para int] [--nolandmask]

 -i  <str> Path to the work directory (i.e. folder that contains the input GEOC dir with the stack of geotiff data, and optionally other dirs: GEOC.MLI, GACOS)
 -M  <int> Number of multilooking factor (Default: 10, 10x10 multilooking)
 -g  <str> Range to be clipped in geographical coordinates (deg), as lon1/lon2/lat1/lat2
 --filter <str>  Spatial filter to support primary unwrapping and to estimate consistence (Default: Goldstein)
   gold:   Adapted implementation of the Goldstein filter, consistence estimated as FFT spectral magnitude
   gauss:  A 2-D Gaussian kernel filter, consistence estimated based on filter residuals. Fast solution, not recommended for high phase gradients
   adf:    Use of ADF2 for the adaptive filter implemented by GAMMA software (if available), ADF-coherence applied as consistence
 --gacos   Use GACOS data (recommended, expects GACOS folder - see LiCSBAS_01_get_geotiff.py). Note this will limit dataset to epochs with GACOS correction.
 --hgtcorr Apply height-correlation correction (default: not apply). Note this will be turned off if GACOS is to be used.
 --cascade  Apply cascade unwrapping approach: 1 cascade with 10xML layer (recommended)
 --cascade_full Apply full cascade unwrapping approach: 3 cascade steps through 10-5-3xML layers (experimental)
 --thres <float> Threshold value for masking noise based on consistence (Default: 0.3)
 --freq <float>   Radar frequency in Hz (Default: 5.405e9 for Sentinel-1)
           (e.g., 1.27e9 for ALOS, 1.2575e9 for ALOS-2/U, 1.2365e9 for ALOS-2/{F,W})
 --n_para <int> Number of parallel processing (Default: # of usable CPU)
 --nolandmask Do not apply landmask (ON by default)
 
The command will run reunwrapping on interferograms inside WORKdir/GEOC.
Outputs are stored inside WORKdir/GEOCmlX[GACOS][clip] where X is the multilooking factor (-M).
For more information about the procedure, see e.g. https://ieeexplore.ieee.org/document/9884337
"""
#%% Change log
'''
vXX 20240205 ML
 - 'almost' full lics_unwrap functionality (incl. ADF)
v1.14.2 20230628 Milan Lazecky, UniLeeds
 - initial version using previously developed lics_unwrap functions
'''


#%% Import
from LiCSBAS_meta import *
import getopt
import os
import sys
import time
import numpy as np
import multiprocessing as multi

# but should cancel if there is no snaphu installed
if os.system('which snaphu >/dev/null 2>/dev/null') != 0:
    print('snaphu not detected. please install it yourself, e.g. from:')
    print('https://web.stanford.edu/group/radar/softwareandlinks/sw/snaphu')
    exit()


try:
    import lics_unwrap as unw
except:
    try:
        from licsar_extra import lics_unwrap as unw
    except:
        print('ERROR: lics_unwrap library not found.')
        print('please install from https://github.com/comet-licsar/licsar_extra')
        print('e.g.:')
        print('pip install git+git://github.com/comet-licsar/licsar_extra.git#egg=licsar_extra')
        sys.exit()


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
    ver="1.14.2"; date='2023-06-28'; author="M. Lazecky"
    print("\n{} ver{} {} {}".format(os.path.basename(argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(argv[0]), ' '.join(argv[1:])), flush=True)
    
    #%% Set default
    workdir = []
    ml = 10
    freq = 5405000000
    thres = 0.3
    cliparea_geo = None
    cascade = False
    only10 = True
    hgtcorr = False
    gacoscorr = False
    do_landmask = True
    spfilter = 'gold'

    try:
        nproc = len(os.sched_getaffinity(0))
    except:
        nproc = multi.cpu_count()
    
    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hi:g:M:", ["help", "gacos", "hgtcorr", "cascade", "cascade_full", "filter=","nolandmask", "thres=", "freq=", "n_para="])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                return 0
            elif o == '-i':
                workdir = a
            elif o == '-M':
                ml = int(a)
            elif o == '-g':
                cliparea_geo = a
            elif o == '--thres':
                thres = float(a)
            elif o == '--gacos':
                gacoscorr = True
            elif o =='--filter':
                spfilter = a
            elif o == '--hgtcorr':
                hgtcorr = True
            elif o == '--nolandmask':
                do_landmask = False
            elif o == '--cascade':
                cascade = True
                only10 = True
            elif o == '--cascade_full':
                if cascade:
                    print('both cascade params set. Prioritising the cascade_full param')
                cascade = True
                only10 = False
            elif o == '--freq':
                freq = float(a)
            elif o == '--n_para':
                nproc = int(a)
        
        if not workdir:
            raise Usage('No WORK directory given, -d is not optional!')
        elif not os.path.isdir(workdir):
            raise Usage('No {} dir exists!'.format(workdir))
        elif not os.path.isdir(os.path.join(workdir, 'GEOC')):
            raise Usage('No GEOC dir exists in {}!'.format(workdir))
        if gacoscorr and not os.path.exists(os.path.join(workdir, 'GACOS')):
            raise Usage('No GACOS dir exists in {} but use of GACOS turned on!'.format(workdir))
        if spfilter not in ['gold', 'gauss', 'adf']:
            raise Usage("Wrong filtering option set - only 'gold', 'gauss', or 'adf' are available")
        if spfilter == 'adf':
            # check for gamma commands
            if os.system('which adf2 >/dev/null 2>/dev/null') != 0:
                raise Usage('ERROR: GAMMA SW not found, cancelling')
    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2
    
    if gacoscorr and hgtcorr:
        print('WARNING, both GACOS and DEM-correlated signal corrections are ON. Turning hgtcorr OFF.')
        hgtcorr = False
    
    # just run the existing script, but it expects being inside the directory with the GEOC folder!
    os.chdir(workdir)
    outdir = 'GEOCml'+str(ml)
    if gacoscorr:
        outdir=outdir+'GACOS'
    if cliparea_geo:
        outdir=outdir+'clip'
    outdir = os.path.join(workdir, outdir)
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    os.chdir(outdir) # need to run the processing here..
    # about the filters
    if spfilter == 'gauss':
        goldstein = False
        use_gamma = False
        smooth = True
    elif spfilter == 'gold':
        goldstein = True
        use_gamma = False
        smooth = False
    elif spfilter == 'adf':
        goldstein = True
        use_gamma = True
        smooth = False
    print('Running unwrapping using given parameters')
    unw.process_frame(ml = ml, thres = thres, cliparea_geo = cliparea_geo, 
                cascade=cascade, only10 = only10,
                hgtcorr = hgtcorr, gacoscorr = gacoscorr,
                nproc = nproc, freq=freq,
                # if smooth, combine with filtered ifgs
                goldstein = goldstein, smooth = smooth, use_gamma = use_gamma,
                prefer_unfiltered = True, # UNFILTERED SEEM ALWAYS BETTER!!! # TODO ?
                # keeping the 'not-to-be-changed'defaults:
                lowpass = False, defomax = 0.3, dolocal = True, frame = 'dummy', specmag = True,
                pairsetfile = None, subtract_gacos = True, export_to_tif = False,
                keep_coh_debug = True, use_amp_coh = False, use_coh_stab = False, use_amp_stab = False, gacosdir = '../GACOS', do_landmask = do_landmask)
    
    os.chdir(workdir)
    #%% Finish
    elapsed_time = time.time()-start
    hour = int(elapsed_time/3600)
    minite = int(np.mod((elapsed_time/60),60))
    sec = int(np.mod(elapsed_time,60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour,minite,sec))
    
    print('\n{} Successfully finished!!\n'.format(os.path.basename(argv[0])))
    print('Output directory: {}\n'.format(os.path.relpath(outdir)))


#%% main
if __name__ == "__main__":
    sys.exit(main())

