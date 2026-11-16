#!/usr/bin/env python3
"""

This script applies spatio-temporal filter (HP in time and LP in space with gaussian kernel, same as StaMPS) to the time series of displacement. Deramping (1D, bilinear, or 2D polynomial) can also be applied if -r option is used. Topography-correlated components (linear with elevation) can also be subtracted with --hgt_linear option simultaneously with deramping before spatio-temporal filtering. The impact of filtering (deramp and linear elevation as well) can be visually checked by showing 16filt*/*png. A stable reference point is determined after the filtering as well as Step 1-3.

===============
Input & output files
===============
Inputs in TS_GEOCml*/ :
 - cum.h5
 - results
   - mask
   - hgt (if --hgt_linear option is used)
   [- U (if --hgt_linear option is used)]
 - info/13parameters.txt

Outputs in TS_GEOCml*/ :
 - cum_filt_s{spatial_kernel_size(km)}_t{temporal_width(day)}.h5
 - 16filt_cum/
   - yyyymmdd_filt.png
  [- yyyymmdd_deramp.png]     (if -r option is used)
  [- yyyymmdd_hgt_linear.png] (if --hgt_linear option is used)
  [- yyyymmdd_hgt_corr.png]   (if --hgt_linear option is used)
 - 16filt_increment/
   - yyyymmdd_yyyymmdd_filt.png
  [- yyyymmdd_yyyymmdd_deramp.png]     (if -r option is used)
  [- yyyymmdd_yyyymmdd_hgt_linear.png] (if --hgt_linear option is used)
  [- yyyymmdd_yyyymmdd_hgt_corr.png]   (if --hgt_linear option is used)
 - results/
   - vel.filt[.mskd][.png]   : Filtered velocity
   - vintercept.filt.mskd[.png]
 - info/
   - 16parameters.txt        : List of used parameters
   - 16ref.txt[.kml]         : Auto-determined stable ref point
   - 16rms_cum_wrt_med[.png] : RMS of cum wrt median used for ref selection

=====
Usage
=====
LiCSBAS16_filt_ts.py -t tsadir [-s filtwidth_km] [-y filtwidth_yr] [-r deg]
 [--hgt_linear] [--hgt_min int] [--hgt_max int] [--demerr] [--nomask] [--n_para int]
 [--range x1:x2/y1:y2 | --range_geo lon1/lon2/lat1/lat2]
 [--ex_range x1:x2/y1:y2 | --ex_range_geo lon1/lon2/lat1/lat2]
 [--from_model path/to/model.h5] [--interpolate_nans] [--nopngs]

 -t  Path to the TS_GEOCml* dir.
 -s  Width of spatial filter in km (Default: 2 km)
 -y  Width of temporal filter in yr (Default: auto, avg_interval*3)
 -r  Degree of deramp [1, bl, 2] (Default: no deramp)
     1: 1d ramp, bl: bilinear, 2: 2d polynomial
 --demerr     Estimate and remove DEM error phase
 --hgt_linear Subtract topography-correlated component using a linear method
              (Default: Not apply)
 --hgt_min    Minumum hgt to take into account in hgt-linear (Default: 200m)
 --hgt_max    Maximum hgt to take into account in hgt-linear (Default: 10000m, no effect)
 --nomask     Apply filter to unmasked data (Default: apply to masked)
 --nofilter   Do not perform neither spatial nor temporal filtering
 --n_para     Number of parallel processing (Default: # of usable CPU)
 --range      Range used in deramp and hgt_linear. Index starts from 0.
              0 for x2/y2 means all. (i.e., 0:0/0:0 means whole area).
 --range_geo  Range used in deramp and hgt_linear in geographical coordinates
              (deg).
 --ex_range   Range EXCLUDED in deramp and hgt_linear. Index starts from 0.
              0 for x2/y2 means all. (i.e., 0:0/0:0 means whole area).
 --ex_range_geo  Range EXCLUDED in deramp and hgt_linear in geographical
                 coordinates (deg).
 --from_model path/to/model.h5  Use externally calculated model to perform residual-based filtering (in dev further. see LiCSBAS_cum2vel.py to generate this)
 --interpolate_nans   This will use the filter to fill nan values (in unmasked data). If temporal filtering is disabled, it will use linear interpolation in space instead.
 --nopngs     Avoid generating some (unnecessary) PNG previews of increment residuals etc.
 --sbovl     processing sbovl input spatio-temporal filter.
 --sbovl_abs recalculate the absolute velocity of sbovl, referecing steps are skipped!
 --naming   save the cum_filt with spatial and temporal filter size like cum_filt_s{spatial_kernel_size(km)}_t{temporal_width(day)}.h5
Note: Spatial filter consume large memory. If the processing is stacked, try
 - --n_para 1
 - Indicate small filtwidth_km for -s option
 - Reduce data size in step02 or step05

"""
#%% Change log
'''
20260517 MN
 - reordering sbovl, sbovl_abs and removing the tide and iono flags: these correction will applied right after step13 before the bootstraping.
20250211 MN
 - added sbovl, tide and iono flags for Burst overlap interferometry in LiCSBAS.
20241107 ML
 - added interpolate_nans and updated masking of final cum_filt data
20241029 Milan Lazecky
 - allow running the filter starting from model residuals --- do not use before deramping
v1.6.0 20230116 Yu Morishita
 - Add --demerr option to estimate/remove DEM error phase
v1.5.3 20230602 M. Lazecky and Pedro E. Bedon, Uni of Leeds
 - scale heights with inc. angle for hgt_linear
v1.5.2 20211122 Milan Lazecky, Leeds Uni
 - include no_filter parameter
v1.5.1 20210311 Yu Morishita, GSI
 - Include noise indices and LOS unit vector in cum.h5 file
v1.5 20210309 Yu Morishita, GSI
 - Add GPU option but not recommended (hidden option)
 - Speed up by not directry read/write from/to hdf5 file during process
v1.4.6 20210308 Yu Morishita, GSI
 - Not use multiprocessing when n_para=1
v1.4.5 20201124 Yu Morishita, GSI
 - Comporess hdf5 file
v1.4.4 20201119 Yu Morishita, GSI
 - Change default cmap for wrapped phase from insar to SCM.romaO
v1.4.3 20201118 Yu Morishita, GSI
 - Again Bug fix of multiprocessing
v1.4.2 20201116 Yu Morishita, GSI
 - Bug fix of multiprocessing in Mac python>=3.8
v1.4.1 20201028 Yu Morishita, GSI
 - Update how to get n_para
v1.4 20201020 Yu Morishita, GSI
 - Add --range[_geo] and --ex_range[_geo] options
v1.3 20200909 Yu Morishita, GSI
 - Parallel processing
v1.2 20200228 Yu Morishita, Uni of Leeds and GSI
 - Divide 16filt dir to 16filt_increment and 16filt_cum
 - Change color of png
 - Update about parameters.txt
 - Add --hgt_linear and related options
 - Bag fix for deramp (mask was not applyed)
 - Automatically find stable reference point
v1.1 20190829 Yu Morishita, Uni of Leeds and GSI
 - Remove cum_filt.h5 if exists before creation
v1.0 20190731 Yu Morishita, Uni of Leeds and GSI
 - Original implementation
'''

#%% Import
from LiCSBAS_meta import *
import getopt
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys
import time
import shutil
import warnings
import numpy as np
import datetime as dt
import h5py as h5
from astropy.convolution import Gaussian2DKernel, convolve_fft
import multiprocessing as multi
import cmcrameri.cm as cmc
import LiCSBAS_io_lib as io_lib
import LiCSBAS_tools_lib as tools_lib
import LiCSBAS_inv_lib as inv_lib
import LiCSBAS_plot_lib as plot_lib
import re
from scipy.interpolate import interp1d


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

    ## for parallel processing
    global cum, mask, deg_ramp, hgt_linearflag, hgt, hgt_min, hgt_max,\
    filtcumdir, filtincdir, imdates, cycle, coef_r2m, models, \
    filtwidth_yr, filtwidth_km, dt_cum, x_stddev, y_stddev, mask2, cmap_wrap
    global cum_org, cum_filt, gpu
    global interpolateflag

    #%% Set default
    tsadir = []
    filtwidth_km = 2
    filtwidth_yr = []
    deg_ramp = []
    hgt_linearflag = False
    hgt_min = 200 ## meter
    hgt_max = 10000 ## meter
    maskflag = True
    filterflag = True
    demerrflag = False
    inputresidflag = False
    interpolateflag = False
    gpu = False
    sbovl = False
    sbovl_abs = False
    tide = False
    iono = False
    naming = False
    try:
        n_para = len(os.sched_getaffinity(0))
    except:
        n_para = multi.cpu_count()

    os.environ["OMP_NUM_THREADS"] = "1"
    # Because np.linalg.lstsq use full CPU but not much faster than 1CPU.
    # Instead parallelize by multiprocessing

    range_str = []
    range_geo_str = []
    ex_range_str = []
    ex_range_geo_str = []

    cumname = 'cum.h5'

    cmap_vel = cmc.roma.reversed()
    cmap_noise_r = 'viridis_r'
    cmap_wrap = cmc.romaO
    q = multi.get_context('fork')
    compress = 'gzip'
    modelfile = ''
    nopngs = False

    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "ht:s:y:r:",
                           ["help", "demerr", "hgt_linear", "hgt_min=", "hgt_max=",
                            "nomask", "interpolate_nans", "nofilter", "n_para=", "range=", "range_geo=",
                            "ex_range=", "ex_range_geo=", "gpu", "from_model=", "nopngs", "sbovl", "sbovl_abs", "naming"])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                return 0
            elif o == '-t':
                tsadir = a
            elif o == '-s':
                filtwidth_km = float(a)
            elif o == '-y':
                filtwidth_yr = float(a)
            elif o == '-r':
                deg_ramp = a
            elif o == '--demerr':
                demerrflag = True
            elif o == '--hgt_linear':
                hgt_linearflag = True
            elif o == '--hgt_min':
                hgt_min = int(a)
            elif o == '--hgt_max':
                hgt_max = int(a)
            elif o == '--nomask':
                maskflag = False
            elif o == '--nofilter':
                filterflag = False
            elif o == '--interpolate_nans':
                interpolateflag = True
            elif o == '--n_para':
                n_para = int(a)
            elif o == '--range':
                range_str = a
            elif o == '--range_geo':
                range_geo_str = a
            elif o == '--ex_range':
                ex_range_str = a
            elif o == '--ex_range_geo':
                ex_range_geo_str = a
            elif o == '--gpu':
                gpu = True
            elif o == '--nopngs':
                nopngs = True
            elif o == '--sbovl':
                sbovl = True
            elif o == '--sbovl_abs':
                sbovl = True
                sbovl_abs = True
            elif o == '--naming':
                naming = True
            elif o == '--from_model':
                modelfile = a
                inputresidflag = True
            # elif o == '--tide':
            #     tide = True
            # elif o == '--iono':
            #     iono = True
            
        if not tsadir:
            raise Usage('No tsa directory given, -t is not optional!')
        elif not os.path.isdir(tsadir):
            raise Usage('No {} dir exists!'.format(tsadir))
        elif not os.path.exists(os.path.join(tsadir, cumname)):
            raise Usage('No {} exists in {}!'.format(cumname, tsadir))
        if range_str and range_geo_str:
            raise Usage('Both --range and --range_geo given, use either one not both!')
        if ex_range_str and ex_range_geo_str:
            raise Usage('Both --ex_range and --ex_range_geo given, use either one not both!')
        if gpu:
            print("\nGPU option is activated. Need cupy module.\n")
            import cupy as cp
        if modelfile:
            if not os.path.exists(modelfile):
                print('Specified model file does not exist: '+modelfile)
                modelfile = os.path.join(tsadir, 'model.h5')
                print('checking for '+modelfile)
                if not os.path.exists(modelfile):
                    inputresidflag = False
                    print('Warning, model file does not exist. Not using.\n')
    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2

    #%% Directory and file setting
    tsadir = os.path.abspath(tsadir)
    cumfile = os.path.join(tsadir, cumname)
    resultsdir = os.path.join(tsadir, 'results')
    infodir = os.path.join(tsadir, 'info')
    inparmfile = os.path.join(infodir,  '13parameters.txt')
    if not os.path.exists(inparmfile):  ## for old LiCSBAS13 <v1.2
        inparmfile = os.path.join(infodir, 'parameters.txt')
    outparmfile = os.path.join(infodir,  '16parameters.txt')

    pixsp_r = float(io_lib.get_param_par(inparmfile, 'pixel_spacing_r'))
    pixsp_a = float(io_lib.get_param_par(inparmfile, 'pixel_spacing_a'))
    x_stddev = filtwidth_km*1000/pixsp_r
    y_stddev = filtwidth_km*1000/pixsp_a

    wavelength = float(io_lib.get_param_par(inparmfile, 'wavelength')) #meter
    coef_r2m = -wavelength/4/np.pi*1000 #rad -> mm, positive is -LOS

    if wavelength > 0.2: ## L-band
        cycle = 1.5 # 2pi/cycle for comparison png
    elif wavelength <= 0.2: ## C-band
        if not sbovl:
            cycle = 3 # 3*2pi/cycle for comparison png
        else:
            cycle = 3  #TODO must be around 75?? because of the sbovl? I need to check MN

    filtincdir = os.path.join(tsadir, '16filt_increment')
    if os.path.exists(filtincdir): shutil.rmtree(filtincdir)
    os.mkdir(filtincdir)
    filtcumdir = os.path.join(tsadir, '16filt_cum')
    if os.path.exists(filtcumdir): shutil.rmtree(filtcumdir)
    os.mkdir(filtcumdir)

    #standard format
    vconstfile = os.path.join(resultsdir, 'vintercept.filt')
    velfile = os.path.join(resultsdir, 'vel.filt')

    cumh5 = h5.File(cumfile,'r')  ##open cum.h5 to read non-filtered data

    #%% Dates
    imdates = cumh5['imdates'][()].astype(str).tolist()
    if sbovl_abs:
        print('absoluting mode activated.')
        if 'cum_abs' in cumh5:
            cum_org = cumh5['cum_abs'][()]
            sbovl_suffix = '_abs'
        else:
            cum_org = cumh5['cum'][()]
            sbovl_suffix = ''
        print(f'suffix for sbovl_abs: {sbovl_suffix}')
        ##redefine the output files
        # vconstfile = os.path.join(resultsdir, f'vintercept_ransac{sbovl_suffix}.filt')
        # velfile = os.path.join(resultsdir, f'vel_ransac{sbovl_suffix}.filt')
        vconstfile = os.path.join(resultsdir, f'vintercept{sbovl_suffix}.filt')
        velfile = os.path.join(resultsdir, f'vel{sbovl_suffix}.filt')
    else:
        cum_org = cumh5['cum'][()]
        # if sbovl:
        #     if tide:
        #         tide_org = cumh5['tide'][()]
        #     if iono:
        #         iono_org = cumh5['iono'][()]
                
    
    # #%% If tide/iono are all-NaN for an epoch, set that correction epoch to 0 (skip correction), separately for each
    # if sbovl:
    #     #tide
    #     if tide:
    #         tide_allnan = np.all(np.isnan(tide_org), axis=(1, 2))
    #         if np.any(tide_allnan):
    #             bad_ix = np.where(tide_allnan)[0]
    #             bad_dates = [imdates[i] for i in bad_ix]
    #             print(f"WARNING: Tide is full-NaN for {len(bad_ix)} epochs. "
    #                 f"Skipping tide (set to 0) on: {bad_dates}", flush=True)
    #             tide_org[tide_allnan, :, :] = 0.0
    #     #iono
    #     if iono:
    #         iono_allnan = np.all(np.isnan(iono_org), axis=(1, 2))
    #         if np.any(iono_allnan):
    #             bad_ix = np.where(iono_allnan)[0]
    #             bad_dates = [imdates[i] for i in bad_ix]
    #             print(f"WARNING: Iono is full-NaN for {len(bad_ix)} epochs. "
    #                 f"Skipping iono (set to 0) on: {bad_dates}", flush=True)
    #             iono_org[iono_allnan, :, :] = 0.0

    n_im, length, width = cum_org.shape

    #%% tide and iono removal for sbovl before filtering
    if sbovl:
        if maskflag:
            maskfile = os.path.join(resultsdir, 'mask')
            mask = io_lib.read_img(maskfile, length, width)
            mask[mask==0] = np.nan ## 0->nan
            # if mask is involved, apply to cum already:
            # cum_org = cum_org * mask[np.newaxis,:,:]
            # 20240711: no, we will always want to filter through everthing and only then apply mask at the end..
            # if this is not the case and you want to really drop pixels that are inputs to the filter, please uncomment the line above
        else:
            mask = np.ones((length, width), dtype=np.float32)
            mask[np.isnan(cum_org[0, :, :])] = np.nan
        
        if not sbovl_abs: 
            infodir = os.path.join(tsadir, 'info')
            ref13file = os.path.join(infodir, '13ref.txt')
            ref12file = os.path.join(infodir, '12ref.txt')
            with open(ref13file, "r") as f:
                ref13area = f.read().split()[0]  # str, x1/x2/y1/y2
            with open(ref12file, "r") as f:
                ref12area = f.read().split()[0]  # str, x1/x2/y1/y2

            ref13x1, ref13x2, ref13y1, ref13y2 = [int(s) for s in re.split('[:/]', ref13area)]
            ref12x1, ref12x2, ref12y1, ref12y2 = [int(s) for s in re.split('[:/]', ref12area)]

            # --- Reference: Cumulative displacement ---
            refpoint_cum_org = np.nanmean(cum_org[:, ref13y1:ref13y2, ref13x1:ref13x2], axis=(1,2))
            if np.any(np.isnan(refpoint_cum_org)):
                print("Some NaNs detected in refpoint_cum_org — replacing with nanmedian across all pixels.")
                refpoint_cum_org = np.where(
                    np.isnan(refpoint_cum_org),
                    np.nanmedian(cum_org, axis=(1,2)),
                    refpoint_cum_org
                )
            if np.any(np.isnan(refpoint_cum_org)):
                print("Still NaNs in refpoint_cum_org — interpolating over time.")
                time_idx = np.arange(refpoint_cum_org.shape[0])
                valid = ~np.isnan(refpoint_cum_org)
                if np.sum(valid) >= 2:
                    f_interp = interp1d(time_idx[valid], refpoint_cum_org[valid], kind='linear',
                                        bounds_error=False, fill_value='extrapolate')
                    refpoint_cum_org = f_interp(time_idx)
                else:
                    print("WARNING: Not enough valid points in refpoint_cum_org to interpolate.")
                    refpoint_cum_org[:] = 0

            
            # # --- Reference: Tide correction ---
            # if tide:
            #     refpoint_tide = np.nanmean(tide_org[:, ref13y1:ref13y2, ref13x1:ref13x2], axis=(1,2))
            #     if np.any(np.isnan(refpoint_tide)):
            #         print("Some NaNs detected in refpoint_tide — replacing with nanmedian across all pixels.")
            #         refpoint_tide = np.where(
            #             np.isnan(refpoint_tide),
            #             np.nanmedian(tide_org, axis=(1,2)),
            #             refpoint_tide
            #         )
            #     # refpoint_tide = np.nanmedian(tide_org, axis=(1, 2)) #median here #MN maybe we can open this in the future. 
            #     if np.any(np.isnan(refpoint_tide)):
            #         print("Still NaNs in refpoint_tide — interpolating over time.")
            #         time_idx = np.arange(refpoint_tide.shape[0])
            #         valid = ~np.isnan(refpoint_tide)
            #         if np.sum(valid) >= 2:
            #             f_interp = interp1d(time_idx[valid], refpoint_tide[valid], kind='linear',
            #                                 bounds_error=False, fill_value='extrapolate')
            #             refpoint_tide = f_interp(time_idx)
            #         else:
            #             print("WARNING: Not enough valid points in refpoint_tide to interpolate.")
            #             refpoint_tide[:] = 0
            # else:
            #     refpoint_tide = None


            # # --- Reference: Ionospheric correction ---
            # if iono:
            #     refpoint_iono = np.nanmean(iono_org[:, ref13y1:ref13y2, ref13x1:ref13x2], axis=(1,2))
            #     # if np.any(np.isnan(refpoint_iono)):
            #     #     refpoint_iono =np.nanmean(iono_org[:, ref12y1:ref12y2, ref12x1:ref12x2], axis=(1,2))
            #     if np.any(np.isnan(refpoint_iono)):
            #         print("Some NaNs detected in refpoint_iono — replacing with nanmedian across all pixels.")
            #         refpoint_iono = np.where(
            #             np.isnan(refpoint_iono),
            #             np.nanmedian(iono_org, axis=(1,2)),
            #             refpoint_iono
            #         )
            #     # refpoint_iono = np.nanmedian(iono_org, axis=(1, 2)) #median here #MN
            #     if np.any(np.isnan(refpoint_iono)):
            #         print("Still NaNs in refpoint_iono — interpolating over time.")
            #         time_idx = np.arange(refpoint_iono.shape[0])
            #         valid = ~np.isnan(refpoint_iono)
            #         if np.sum(valid) >= 2:
            #             f_interp = interp1d(time_idx[valid], refpoint_iono[valid], kind='linear',
            #                                 bounds_error=False, fill_value='extrapolate')
            #             refpoint_iono = f_interp(time_idx)
            #         else:
            #             print("WARNING: Not enough valid points in refpoint_iono to interpolate.")
            #             refpoint_iono[:] = 0
            # else:
            #     refpoint_iono = None

            # --- Reference each dataset ---
            for i in range(n_im):
                cum_org[i, :, :] -= refpoint_cum_org[i]
                # if tide:
                #     tide_org[i, :, :] -= refpoint_tide[i]
                # if iono:
                #     iono_org[i, :, :] -= refpoint_iono[i]

            # # --- Finally, remove full tide and iono (already referenced) from cumulative
            # if tide:
            #     cum_org -= tide_org
            # if iono:
            #     cum_org -= iono_org

        # --- Else case for sbovl_abs (presumably)
        else:
            print('Skipping back referencing to stable point for sbovl + daz mode')



    if n_para > n_im:
        n_para = n_im

    ### Calc dt in year
    imdates_dt = ([dt.datetime.strptime(imd, '%Y%m%d').toordinal() for imd in imdates])
    dt_cum = np.float32((np.array(imdates_dt)-imdates_dt[0])/365.25)

    ### temporal filter width
    if not filtwidth_yr and filtwidth_yr != 0:
        filtwidth_yr = np.diff(dt_cum).mean() * 3  #dt_cum[-1]/(n_im-1)*3 ## avg interval*3

    ####define the cum_filt file
    if naming:
        cumffile = os.path.join(tsadir, f'cum_filt_s{filtwidth_km}_t{int(filtwidth_yr*365.25)}.h5')
    else:
        cumffile = os.path.join(tsadir, f'cum_filt.h5') #s{filtwidth_km}_t{int(filtwidth_yr*365.25)} MN
    
    if os.path.exists(cumffile): os.remove(cumffile)
    cumfh5 = h5.File(cumffile,'w') #open cum_filt.h5 to write filtered data
    # 

    ### Save dates and other info into cumf
    cumfh5.create_dataset('imdates', data=cumh5['imdates'])
    cumfh5.create_dataset('gap', data=cumh5['gap'], compression=compress)
    if 'bperp' in list(cumh5.keys()): ## if dummy, no bperp field
        cumfh5.create_dataset('bperp', data=cumh5['bperp'])
    else:
        print('No bperp field found in {}. Skip.'.format(cumname))

    if 'corner_lat' in list(cumh5.keys()):
        lat1 = float(cumh5['corner_lat'][()])
        lon1 = float(cumh5['corner_lon'][()])
        dlat = float(cumh5['post_lat'][()])
        dlon = float(cumh5['post_lon'][()])
        cumfh5.create_dataset('corner_lat', data=cumh5['corner_lat'])
        cumfh5.create_dataset('corner_lon', data=cumh5['corner_lon'])
        cumfh5.create_dataset('post_lat', data=cumh5['post_lat'])
        cumfh5.create_dataset('post_lon', data=cumh5['post_lon'])
    else: ## not geocoded
        print('No latlon field found in {}. Skip.'.format(cumname))


    ### hgt_linear
    if hgt_linearflag:
        hgtfile = os.path.join(resultsdir, 'hgt')
        if not os.path.exists(hgtfile):
            print('\nERROR: No hgt file exist in results dir!', file=sys.stderr)
            print('--hgt_linear option cannot be used.', file=sys.stderr)
            return 2
        hgt = io_lib.read_img(hgtfile, length, width)
        Ufile = os.path.join(resultsdir, 'U')
        if os.path.exists(Ufile):
            print('scaling by incidence angle')
            cosinc = io_lib.read_img(Ufile, length, width)
            hgt = hgt / cosinc
        hgt[np.isnan(hgt)] = 0
    else:
        hgt = []

    ### demerr
    if demerrflag:
        bperp = np.float32(np.array(cumh5['bperp'][()].tolist()))
        demerrfile = os.path.join(resultsdir, 'demerr')
        

    
    #%% --range[_geo] and --ex_range[_geo]
    if range_str: ## --range
        if not tools_lib.read_range(range_str, width, length):
            print('\nERROR in {}\n'.format(range_str), file=sys.stderr)
            return 1
        else:
            x1, x2, y1, y2 = tools_lib.read_range(range_str, width, length)
            range_str = '{}:{}/{}:{}'.format(x1, x2, y1, y2)
    elif range_geo_str: ## --range_geo
        if not tools_lib.read_range_geo(range_geo_str, width, length, lat1, dlat, lon1, dlon):
            print('\nERROR in {}\n'.format(range_geo_str), file=sys.stderr)
            return 1
        else:
            x1, x2, y1, y2 = tools_lib.read_range_geo(range_geo_str, width, length, lat1, dlat, lon1, dlon)
            range_str = '{}:{}/{}:{}'.format(x1, x2, y1, y2)

    if ex_range_str: ## --ex_range
        if not tools_lib.read_range(ex_range_str, width, length):
            print('\nERROR in {}\n'.format(ex_range_str), file=sys.stderr)
            return 1
        else:
            ex_x1, ex_x2, ex_y1, ex_y2 = tools_lib.read_range(ex_range_str, width, length)
            ex_range_str = '{}:{}/{}:{}'.format(ex_x1, ex_x2, ex_y1, ex_y2)
    elif ex_range_geo_str: ## --ex_range_geo
        if not tools_lib.read_range_geo(ex_range_geo_str, width, length, lat1, dlat, lon1, dlon):
            print('\nERROR in {}\n'.format(ex_range_geo_str), file=sys.stderr)
            return 1
        else:
            ex_x1, ex_x2, ex_y1, ex_y2 = tools_lib.read_range_geo(ex_range_geo_str, width, length, lat1, dlat, lon1, dlon)
            ex_range_str = '{}:{}/{}:{}'.format(ex_x1, ex_x2, ex_y1, ex_y2)

    ### Make range mask
    mask2 = np.ones((length, width), dtype=np.float32)
    if range_str:
        mask2 = mask2*np.nan
        mask2[y1:y2, x1:x2] = 1
    if ex_range_str:
        mask2[ex_y1:ex_y2, ex_x1:ex_x2] = np.nan


    #%% Display settings
    print('')
    print('Size of image (w,l)      : {0}, {1}'.format(width, length))
    print('Number of images         : {}'.format(n_im))
    print('Width of filter in space : {} km ({:.1f}x{:.1f} pixel)'.format(filtwidth_km, x_stddev, y_stddev))
    print('Width of filter in time  : {:.3f} yr ({} days)'.format(filtwidth_yr, int(filtwidth_yr*365.25)))
    print('Deramp flag              : {}'.format(deg_ramp), flush=True)
    print('hgt-linear flag          : {}'.format(hgt_linearflag), flush=True)
    if hgt_linearflag:
        print('Minimum hgt              : {} m'.format(hgt_min), flush=True)
        print('Maximum hgt              : {} m'.format(hgt_max), flush=True)
    if range_str:
        print('Range                    : {}'.format(range_str), flush=True)
    if ex_range_str:
        print('Excluded range           : {}'.format(ex_range_str), flush=True)
    with open(outparmfile, "w") as f:
        print('filtwidth_km:  {}'.format(filtwidth_km), file=f)
        print('filtwidth_xpixels:  {:.1f}'.format(x_stddev), file=f)
        print('filtwidth_ypixels:  {:.1f}'.format(y_stddev), file=f)
        print('filtwidth_yr:  {:.3f}'.format(filtwidth_yr), file=f)
        print('filtwidth_day:  {}'.format(int(filtwidth_yr*365.25)), file=f)
        print('deg_ramp:  {}'.format(deg_ramp), file=f)
        print('demerr:  {}'.format(demerrflag * 1), file=f)
        print('hgt_linear:  {}'.format(hgt_linearflag*1), file=f)
        print('hgt_min: {}'.format(hgt_min), file=f)
        print('hgt_max: {}'.format(hgt_max), file=f)
        print('range: {}'.format(range_str), file=f)
        print('ex_range: {}'.format(ex_range_str), file=f)

    # 
    #%% Load Mask (1: unmask, 0: mask, nan: no cum data)
    if maskflag:
        maskfile = os.path.join(resultsdir, 'mask')
        mask = io_lib.read_img(maskfile, length, width)
        mask[mask==0] = np.nan ## 0->nan
        # if mask is involved, apply to cum already:
        # cum_org = cum_org * mask[np.newaxis,:,:]
        # 20240711: no, we will always want to filter through everthing and only then apply mask at the end..
        # if this is not the case and you want to really drop pixels that are inputs to the filter, please uncomment the line above
    else:
        mask = np.ones((length, width), dtype=np.float32)
        mask[np.isnan(cum_org[0, :, :])] = np.nan

    
    #%% First, deramp and hgt-linear if indicated
    cum = np.zeros(cum_org.shape, dtype=np.float32)*np.nan
    if not deg_ramp and not hgt_linearflag:
        cum = cum_org  #TODO check here again.
        del cum_org
    else:
        if not deg_ramp:
            print('\nEstimate hgt-linear component,', flush=True)
        elif not hgt_linearflag:
            print('\nDeramp ifgs with the degree of {},'.format(deg_ramp), flush=True)
        else:
            print('\nDeramp ifgs with the degree of {} and hgt-linear,'.format(deg_ramp), flush=True)

        if n_para == 1 or gpu:
            if gpu: print('With GPU')
            models = np.zeros(n_im, dtype=object)
            for i in range(n_im):
                cum[i, :, :], models[i] = deramp_wrapper(i)
        else:
            print('with {} parallel processing...'.format(n_para), flush=True)
            ### Parallel processing
            p = q.Pool(n_para)
            _result = np.array(p.map(deramp_wrapper, range(n_im)), dtype=object)
            p.close()
            del args

            models = _result[:, 1]
            for i in range(n_im):
                cum[i, :, :] = _result[i, 0]
            del _result

        if nopngs:
            print('Skipping creation of increment pngs')
        else:
            ### Only for output increment png files
            print('\nCreate png for increment with {} parallel processing...'.format(n_para), flush=True)
            p = q.Pool(n_para)
            p.map(deramp_wrapper2, range(1, n_im))
            p.close()

        del cum_org

        # %% if the input should be residuals from given model
    if inputresidflag:
        modelh5 = h5.File(modelfile, 'r')
        cum_model = modelh5['cum_model'][()]
        cum = cum - cum_model
        del cum_model
        modelh5.close()
        # print('in dev')
        # load modelfile model_cum as h5, and remove from cum to get resids that will then get processed

        # %% DEM err
    if demerrflag:
        print('\nEstimate DEM error component,', flush=True)
        # 20230116 working
        G = np.stack((np.ones_like(dt_cum), dt_cum, bperp), axis=1)
        demerr = np.zeros((length, width), dtype=np.float32) * np.nan
        _vconst = np.zeros((length, width), dtype=np.float32) * np.nan
        _vel = np.zeros((length, width), dtype=np.float32) * np.nan

        bool_unnan = ~np.isnan(cum[0, :, :]*mask).reshape(length, width)  ## not all nan # 20241107 added mask
        cum_pt = cum.reshape(n_im, length * width)[:, bool_unnan.ravel()]  # n_im x n_pt
        n_pt_unnan = bool_unnan.sum()
        vconst_tmp = np.zeros((n_pt_unnan), dtype=np.float32) * np.nan
        vel_tmp = np.zeros((n_pt_unnan), dtype=np.float32) * np.nan
        demerr_tmp = np.zeros((n_pt_unnan), dtype=np.float32) * np.nan

        bool_nonan_pt = np.all(~np.isnan(cum_pt), axis=0)

        ### First, calc point without nan
        print('  First, solving {0:6}/{1:6}th points with full cum...'.format(bool_nonan_pt.sum(), n_pt_unnan),
              flush=True)
        vconst_tmp[bool_nonan_pt], vel_tmp[bool_nonan_pt], demerr_tmp[bool_nonan_pt] = \
        np.linalg.lstsq(G, cum_pt[:, bool_nonan_pt], rcond=None)[0]

        ### Next, calc point with nan
        print('  Next, solving {0:6}/{1:6}th points with nan in cum...'.format((~bool_nonan_pt).sum(), n_pt_unnan),
              flush=True)

        mask_cum = ~np.isnan(cum_pt[:, ~bool_nonan_pt])
        vconst_tmp[~bool_nonan_pt], vel_tmp[~bool_nonan_pt], demerr_tmp[~bool_nonan_pt] = inv_lib.censored_lstsq_slow(G,
                                                                                                                      cum_pt[
                                                                                                                      :,
                                                                                                                      ~bool_nonan_pt],
                                                                                                                      mask_cum)
        _vconst[bool_unnan], _vel[bool_unnan], demerr[bool_unnan] = vconst_tmp, vel_tmp, demerr_tmp

        demerr.tofile(demerrfile)

        # Compute DEM err phase and subtract
        for i in range(n_im):
            ## Output comparison image of DEM error
            data3 = [np.angle(np.exp(1j * (data / coef_r2m / cycle)) * cycle) for data in
                     [cum[i, :, :] * mask, demerr * bperp[i], cum[i, :, :] * mask - demerr * bperp[i]]]
            pngfile = os.path.join(filtcumdir, imdates[i] + '_demerr.png')
            deramp_title3 = ['Before DEMerr corr ({}pi/cycle)'.format(cycle * 2),
                             'DEM err phase (bperp:{:.0f}m)'.format(bperp[i]),
                             'After DEMerr corr ({}pi/cycle)'.format(cycle * 2)]
            plot_lib.make_3im_png(data3, pngfile, cmap_wrap, deramp_title3, vmin=-np.pi, vmax=np.pi, cbar=False)

            # Subtract
            cum[i, :, :] = cum[i, :, :] - demerr * bperp[i]


    if filterflag:
        #%% Filter each image
        cum_filt = np.zeros((n_im, length, width), dtype=np.float32)

        print('\nHP filter in time, LP filter in space,', flush=True)
        if filtwidth_km == 0.0:
            print('\n(skipping spatial filter)', flush=True)
        if filtwidth_yr == 0.0:
            print('\n(skipping temporal filter)', flush=True)
        if n_para == 1:
            for i in range(n_im):
                cum_filt[i, :, :] = np.float32(filter_wrapper(i))
        else:
            print('with {} parallel processing...'.format(n_para), flush=True)
            ### Parallel processing
            p = q.Pool(n_para)
            cum_filt[:, :, :] = np.array(p.map(filter_wrapper, range(n_im)), dtype=np.float32)
            p.close()


        ### Only for output increment png files
        print('\nCreate png for increment with {} parallel processing...'.format(n_para), flush=True)
        p = q.Pool(n_para)
        p.map(filter_wrapper2, range(1, n_im))
        p.close()
    else:
        # not filtering
        cum_filt = cum

    # 
    #%% Find stable ref point
    if not sbovl_abs: 
        print('\nFind stable reference point...', flush=True)
        ### Compute RMS of time series with reference to all points
        sumsq_cum_wrt_med = np.zeros((length, width), dtype=np.float32)
        for i in range(n_im):
            sumsq_cum_wrt_med = sumsq_cum_wrt_med + (cum_filt[i, :, :]-np.nanmedian(cum_filt[i, :, :]))**2
            ### we do not want ref point to contain nans
            sumsq_cum_wrt_med[np.isnan(cum[i, :, :])] = np.nan
        rms_cum_wrt_med = np.sqrt(sumsq_cum_wrt_med/n_im)*mask

        ### Mask by minimum n_gap
        n_gap = io_lib.read_img(os.path.join(resultsdir, 'n_gap'), length, width)
        min_n_gap = np.nanmin(n_gap)
        mask_n_gap = np.float32(n_gap==min_n_gap)
        mask_n_gap[mask_n_gap==0] = np.nan
        rms_cum_wrt_med = rms_cum_wrt_med*mask_n_gap
        #
        #TODO I have closed here as I get some nan errors for sbovl rms_cum_wrt_med = nan,  refy1s, refx1s = refy1s[0], refx1s[0] ## Only first index IndexError: index 0 is out of bounds for axis 0 with size 0
        ### Find stable reference
        min_rms = np.nanmin(rms_cum_wrt_med)
        refy1s, refx1s = np.where(rms_cum_wrt_med==min_rms)
        refy1s, refx1s = refy1s[0], refx1s[0] ## Only first index
        refy2s, refx2s = refy1s+1, refx1s+1
        print('Selected ref: {}:{}/{}:{}'.format(refx1s, refx2s, refy1s, refy2s), flush=True)

        # Cleaning memory - means need to get the refpoint_cum_org first
        refpoint_cum_org = cum[:, refy1s, refx1s]
        del cum

    # adding back model to the filtered residuals
    if inputresidflag:
        # read again
        modelh5 = h5.File(modelfile, 'r')
        cum_model = modelh5['cum_model'][()]
        cum_filt = cum_filt + cum_model
        del cum_model
        modelh5.close()

    ### Referencing cumulative displacement to new stable ref
    if not sbovl_abs:
        refpoint_cum_filt = cum_filt[:, refy1s, refx1s]
        for i in range(n_im):
            # cum_filt[i, :, :] = cum_filt[i, :, :] - refpoint_cum_org[i]  #cum[i, refy1s, refx1s]
            cum_filt[i, :, :] = cum_filt[i, :, :] - refpoint_cum_filt[i]
        #referecing the first epoch
        cum_filt = cum_filt - cum_filt[0, :, :]
    else:
        print('Skipping back referencing to stable point for sbovl + daz mode')

    if not sbovl_abs: ##TODO I have closed here as I get some nan errors for sbovl 
        ### Save image
        rms_cum_wrt_med_file = os.path.join(infodir, '16rms_cum_wrt_med')
        with open(rms_cum_wrt_med_file, 'w') as f:
            rms_cum_wrt_med.tofile(f)
        pngfile = os.path.join(infodir, '16rms_cum_wrt_med.png')
        plot_lib.make_im_png(rms_cum_wrt_med, pngfile, cmap_noise_r, 'RMS of cum wrt median (mm)', np.nanpercentile(rms_cum_wrt_med, 1), np.nanpercentile(rms_cum_wrt_med, 99))

        ### Save ref
        cumfh5.create_dataset('refarea', data='{}:{}/{}:{}'.format(refx1s, refx2s, refy1s, refy2s))
        refsfile = os.path.join(infodir, '16ref.txt')
        with open(refsfile, 'w') as f:
            print('{}:{}/{}:{}'.format(refx1s, refx2s, refy1s, refy2s), file=f)

        if 'corner_lat' in list(cumh5.keys()): ## Geocoded
            ### Make ref_stable.kml
            reflat = lat1+dlat*refy1s
            reflon = lon1+dlon*refx1s
            io_lib.make_point_kml(reflat, reflon, os.path.join(infodir, '16ref.kml'))


    #%% Calc filtered velocity
    print('\nCalculate velocity of filtered time series...', flush=True)
    if inputresidflag:
        print('\n(note you may want to check LiCSBAS_cum2vel.py for more options than linear trend only)', flush=True)
        print('')

    G = np.stack((np.ones_like(dt_cum), dt_cum), axis=1)
    vconst = np.zeros((length, width), dtype=np.float32)*np.nan
    vel = np.zeros((length, width), dtype=np.float32)*np.nan

    bool_unnan = ~np.isnan(cum_filt[0, :, :]).reshape(length, width) ## not all nan
    cum_pt = cum_filt.reshape(n_im, length*width)[:, bool_unnan.ravel()] #n_im x n_pt
    n_pt_unnan = bool_unnan.sum()
    vconst_tmp = np.zeros(n_pt_unnan, dtype=np.float32)*np.nan
    vel_tmp = np.zeros(n_pt_unnan, dtype=np.float32)*np.nan

    bool_nonan_pt = np.all(~np.isnan(cum_pt), axis=0)
    
    ### First, calc vel point without nan
    print('  First, solving {0:6}/{1:6}th points with full cum...'.format(bool_nonan_pt.sum(), n_pt_unnan), flush=True)
    vconst_tmp[bool_nonan_pt], vel_tmp[bool_nonan_pt] = np.linalg.lstsq(G, cum_pt[:, bool_nonan_pt], rcond=None)[0]

    ### Next, calc vel point with nan
    print('  Next, solving {0:6}/{1:6}th points with nan in cum...'.format((~bool_nonan_pt).sum(), n_pt_unnan), flush=True)

    mask_cum = ~np.isnan(cum_pt[:, ~bool_nonan_pt])
    vconst_tmp[~bool_nonan_pt], vel_tmp[~bool_nonan_pt] = inv_lib.censored_lstsq_slow(G, cum_pt[:, ~bool_nonan_pt], mask_cum)
    vconst[bool_unnan], vel[bool_unnan] = vconst_tmp, vel_tmp

    vconst.tofile(vconstfile)
    vel.tofile(velfile)

    if maskflag:
        vel_mskd = vel*mask
        vconst_mskd = vconst*mask
        vconst_mskd.tofile(vconstfile+'.mskd')
        vel_mskd.tofile(velfile+'.mskd')

    print('\nWriting to HDF5 file...', flush=True)
    if maskflag:
        print('\n(masked version)', flush=True)
        cum_filt = cum_filt * mask[np.newaxis, :, :]
    # 
    if sbovl_abs:
        cumfh5.create_dataset('vel' + sbovl_suffix, data=vel.reshape(length, width)*mask, compression=compress)
        cumfh5.create_dataset('vintercept' + sbovl_suffix, data=vconst.reshape(length, width)*mask, compression=compress)
        cumfh5.create_dataset('cum' + sbovl_suffix, data=cum_filt, compression=compress)
    else:
        cumfh5.create_dataset('vel', data=vel.reshape(length, width)*mask, compression=compress)
        cumfh5.create_dataset('vintercept', data=vconst.reshape(length, width)*mask, compression=compress)
        cumfh5.create_dataset('cum', data=cum_filt, compression=compress)


    #%% Add info and close
    cumfh5.create_dataset('filtwidth_yr', data=filtwidth_yr)
    cumfh5.create_dataset('filtwidth_km', data=filtwidth_km)
    cumfh5.create_dataset('deramp_flag', data=deg_ramp)
    cumfh5.create_dataset('hgt_linear_flag', data=hgt_linearflag*1)
    cumfh5.create_dataset('demerr_flag', data=demerrflag * 1)
    cumfh5.create_dataset('masked', data=maskflag * 1)

    indices = ['coh_avg', 'hgt', 'n_loop_err', 'n_unw', 'slc.mli',
               'maxTlen', 'n_gap', 'n_ifg_noloop', 'resid_rms',
               'E.geo', 'N.geo', 'U.geo']
    for index in indices:
        if index in list(cumh5.keys()):
            cumfh5.create_dataset(index, data=cumh5[index])
        else:
            print('  No {} field found in {}. Skip.'.format(index, cumname))

    indices2 = ['mask', 'vstd', 'stc']
    for index in indices2:
        file = os.path.join(resultsdir, index)
        if os.path.exists(file):
            data = io_lib.read_img(file, length, width)
            cumfh5.create_dataset(index, data=data, compression=compress)
        else:
            print('  {} not exist in results dir. Skip'.format(index))

    cumh5.close()
    cumfh5.close()

    # 
    #%% Output image
    if sbovl_abs:
        pngfile = os.path.join(resultsdir,f'vel{sbovl_suffix}.filt.png')
    else:
        pngfile = os.path.join(resultsdir,'vel.filt.png')
    title = 'Filtered velocity (mm/yr)'
    vmin = np.nanpercentile(vel, 1)
    vmax = np.nanpercentile(vel, 99)
    plot_lib.make_im_png(vel, pngfile, cmap_vel, title, vmin, vmax)

    ## vintercept
    if sbovl_abs:
        pngfile = os.path.join(resultsdir,f'vintercept{sbovl_suffix}.filt.png')
    else:
        pngfile = os.path.join(resultsdir,'vintercept.filt.png')
    title = 'Intercept of filtered velocity (mm)'
    vmin = np.nanpercentile(vconst, 1)
    vmax = np.nanpercentile(vconst, 99)
    plot_lib.make_im_png(vconst, pngfile, cmap_vel, title, vmin, vmax)

    if demerrflag:
        pngfile = os.path.join(resultsdir, 'demerr.png')
        title = 'Coefficient of DEM error phase (mm/m)'
        vmin = np.nanpercentile(demerr, 1)
        vmax = np.nanpercentile(demerr, 99)
        plot_lib.make_im_png(demerr, pngfile, cmap_vel, title, vmin, vmax)


    if maskflag:
        if sbovl_abs:
            pngfile = os.path.join(resultsdir,f'vel{sbovl_suffix}.filt.mskd.png')
        else:
            pngfile = os.path.join(resultsdir,'vel.filt.mskd.png')
        title = 'Masked filtered velocity (mm/yr)'
        vmin = np.nanpercentile(vel_mskd, 1)
        vmax = np.nanpercentile(vel_mskd, 99)
        plot_lib.make_im_png(vel_mskd, pngfile, cmap_vel, title, vmin, vmax)

        ## vintercept
        if sbovl_abs:
            pngfile = os.path.join(resultsdir,f'vintercept{sbovl_suffix}.filt.mskd.png')
        else:
            pngfile = os.path.join(resultsdir,'vintercept.filt.mskd.png')
        title = 'Masked intercept of filtered velocity (mm)'
        vmin = np.nanpercentile(vconst_mskd, 1)
        vmax = np.nanpercentile(vconst_mskd, 99)
        plot_lib.make_im_png(vconst_mskd, pngfile, cmap_vel, title, vmin, vmax)


    #%% Finish
    elapsed_time = time.time()-start
    hour = int(elapsed_time/3600)
    minite = int(np.mod((elapsed_time/60),60))
    sec = int(np.mod(elapsed_time,60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour,minite,sec))

    print('\n{} Successfully finished!!\n'.format(os.path.basename(argv[0])))
    print('Output: {}\n'.format(os.path.relpath(cumffile)), flush=True)

    print('To plot the time-series:')
    print('LiCSBAS_plot_ts.py -i {} --corrections &\n'.format(os.path.relpath(cumffile)))


#%%
def deramp_wrapper(i):
    if np.mod(i, 10) == 0:
        print("  {0:3}/{1:3}th image...".format(i, len(imdates)), flush=True)

    fit, model = tools_lib.fit2dh(cum_org[i, :, :]*mask*mask2, deg_ramp, hgt,
                                  hgt_min, hgt_max, gpu=gpu) ## fit is not masked
    _cum = cum_org[i, :, :]-fit

    if hgt_linearflag:
        fit_hgt = hgt*model[-1]*mask  ## extract only hgt-linear component
        cum_bf = _cum+fit_hgt ## After deramp before hgt-linear

        ## Output comparison image of hgt_linear
        std_before = np.nanstd(cum_bf)
        std_after = np.nanstd(_cum*mask)
        data3 = [np.angle(np.exp(1j*(data/coef_r2m/cycle))*cycle) for data in [cum_bf, fit_hgt, _cum*mask]]
        title3 = ['Before hgt-linear (STD: {:.1f}mm)'.format(std_before), 'hgt-linear phase ({:.1f}mm/km)'.format(model[-1]*1000), 'After hgt-linear (STD: {:.1f}mm)'.format(std_after)]
        pngfile = os.path.join(filtcumdir, imdates[i]+'_hgt_linear.png')
        plot_lib.make_3im_png(data3, pngfile, cmap_wrap, title3, vmin=-np.pi, vmax=np.pi, cbar=False)

        pngfile = os.path.join(filtcumdir, imdates[i]+'_hgt_corr.png')
        title = '{} ({:.1f}mm/km, based on {}<=hgt<={})'.format(imdates[i], model[-1]*1000, hgt_min, hgt_max)
        plot_lib.plot_hgt_corr(cum_bf, fit_hgt, hgt, title, pngfile)

    else:
        fit_hgt = 0  ## for plot deframp

    if deg_ramp:
        ramp = (fit-fit_hgt)*mask

        ## Output comparison image of deramp
        data3 = [np.angle(np.exp(1j*(data/coef_r2m/cycle))*cycle) for data in [cum_org[i, :, :]*mask, ramp, cum_org[i, :, :]*mask-ramp]]
        pngfile = os.path.join(filtcumdir, imdates[i]+'_deramp.png')
        deramp_title3 = ['Before deramp ({}pi/cycle)'.format(cycle*2), 'ramp phase (deg:{})'.format(deg_ramp), 'After deramp ({}pi/cycle)'.format(cycle*2)]
        plot_lib.make_3im_png(data3, pngfile, cmap_wrap, deramp_title3, vmin=-np.pi, vmax=np.pi, cbar=False)

    return _cum, model


#%%
def deramp_wrapper2(i):
    ## Only for output increment png files

    if hgt_linearflag and i != 0: ## first image has no increment
        ## fit_hgt, model
        fit_hgt = hgt*models[i][-1]*mask  ## extract only hgt-linear component
        fit_hgt1 = hgt*models[i-1][-1]*mask ## last one
        inc = (cum[i, :, :]-cum[i-1, :, :])*mask

        ## Output comparison image of hgt_linear for increment
        std_before = np.nanstd(inc+fit_hgt-fit_hgt1)
        std_after = np.nanstd(inc)
        data3 = [np.angle(np.exp(1j*(data/coef_r2m/cycle))*cycle) for data in [inc+fit_hgt-fit_hgt1, fit_hgt-fit_hgt1, inc]]
        title3 = ['Before hgt-linear (STD: {:.1f}mm)'.format(std_before), 'hgt-linear phase ({:.1f}mm/km)'.format((models[i][-1]-models[i-1][-1])*1000), 'After hgt-linear (STD: {:.1f}mm)'.format(std_after)]
        pngfile = os.path.join(filtincdir, '{}_{}_hgt_linear.png'.format(imdates[i-1], imdates[i]))
        plot_lib.make_3im_png(data3, pngfile, cmap_wrap, title3, vmin=-np.pi, vmax=np.pi, cbar=False)

        pngfile = os.path.join(filtincdir, '{}_{}_hgt_corr.png'.format(imdates[i-1], imdates[i]))
        title = '{}_{} ({:.1f}mm/km, based on {}<=hgt<={})'.format(imdates[i-1], imdates[i], (models[i][-1]-models[i-1][-1])*1000, hgt_min, hgt_max)
        plot_lib.plot_hgt_corr(inc+fit_hgt-fit_hgt1, fit_hgt-fit_hgt1, hgt, title, pngfile)

    else:
        fit_hgt = 0  ## for plot deframp
        fit_hgt1 = 0

    if deg_ramp and i != 0: ## first image has no increment
        ## ramp
        ramp = (cum_org[i, :, :]-cum[i, :, :]-fit_hgt)*mask
        ramp1 = (cum_org[i-1, :, :]-cum[i-1, :, :]-fit_hgt1)*mask
        inc_org = (cum_org[i, :, :]-cum_org[i-1, :, :])*mask

        ## Output comparison image of deramp for increment
        data3 = [np.angle(np.exp(1j*(data/coef_r2m/cycle))*cycle) for data in [inc_org, ramp-ramp1, inc_org-(ramp-ramp1)]]
        pngfile = os.path.join(filtincdir, '{}_{}_deramp.png'.format(imdates[i-1], imdates[i]))
        deramp_title3 = ['Before deramp ({}pi/cycle)'.format(cycle*2), 'ramp phase (deg:{})'.format(deg_ramp), 'After deramp ({}pi/cycle)'.format(cycle*2)]
        plot_lib.make_3im_png(data3, pngfile, cmap_wrap, deramp_title3, vmin=-np.pi, vmax=np.pi, cbar=False)


#%%
def filter_wrapper(i):
    n_im, length, width = cum.shape
    if np.mod(i, 10) == 0:
        print("  {0:3}/{1:3}th image...".format(i, n_im), flush=True)


    ### Second, HP in time
    if filtwidth_yr == 0.0:
        # print('No temporal filter applied', flush=True)
        cum_hpt = cum[i, :, :] ## No temporal filter
    else:
        time_diff_sq = (dt_cum[i]-dt_cum)**2

        ## Limit reading data within filtwidth_yr**8
        ixs = time_diff_sq < filtwidth_yr*8

        weight_factor = np.tile(np.exp(-time_diff_sq[ixs]/2/filtwidth_yr**2)[:, np.newaxis, np.newaxis], (1, length, width)) #len(ixs), length, width

        ## Take into account nan in cum
        weight_factor = weight_factor*(~np.isnan(cum[ixs, :, :]))

        ## Normalize weight
        with warnings.catch_warnings(): ## To silence warning by zero division
            warnings.simplefilter('ignore', RuntimeWarning)
            weight_factor = weight_factor/np.sum(weight_factor, axis=0)

        cum_lpt = np.nansum(cum[ixs, :, :]*weight_factor, axis=0)

        cum_hpt = cum[i, :, :] - cum_lpt


    ### Third, LP in space and subtract from original
    if filtwidth_km == 0.0:
        _cum_filt = cum[i, :, :] ## No spatial
        #if interpolateflag:
        #    # this will interpolate the cum_filt for nan points outside of the mask (that comes from step 15)
        #    _cum_filt = tools_lib.interpolate_2d(_cum_filt, method='linear') * mask
    else:
        with warnings.catch_warnings(): ## To silence warning
            if i ==0: cum_hpt = cum_hpt+sys.float_info.epsilon ##To distinguish from 0 of filtered nodata

#                warnings.simplefilter('ignore', FutureWarning)
            warnings.simplefilter('ignore', RuntimeWarning)
            kernel = Gaussian2DKernel(x_stddev, y_stddev)
            cum_hptlps = convolve_fft(cum_hpt*mask, kernel, fill_value=np.nan, allow_huge=True) ## fill edge 0 for interpolation
            cum_hptlps[cum_hptlps == 0] = np.nan ## fill 0 with nan

        _cum_filt = cum[i, :, :] - cum_hptlps
        #if interpolateflag:
        #    # this will interpolate the cum_filt for nan points outside of the mask (that comes from step 15)
        #    _cum_filt = tools_lib.interpolate_2d(_cum_filt, method='linear') * mask

        ### Output comparison image
        data3 = [np.angle(np.exp(1j*(data/coef_r2m/cycle))*cycle) for data in [cum[i, :, :]*mask, cum_hptlps*mask, _cum_filt*mask]]
        title3 = ['Before filter ({}pi/cycle)'.format(cycle*2), 'Filter phase ({}pi/cycle)'.format(cycle*2), 'After filter ({}pi/cycle)'.format(cycle*2)]
        pngfile = os.path.join(filtcumdir, imdates[i]+'_filt.png')
        plot_lib.make_3im_png(data3, pngfile, cmap_wrap, title3, vmin=-np.pi, vmax=np.pi, cbar=False)

    # Optionally interpolating the (unmasked) nan values of pixels
    if interpolateflag:
        if filtwidth_yr == 0.0: # in case of no temporal filter applied, let's interpolate only bilinearly in space
            _cum_filt = tools_lib.interpolate_2d(_cum_filt, method='linear') * mask
        else:  # but if it WAS applied, we can use the low pass filter version to estimate the cum value - should be better
            nanpixels = np.isnan(_cum_filt)
            _cum_filt[nanpixels] = cum_lpt[nanpixels]
            _cum_filt = _cum_filt * mask
        #
    return _cum_filt


#%%
def filter_wrapper2(i):
    ## Only for output increment png files
    dcum_filt = cum_filt[i, :, :]-cum_filt[i-1, :, :]
    dcum = cum[i, :, :]-cum[i-1, :, :]
    dcum_hptlps = dcum-dcum_filt

    ### Output comparison image for increment
    data3 = [np.angle(np.exp(1j*(data/coef_r2m/cycle))*cycle) for data in [dcum*mask, dcum_hptlps, dcum_filt*mask]]
    title3 = ['Before filter ({}pi/cycle)'.format(cycle*2),
              'Filter phase ({}pi/cycle)'.format(cycle*2),
              'After filter ({}pi/cycle)'.format(cycle*2)]
    pngfile = os.path.join(filtincdir, '{}_{}_filt.png'.format(imdates[i-1], imdates[i]))
    plot_lib.make_3im_png(data3, pngfile, cmap_wrap, title3, vmin=-np.pi, vmax=np.pi, cbar=False)


#%% main
if __name__ == "__main__":
    sys.exit(main())
