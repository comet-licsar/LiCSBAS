#!/usr/bin/env python3
"""

This script inverts the SB network of unw to obtain the time series and
velocity using NSBAS (López-Quiroz et al., 2009; Doin et al., 2011) approach.
A stable reference point is determined after the inversion. RMS of the time
series wrt median among all points is calculated for each point.
Then the point with minimum RMS and minimum n_gap is selected as new stable
reference point.

===============
Input & output files
===============
Inputs in GEOCml*/ :
 - yyyymmdd_yyyymmdd/
   - yyyymmdd_yyyymmdd.unw
   - yyyymmdd_yyyymmdd.cc
   
   - yyyymmdd_yyyymmdd.sbovldiff.adf.mm[.png] (if --sbovl is used)
   - yyyymmdd_yyyymmdd.sbovldiff.adf.cc (if --sbovl is used)
 - EQA.dem_par
 - slc.mli.par
 - baselines (may be dummy)
[- [ENU].geo]

Inputs in TS_GEOCml*/ :
 - info/
   - 11bad_ifg.txt
   - 12bad_ifg.txt
   - 12ref.txt
[-results/]
[  - coh_avg]
[  - hgt]
[  - n_loop_err]
[  - n_unw]
[  - slc.mli]

Outputs in TS_GEOCml*/ :
 - cum.h5             : Cumulative displacement (time-seires) in mm
 - results/
   - vel[.png]        : Velocity in mm/yr (positive means LOS decrease; uplift)
   - vintercept[.png] : Constant part of linear velocity (c for vt+c) in mm
   - resid_rms[.png]  : RMS of residual in mm
   - n_gap[.png]      : Number of gaps in SB network
   - n_ifg_noloop[.png] :  Number of ifgs with no loop
   - maxTlen[.png]    : Max length of continous SB network in year
 - info/
   - 13parameters.txt : List of used parameters
   - 13used_image.txt : List of used images
   - 13resid.txt      : List of RMS of residual for each ifg
   - 13ref.txt[kml]   : Auto-determined stable ref point
   - 13rms_cum_wrt_med[.png] : RMS of cum wrt median used for ref selection
 - 13increment/yyyymmdd_yyyymmdd.increment.png
     : Comparison between unw and inverted incremental displacement
 - 13resid/yyyymmdd_yyyymmdd.res.png : Residual for each ifg
 - network/network13*.png : Figures of the network

=====
Usage
=====
LiCSBAS13_sb_inv.py -d ifgdir [-t tsadir] [--inv_alg LS|WLS] [--mem_size float] [--gamma float] [--n_para int] [--n_unw_r_thre float] [--keep_incfile] [--gpu] [--singular] [--only_sb] [--nopngs] [--sbovl]
                 [--no_storepatches] [--load_patches] [--nullify_noloops] [--offsets eqoffsets.txt]

 -d  Path to the GEOCml* dir containing stack of unw data
 -t  Path to the output TS_GEOCml* dir.
 --inv_alg    Inversion algorithm (Default: LS)
   LS :       NSBAS Least Square with no weight
   WLS:       NSBAS Weighted Least Square
              Weight (variance) is calculated by (1-coh**2)/(2*coh**2)
 --mem_size   Max memory size for each patch in MB. (Default: 8000)
 --gamma      Gamma value for NSBAS inversion (Default: 0.0001)
 --n_para     Number of parallel processing (Default: # of usable CPU)
 --sbovl      Inversion of sbovl mm and cc values 
 --n_unw_r_thre
     Threshold of n_unw (number of used unwrap data)
     (Note this value is ratio to the number of images (epochs); i.e., 1.5*n_im)
     Larger number (e.g. 2.5) makes processing faster but result sparser.
     (Default: 1 and 0.5 for C- and L-band, respectively)
 --keep_incfile
     Not remove inc and resid files (Default: remove them)
 --gpu        Use GPU (Need cupy module)
 --singular   Use more economic computation  (unconstrained SBAS with filling gaps in second step; faster and less demanding solution but should be further improved)
 --only_sb    Perform only SB processing (skipping points with NaNs)
 --nopngs     Avoid generating some (unnecessary) PNG previews of increment residuals etc.
 --no_storepatches Don't store completed patch data [default: store patches in case of job timeout]
 --load_patches Load previously completed patches first [default: No, restart inversion]
 --input_units Units of the input data. Possible values: ['rad', 'mm', 'm']. Default: rad
 --offsets eqoffsets.txt  Estimate offsets read from external txt file - must have lines in the form of either yyyymmdd or yyyy-mm-dd
 --nullify_noloops   Nullifies data from ifgs not included in any loop, both ifg and pixel based noloop_ifgs. Uses data before nullification (optional step 12)
 --nullify_noloops_use_data_after_nullification  This would nullify noloop_ifgs after the nullification (usually not recommended)
"""
'''
skipping here as will do it as post-processing:
[--step_events eventepochs.txt]
 --step_events eventepochs.txt  Add inversion offset/steps at given epoch dates (read from eventepochs.txt in form of YYYYMMDD per line)
 20240717 ML
 - adding --step_events functionality
'''
#%% Change log
'''
20250903 ML+PEB
 - nullify_noloops also ignores full source interferograms -> dropping empty epochs
 - fix for filling no-gap nan values 
20241221 Muhammet Nergizci
 - check baseline file empty or not
20241207 ML
 - added singular_gauss (but do not show in help as it still needs some dev...)
20241102 MNergizci
 - added sbovl flag
20240423 ML
 - added parallelised version of 'singular' approach
20231101 Milan Lazecky, Leeds Uni
 - option for input data in metric units
v1.5.5 20230928 Lin Shen, Leeds Uni
 - Add a no loop check to exclude non-redundant interferograms for each point (recalculate the no-loop ifgs info)
v1.5.4 20230804 Jack McGrath, Leeds Uni
 - Add store and load patches option
v1.5.3 20211122 Milan Lazecky, Leeds Uni
 - use singular and only_sb to help make processing computationally economic
v1.5.2 20210311 Yu Morishita, GSI
 - Include noise indices and LOS unit vector in cum.h5 file
v1.5.1 20210309 Yu Morishita, GSI
 - Change default --mem_size to 8000
 - Speed up by reading cum data on memory
v1.5 20210305 Yu Morishita, GSI
 - Add GPU option
 - Speed up by activating n_para_inv and OMP_NUM_THREADS=1
v1.4.8 20210127 Yu Morishita, GSI
 - Automatically reduce mem_size if available RAM is small
v1.4.7 20201124 Yu Morishita, GSI
 - Comporess hdf5 file
v1.4.6 20201119 Yu Morishita, GSI
 - Change default cmap for wrapped phase from insar to SCM.romaO
v1.4.5 20201118 Yu Morishita, GSI
 - Again Bug fix of multiprocessing
v1.4.4 20201116 Yu Morishita, GSI
 - Bug fix of multiprocessing in Mac python>=3.8
v1.4.3 20201104 Yu Morishita, GSI
 - Bug fix when n_pt_unnan=0 in a patch
v1.4.2 20201028 Yu Morishita, GSI
 - Update how to get n_para
v1.4.1 20200925 Yu Morishita, GSI
 - Small bug fix in n_para
v1.4 20200909 Yu Morishita, GSI
 - n_core -> n_para
 - Parallelize making png
v1.3 20200902 Yu Morishita, GSI
 - Parallelize calculation of n_gap and n_ifg_noloop
 - Change n_core default to # of usable CPU
 - Fix n_core_inv=1 for inversion because it already uses multicore
v1.2 20200225 Yu Morishita, Uni of Leeds and GSI
 - Not output network pdf
 - Change color of png
 - Change name of parameters.txt to 13parameters.txt
 - Deal with cc file in uint8 format
 - Automatically find stable reference point
v1.1 20190829 Yu Morishita, Uni of Leeds and GSI
 - Remove cum.h5 if exists before creation
v1.0 20190730 Yu Morishita, Uni of Leeds and GSI
 - Original implementation
'''

#%% Import
from LiCSBAS_meta import *
import getopt
import os
import sys
import re
import time
import traceback
import psutil
import h5py as h5
import numpy as np
import datetime as dt
import multiprocessing as multi
import cmcrameri.cm as cmc
import LiCSBAS_io_lib as io_lib
import LiCSBAS_inv_lib as inv_lib
import LiCSBAS_tools_lib as tools_lib
import LiCSBAS_loop_lib as loop_lib
import LiCSBAS_plot_lib as plot_lib

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
    #ver="1.5.2"; date=20210311; author="Y. Morishita"
    print("\n{} ver{} {} {}".format(os.path.basename(argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(argv[0]), ' '.join(argv[1:])), flush=True)

    ## For parallel processing
    global n_para, n_para_gap, G, Aloop, unwpatch, hasdatapatch, imdates, incdir, ifgdir, length, width,\
        coef_r2m, ifgdates, ref_unw, cycle, keep_incfile, resdir, restxtfile, \
        cmap_vel, cmap_wrap, wavelength, nullify_noloops #, step_events


    #%% Set default
    ifgdir = []
    tsadir = []
    inv_alg = 'LS'
    gpu = False
    singular = False
    only_sb = False
    singular_gauss = False
    nopngs = False
    #noloop = False  # setting this later
    input_units = 'rad'
    nullify_noloops = False
    nullify_noloops_use_data_after_nullification = False
    sbovl = False
    
    try:
        n_para = len(os.sched_getaffinity(0))
    except:
        n_para = multi.cpu_count()

    os.environ["OMP_NUM_THREADS"] = "1"
    # Because np.linalg.lstsq use full CPU but not much faster than 1CPU.
    # Instead parallelize by multiprocessing

    memory_size = 8000
    gamma = 0.0001
    n_unw_r_thre = []
    keep_incfile = False

    cmap_vel = cmc.roma.reversed()
    cmap_noise = 'viridis'
    cmap_noise_r = 'viridis_r'
    cmap_wrap = cmc.romaO
    q = multi.get_context('fork')
    compress = 'gzip'
    store_patches = True
    load_patches = False
    #step_events = False
    offsetsflag = False
    offsets_dt = []
    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hd:t:",
                                       ["help",  "mem_size=", "input_units=", "gamma=",
                                        "n_unw_r_thre=", "keep_incfile", "nopngs", "nullify_noloops", "nullify_noloops_use_data_after_nullification",
                                        "inv_alg=", "n_para=", "gpu", "singular", "singular_gauss","only_sb", "no_storepatches", "load_patches",
                                        "offsets=", "sbovl"])
                                      #  "step_events="])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                return 0
            elif o == '-d':
                ifgdir = a
            elif o == '-t':
                tsadir = a
            elif o == '--mem_size':
                memory_size = float(a)
            elif o == '--gamma':
                gamma = float(a)
            elif o == '--input_units':
                input_units = a
            elif o == '--n_unw_r_thre':
                n_unw_r_thre = float(a)
            elif o == '--keep_incfile':
                keep_incfile = True
            elif o == '--inv_alg':
                inv_alg = a
            elif o == '--n_para':
                n_para = int(a)
            elif o == '--gpu':
                gpu = True
            elif o == '--singular':
                singular = True
            elif o == '--singular_gauss':
                singular = True
                singular_gauss = True
            #elif o == '--step_events':
            #    step_events = True
            #    stepevents_file = a
            elif o == '--only_sb':
                only_sb = True
            elif o == '--nopngs':
                nopngs = True
            elif o == '--nullify_noloops':
                nullify_noloops = True
            elif o == '--nullify_noloops_use_data_after_nullification':
                nullify_noloops_use_data_after_nullification = True
            elif o == '--no_storepatches':
                store_patches = False
            elif o == '--load_patches':
                load_patches = True
            elif o == '--sbovl':
                sbovl = True
            elif o == '--offsets':
                offsetsfile = a
                offsetsflag = True
	      

        if not ifgdir:
            raise Usage('No data directory given, -d is not optional!')
        elif not os.path.isdir(ifgdir):
            raise Usage('No {} dir exists!'.format(ifgdir))
        elif not os.path.exists(os.path.join(ifgdir, 'slc.mli.par')):
            raise Usage('No slc.mli.par file exists in {}!'.format(ifgdir))
        if gpu:
            print("\nGPU option is activated. Need cupy module.\n")
            import cupy as cp
        if sbovl:
            input_units= 'mm'
        else:
            if input_units not in ['rad', 'mm', 'm']:
                raise Usage("Wrong units of the input data - available options are: rad, mm, m.")
        if offsetsflag:
            if not os.path.exists(offsetsfile):
                raise Usage('Offsets file not provided')
            try:
                offsets = io_lib.read_epochlist(offsetsfile, outasdt=False)
                offsets_dt = io_lib.read_epochlist(offsetsfile, outasdt = True)
                if not offsets_dt:
                    print('Offsets file is empty, disabling offsets solution')
                    offsetsflag = False
            except:
                raise Usage('Offsets could not be loaded from '+offsetsfile)
        if inv_alg not in ['LS', 'WLS']:
            raise Usage("Wrong inversion algorithm - only LS or WLS are the options here")
        #if (inv_alg == 'WLS') and (singular == True):
        #    raise Usage('Sorry, --singular works only with LS but you requested WLS as inversion algorithm.')
        #if singular or only_sb:
        #    if n_para>1:
        #        print('WARNING: selected non-NSBAS regime. Current parallelism is under testing (give feedback please)')
        #        #n_para = 1
        #if step_events:
        #    if os.path.exists(stepevents_file):
        #        step_events = io_lib.read_epochlist(stepevents_file)
        #        if len(step_events)==0:
        #            print('WARNING, no step events provided. Cancelling step_events inversion routine')
        #            step_events = False
        #    else:
        #        raise Usage('The provided step events file does not exist.')
    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2


    #%% Directory settings
    ifgdir = os.path.abspath(ifgdir)

    if not tsadir:
        tsadir = os.path.join(os.path.dirname(ifgdir), 'TS_'+os.path.basename(ifgdir))

    if not os.path.isdir(tsadir):
        print('\nNo {} exists!'.format(tsadir), file=sys.stderr)
        return 1

    tsadir = os.path.abspath(tsadir)
    resultsdir = os.path.join(tsadir, 'results')
    infodir = os.path.join(tsadir, 'info')
    netdir = os.path.join(tsadir, 'network')

    bad_ifg11file = os.path.join(infodir, '11bad_ifg.txt')
    bad_ifg12file = os.path.join(infodir, '12bad_ifg.txt')
    bad_ifg120file = os.path.join(infodir, '120bad_ifg.txt')
    # if ref point selected using LiCSBAS120:
    reffile = os.path.join(infodir, '120ref.txt')
    if not os.path.exists(reffile):
        reffile = os.path.join(infodir, '12ref.txt')
    if not os.path.exists(reffile): ## for old LiCSBAS12 < v1.1
        reffile = os.path.join(infodir, 'ref.txt')
    #if not os.path.exists(reffile):
    #    print('You did not run step 12! This is strongly recommended to do. Proceeding further but expect lower quality results.')
    #    os.system('echo "0:0/0:0" > {0}'.format(reffile))
    #    if not os.path.exists(bad_ifg12file):
    #        os.system('touch {0}'.format(bad_ifg12file))

    incdir = os.path.join(tsadir,'13increment')
    if not os.path.exists(incdir): os.mkdir(incdir)

    resdir = os.path.join(tsadir,'13resid')
    if not os.path.exists(resdir): os.mkdir(resdir)
    restxtfile = os.path.join(infodir,'13resid.txt')

    cumh5file = os.path.join(tsadir,'cum.h5')

    if n_para > 32:
        # Emprically >32 does not make much faster despite using large resource
        n_para_inv = 32
    else:
        n_para_inv = n_para


    #%% Check files
    try:
        if not os.path.exists(bad_ifg11file):
            raise Usage('No 11bad_ifg.txt file exists in {}!'.format(infodir))
        if not sbovl:
            if not os.path.exists(bad_ifg12file):
                raise Usage('No 12bad_ifg.txt file exists in {}!'.format(infodir))
        if not os.path.exists(reffile):
            raise Usage('No 12ref.txt file exists in {}!'.format(infodir))
    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2


    #%% Set preliminaly reference
    with open(reffile, "r") as f:
        refarea = f.read().split()[0]  #str, x1/x2/y1/y2
    refx1, refx2, refy1, refy2 = [int(s) for s in re.split('[:/]', refarea)]


    #%% Read data information
    ### Get size
    mlipar = os.path.join(ifgdir, 'slc.mli.par')
    width = int(io_lib.get_param_par(mlipar, 'range_samples'))
    length = int(io_lib.get_param_par(mlipar, 'azimuth_lines'))
    speed_of_light = 299792458 #m/s
    radar_frequency = float(io_lib.get_param_par(mlipar, 'radar_frequency')) #Hz
    wavelength = speed_of_light/radar_frequency #meter
    # get coef to convert to mm
    if input_units == 'rad':
        coef_r2m = -wavelength/4/np.pi*1000 #rad -> mm, positive is -LOS
    elif input_units == 'mm':
        coef_r2m = 1 # expecting this positive in -LOS (subsidence is negative)
    elif input_units == 'm':
        coef_r2m = 1000 # expecting this positive in -LOS (subsidence is negative)

    ### Calc pixel spacing depending on IFG or GEOC, used in later spatial filter
    dempar = os.path.join(ifgdir, 'EQA.dem_par')
    width_geo = int(io_lib.get_param_par(dempar, 'width'))
    length_geo = int(io_lib.get_param_par(dempar, 'nlines'))
    dlat = float(io_lib.get_param_par(dempar, 'post_lat')) #negative
    dlon = float(io_lib.get_param_par(dempar, 'post_lon')) #positive
    lat1 = float(io_lib.get_param_par(dempar, 'corner_lat'))
    lon1 = float(io_lib.get_param_par(dempar, 'corner_lon'))
    if width == width_geo and length == length_geo: ## Geocoded
        print('\nIn geographical coordinates', flush=True)
        centerlat = lat1+dlat*(length/2)
        ra = float(io_lib.get_param_par(dempar, 'ellipsoid_ra'))
        recip_f = float(io_lib.get_param_par(dempar, 'ellipsoid_reciprocal_flattening'))
        rb = ra*(1-1/recip_f) ## polar radius
        pixsp_a = 2*np.pi*rb/360*abs(dlat)
        pixsp_r = 2*np.pi*ra/360*dlon*np.cos(np.deg2rad(centerlat))
    else:
        print('\nIn radar coordinates', flush=True)
        pixsp_r_org = float(io_lib.get_param_par(mlipar, 'range_pixel_spacing'))
        pixsp_a = float(io_lib.get_param_par(mlipar, 'azimuth_pixel_spacing'))
        inc_agl = float(io_lib.get_param_par(mlipar, 'incidence_angle'))
        pixsp_r = pixsp_r_org/np.sin(np.deg2rad(inc_agl))


    ### Set n_unw_r_thre and cycle depending on L- or C-band
    if wavelength > 0.2: ## L-band
        if not n_unw_r_thre: n_unw_r_thre = 0.5
        cycle = 1.5 # 2pi/cycle for comparison png
    elif wavelength <= 0.2: ## C-band
        if not n_unw_r_thre: n_unw_r_thre = 1.0
        cycle = 3 # 3*2pi/cycle for comparison png
    if sbovl:
        cycle = 75 ## for sbovl cyccle size

    #%% Read date and network information
    ### Get all ifgdates in ifgdir
    ifgdates_all = tools_lib.get_ifgdates(ifgdir)
    imdates_all = tools_lib.ifgdates2imdates(ifgdates_all)
    n_im_all = len(imdates_all)
    n_ifg_all = len(ifgdates_all)

    ### Read bad_ifg11 and 12
    bad_ifg11 = io_lib.read_ifg_list(bad_ifg11file)
    if not sbovl:
        bad_ifg12 = io_lib.read_ifg_list(bad_ifg12file)
        if os.path.exists(bad_ifg120file):
            print('adding also ifgs listed as bad in the optional 120 step')
            bad_ifg120 = io_lib.read_ifg_list(bad_ifg120file)
            bad_ifg12 = list(set(bad_ifg12 + bad_ifg120))
    else:
        bad_ifg12=[]
        if os.path.exists(bad_ifg120file):
            print('adding also ifgs listed as bad in the optional 120 step')
            bad_ifg120 = io_lib.read_ifg_list(bad_ifg120file)
            bad_ifg12 = list(set(bad_ifg12 + bad_ifg120))
    if nullify_noloops:
        # adding also noloop_ifgs as ifgs to skip
        print('skipping noloop_ifgs')
        bad_ifg12fileno = os.path.join(infodir, '12no_loop_ifg.txt')
        if os.path.exists(bad_ifg12fileno):
            bad_ifg12no = io_lib.read_ifg_list(bad_ifg12fileno)  ## no loop file
            bad_ifg12 = list(set(bad_ifg12 + bad_ifg12no))
    #
    bad_ifg_all = list(set(bad_ifg11+bad_ifg12))
    # removing coseismic ifgs for standard solutions. this will cause gap that will get interpolated
    # not needed/wanted for 'only_sb' and 'singular_gauss' methods
    if offsetsflag and (not singular_gauss) and (not only_sb):
        print('\n skipping coseismic interferograms \n')
        print('WARNING, this will remove coseismic signal from the inverted data. \n')
        print('( to prevent this, rerun with --only_sb ) \n')
        #print('( to prevent this, rerun with --singular_gauss or --only_sb ) \n')
        print('\n Note, the offsets should be shifted by -1 day if they occur in the same acquisition date but before the acquisition time! \n')
        coseismifgs = []
        for i, ifgd in enumerate(ifgdates_all):
            ep1 = int(ifgd[:8])
            ep2 = int(ifgd[-8:])
            for skep in offsets:
                if (ep1 < int(skep)) and (ep2 > int(skep)):
                    coseismifgs.append(ifgd)
                elif ep1 == int(skep) or ep2 == int(skep):
                    print('WARNING, the offset '+str(skep)+' is the same date as the acquisition. Skipping '+ifgd)
                    coseismifgs.append(ifgd)
        print('\n .. identified '+str(len(coseismifgs))+' coseismic ifgs \n')
        bad_ifg_all = list(set(bad_ifg_all + coseismifgs))

    bad_ifg_all.sort()

    ### Remove bad ifgs and images from list
    ifgdates = list(set(ifgdates_all)-set(bad_ifg_all))
    ifgdates.sort()

    imdates = tools_lib.ifgdates2imdates(ifgdates)

    n_ifg = len(ifgdates)
    n_ifg_bad = len(set(bad_ifg11+bad_ifg12))
    n_im = len(imdates)
    n_unw_thre = int(n_unw_r_thre*n_im)

    ##this necesarry to apply step 15, we ignore step12 therefore coh_avg and n_unw not created.
    if sbovl:
        ### Calc coh avg and n_unw
        coh_avg = np.zeros((length, width), dtype=np.float32)
        n_coh = np.zeros((length, width), dtype=np.int16)
        n_unw = np.zeros((length, width), dtype=np.int16)
    
        btemps = tools_lib.calc_temporal_baseline(ifgdates)
        thisbtemp = max(set(btemps), key=btemps.count)
        coh_avg_freq = np.zeros((length, width), dtype=np.float32)
        n_coh_freq = np.zeros((length, width), dtype=np.int16)
        ii = 0
        for ifgd in ifgdates:
            ccfile = os.path.join(ifgdir, ifgd, ifgd + '.sbovldiff.adf.cc')
            if os.path.getsize(ccfile) == length * width:
                coh = io_lib.read_img(ccfile, length, width, np.uint8)
                coh = coh.astype(np.float32) / 255
            else:
                coh = io_lib.read_img(ccfile, length, width)
                coh[np.isnan(coh)] = 0  # Fill nan with 0
    
            coh_avg += coh
            n_coh += (coh != 0)
            if btemps[ii] == thisbtemp:
                coh_avg_freq += coh
                n_coh_freq += (coh != 0)
            ii = ii + 1
            unwfile = os.path.join(ifgdir, ifgd, ifgd+'.sbovldiff.adf.mm') # after nullification
            #unwfile_ori = os.path.join(ifgdir, ifgd, ifgd + '.unw.ori')
            #if os.path.exists(unwfile_ori):
            #    unwfile = unwfile_ori
            unw = io_lib.read_img(unwfile, length, width)
            unw[unw == 0] = np.nan # Fill 0 with nan
            n_unw += ~np.isnan(unw) # Summing number of unnan unw
    
        coh_avg[n_coh == 0] = np.nan
        n_coh[n_coh == 0] = 1  # to avoid zero division
        coh_avg = coh_avg / n_coh
        coh_avg[coh_avg == 0] = np.nan
    
        coh_avg_freq[n_coh_freq == 0] = np.nan
        n_coh_freq[n_coh_freq == 0] = 1  # to avoid zero division
        coh_avg_freq = coh_avg_freq / n_coh_freq
        coh_avg_freq[coh_avg_freq == 0] = np.nan
    
        ### Save files
        n_unwfile = os.path.join(resultsdir, 'n_unw')
        np.float32(n_unw).tofile(n_unwfile)
    
        coh_avgfile = os.path.join(resultsdir, 'coh_avg')
        coh_avg.tofile(coh_avgfile)

    
    ### Make 13used_image.txt
    imfile = os.path.join(infodir, '13used_image.txt')
    with open(imfile, 'w') as f:
        for i in imdates:
            print('{}'.format(i), file=f)

    ### Calc dt in year
    imdates_dt = ([dt.datetime.strptime(imd, '%Y%m%d').toordinal() for imd in imdates])
    dt_cum = np.float32((np.array(imdates_dt)-imdates_dt[0])/365.25)

    ### Construct G and Aloop matrix for increment and n_gap
    G = inv_lib.make_sb_matrix(ifgdates)
    Aloop = loop_lib.make_loop_matrix(ifgdates)
    B = inv_lib.make_sb_matrix_epochs(ifgdates) # useful for returning nans between connections

    #%% Plot network
    ## Read bperp data or dummy
    bperp_file = os.path.join(ifgdir, 'baselines')
    if os.path.exists(bperp_file):
        with open(bperp_file, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]  # Remove empty lines
        if len(lines) >= len(imdates):  # Ensure enough entries
            bperp = io_lib.read_bperp_file(bperp_file, imdates)
            bperp_all = io_lib.read_bperp_file(bperp_file, imdates_all)
        else:
            print("WARNING: Baselines file contains fewer entries than the number of ifgs. Using dummy values.")
            bperp = np.random.random(len(imdates)).tolist()
            bperp_all = np.random.random(len(imdates_all)).tolist()
    else:  # Generate dummy baselines if file doesn't exist
        print("WARNING: Baselines file not found. Using dummy values.")
        bperp = np.random.random(len(imdates)).tolist()
        bperp_all = np.random.random(len(imdates_all)).tolist()

    pngfile = os.path.join(netdir, 'network13_all.png')
    plot_lib.plot_network(ifgdates_all, bperp_all, [], pngfile)

    pngfile = os.path.join(netdir, 'network13.png')
    plot_lib.plot_network(ifgdates_all, bperp_all, bad_ifg_all, pngfile)

    pngfile = os.path.join(netdir, 'network13_nobad.png')
    plot_lib.plot_network(ifgdates_all, bperp_all, bad_ifg_all, pngfile, plot_bad=False)


    #%% Get patch row number
    ### Check RAM
    mem_avail = (psutil.virtual_memory().available)/2**20 #MB
    if memory_size > mem_avail/2:
        print('\nNot enough memory available compared to mem_size ({} MB).'.format(memory_size))
        print('Reduce mem_size automatically to {} MB.'.format(int(mem_avail/2)))
        memory_size = int(mem_avail/2)

    ### Determine if read cum on memory (fast) or hdf5 (slow)
    cum_size = int(n_im*length*width*4/2**20) #MB
    if memory_size > cum_size*2:
        print('Read cum data on memory (fast but need memory).')
        save_mem = False # read on memory
        memory_size_patch = memory_size - cum_size
    else:
        print('Read cum data in HDF5 (save memory but slow).')
        save_mem = True # read on hdf5
        memory_size_patch = memory_size

    n_store_data = n_ifg*2 + n_im*2 + n_im/4 + 6 + 1 + n_im/2
    # n_im: cum, gap (1B), inc
    # n_ifg: unw, resid
    # and 6 length x width primary outputs
    # plus few small variables... assuming just length x width x 4B - should be less..
    # last one for temporary gap calc variable that is 2B with n_im x len x wid
    if inv_alg == 'WLS':
        n_store_data += n_ifg  # for varpatch

    if nullify_noloops:
        n_store_data += n_ifg/4 # 1B boolean

    n_patch, patchrow = tools_lib.get_patchrow(width, length, n_store_data, memory_size_patch)
    print('Patch: {}'.format(n_patch))
    print('Patchrows:')
    print([row for row in patchrow])

    #%% Display and output settings & parameters
    print('')
    print('Size of image (w,l)    : {}, {}'.format(width, length))
    print('# of all images        : {}'.format(n_im_all))
    print('# of images to be used : {}'.format(n_im))
    print('# of all ifgs          : {}'.format(n_ifg_all))
    print('# of ifgs to be used   : {}'.format(n_ifg))
    print('# of removed ifgs      : {}'.format(n_ifg_bad))
    print('Threshold of used unw  : {}'.format(n_unw_thre))
    print('')
    print('Reference area (X/Y)   : {}:{}/{}:{}'.format(refx1, refx2, refy1, refy2))
    print('Allowed memory size    : {} MB'.format(memory_size))
    print('Number of patches      : {}'.format(n_patch))
    print('Inversion algorism     : {}'.format(inv_alg))
    print('Gamma value            : {}'.format(gamma), flush=True)

    with open(os.path.join(infodir, '13parameters.txt'), "w") as f:
        print('range_samples:  {}'.format(width), file=f)
        print('azimuth_lines:  {}'.format(length), file=f)
        print('wavelength:     {}'.format(wavelength), file=f)
        print('n_im_all:       {}'.format(n_im_all), file=f)
        print('n_im:           {}'.format(n_im), file=f)
        print('n_ifg_all:      {}'.format(n_ifg_all), file=f)
        print('n_ifg:          {}'.format(n_ifg), file=f)
        print('n_ifg_bad:      {}'.format(n_ifg_bad), file=f)
        print('n_unw_thre:     {}'.format(n_unw_thre), file=f)
        print('ref_area:       {}:{}/{}:{}'.format(refx1, refx2, refy1, refy2), file=f)
        print('memory_size:    {} MB'.format(memory_size), file=f)
        print('n_patch:        {}'.format(n_patch), file=f)
        print('inv_alg:        {}'.format(inv_alg), file=f)
        print('gamma:          {}'.format(gamma), file=f)
        print('pixel_spacing_r: {:.2f} m'.format(pixsp_r), file=f)
        print('pixel_spacing_a: {:.2f} m'.format(pixsp_a), file=f)


    #%% Ref phase for inversion
    if not sbovl:
        lengththis = refy2-refy1
        countf = width*refy1
        countl = width*lengththis # Number to be read
        ref_unw = []
        nanserror = []
        for i, ifgd in enumerate(ifgdates):
            unwfile = os.path.join(ifgdir, ifgd, ifgd+'.unw')
            f = open(unwfile, 'rb')
            f.seek(countf*4, os.SEEK_SET) #Seek for >=2nd path, 4 means byte

            ### Read unw data (mm) at ref area
            unw = np.fromfile(f, dtype=np.float32, count=countl).reshape((lengththis, width))[:, refx1:refx2]*coef_r2m

            unw[unw == 0] = np.nan
            if np.all(np.isnan(unw)):
                print('All nan in ref area in {}. Removing from processing.'.format(ifgd))
                #print('Rerun LiCSBAS12.')
                f.close()
                nanserror.append(ifgd)
                #return 1
                continue

            ref_unw.append(np.nanmean(unw))

            f.close()

        if nanserror:
            print('There were still ifgs with all nan in ref area. Please rerun step 13')
            print('you can check following file (remove it if you decide to change reference point):')
            noref_ifgfile = os.path.join(infodir, '120bad_ifg.txt')
            print(noref_ifgfile)
            with open(noref_ifgfile, 'a') as f:
                for i in nanserror:
                    print('{}'.format(i), file=f)
            return 1
    else:
        print('SBOVL: no reference phase set up??')
    #%% Open cum.h5 for output
    ### Decide here what to do re. cumh5file and reloading patches. Need to check that stored cumh5 file is the right size etc
    print('store_patches:', store_patches)
    cumfile = os.path.join(resultsdir, 'cum')
    if load_patches:    
        if os.path.exists(cumfile):
            try:
                cum = np.fromfile(cumfile, dtype=np.float32).reshape((n_im, length, width))
                vel = np.zeros((length, width), dtype=np.float32)
                vconst = np.zeros((length, width), dtype=np.float32)
                vel_tmp = np.fromfile(os.path.join(resultsdir, 'vel'), dtype=np.float32)
                vconst_tmp = np.fromfile(os.path.join(resultsdir, 'vel'), dtype=np.float32)
                processed_rows = int(vel_tmp.shape[0] / width)
               
                vel[:processed_rows, :] = vel_tmp.reshape((processed_rows, width))
                vconst[:processed_rows, :] = vconst_tmp.reshape((processed_rows, width))
                cumh5 = h5.File(cumh5file, 'r+')
                gap = cumh5.require_dataset('gap', (n_im-1, length, width), dtype=np.int8, compression=compress)
                
                print(cumh5.keys())
                if save_mem:
                    # Write loaded patches to cum.h5
                    cumh5.create_dataset('cum', data=cum, compression=compress)
                    cumh5.create_dataset('vel', data=vel, compression=compress)
                    cumh5.create_dataset('vconst', data=vconst, compression=compress)

                    cum = cumh5.require_dataset('cum', (n_im, length, width),
                                                dtype=np.float32, compression=compress)
                    vel = cumh5.require_dataset('vel', (length, width),
                                                dtype=np.float32, compression=compress)
                    vconst = cumh5.require_dataset('vintercept', (length, width),
                                                dtype=np.float32, compression=compress)
                    
                print('Processed Patches loaded - {} rows completed'.format(processed_rows))
            except:
                print('Data doesnt match. Restarting inversion')
                processed_rows = 0
        else:
            print('No previous patches found - this is either the first run or the previous run was successful!')
            processed_rows = 0
    else:
      processed_rows = 0
 
    if processed_rows == 0:
        if os.path.exists(cumh5file): os.remove(cumh5file)
        cumh5 = h5.File(cumh5file, 'w')
        cumh5.create_dataset('imdates', data=[np.int32(imd) for imd in imdates])
        if not np.all(np.abs(np.array(bperp))<=1):# if not dummy
            cumh5.create_dataset('bperp', data=bperp)
        gap = cumh5.require_dataset('gap', (n_im-1, length, width),
                                    dtype=np.int8, compression=compress)
        if save_mem:
            cum = cumh5.require_dataset('cum', (n_im, length, width),
                                        dtype=np.float32, compression=compress)
            vel = cumh5.require_dataset('vel', (length, width),
                                        dtype=np.float32, compression=compress)
            vconst = cumh5.require_dataset('vintercept', (length, width),
                                        dtype=np.float32, compression=compress)
        else:
            ### If store, check here for something....
            cum = np.zeros((n_im, length, width), dtype=np.float32)
            vel = np.zeros((length, width), dtype=np.float32)
            vconst = np.zeros((length, width), dtype=np.float32)

        if width == width_geo and length == length_geo: ## if geocoded
            cumh5.create_dataset('corner_lat', data=lat1)
            cumh5.create_dataset('corner_lon', data=lon1)
            cumh5.create_dataset('post_lat', data=dlat)
            cumh5.create_dataset('post_lon', data=dlon)

    # By here, need to have identified which patchrows have been completed, and just make the forloop start from there
    # Also makesure that there is a structure to load into that has the right data

    #%% For each patch
    for i_patch, rows in enumerate(patchrow):
        if rows[1] <= processed_rows:
            print('\nAlready Processed {0}/{1}th line ({2}/{3}th patch)...'.format(rows[1], patchrow[-1][-1], i_patch+1, n_patch), flush=True)
            continue
        else:
            print('\nProcess {0}/{1}th line ({2}/{3}th patch)...'.format(rows[1], patchrow[-1][-1], i_patch+1, n_patch), flush=True)
            start2 = time.time()

            #%% Read data
            ### Allocate memory
            lengththis = rows[1] - rows[0]
            n_pt_all = lengththis*width
            unwpatch = np.zeros((n_ifg, lengththis, width), dtype=np.float32)
            if nullify_noloops:
                hasdatapatch = np.zeros((n_ifg, lengththis, width), dtype=bool)
            if inv_alg == 'WLS':
                cohpatch = np.zeros((n_ifg, lengththis, width), dtype=np.float32)

            ### For each ifg
            print("  Reading {0} ifg's unw data...".format(n_ifg), flush=True)
            countf = width*rows[0]
            countl = width*lengththis
            for i, ifgd in enumerate(ifgdates):
                if sbovl:
                    unwfile = os.path.join(ifgdir, ifgd, ifgd+'.sbovldiff.adf.mm')
                else:
                    unwfile = os.path.join(ifgdir, ifgd, ifgd+'.unw')
                f = open(unwfile, 'rb')
                f.seek(countf*4, os.SEEK_SET) #Seek for >=2nd patch, 4 means byte

                ### Read unw data (mm) at patch area
                unw = np.fromfile(f, dtype=np.float32, count=countl).reshape((lengththis, width))*coef_r2m
                unw[unw == 0] = np.nan # Fill 0 with nan
                if not sbovl:
                    unw = unw - ref_unw[i]
                else:
                    print('SBOVL: no reference removal set up??')
                unwpatch[i] = unw
                f.close()

                ### Read coh file at patch area for WLS
                if inv_alg == 'WLS':
                    if sbovl:
                        cohfile = os.path.join(ifgdir, ifgd, ifgd+'.sbovldiff.adf.cc')
                    else:
                        cohfile = os.path.join(ifgdir, ifgd, ifgd+'.cc')
                    f = open(cohfile, 'rb')

                    if os.path.getsize(cohfile) == length*width: ## uint8 format
                        f.seek(countf, os.SEEK_SET) #Seek for >=2nd patch
                        cohpatch[i, :, :] = (np.fromfile(f, dtype=np.uint8, count=countl).reshape((lengththis, width))).astype(np.float32)/255
                    else: ## old float32 format
                        f.seek(countf*4, os.SEEK_SET) #Seek for >=2nd patch, 4 means byte
                        cohpatch[i, :, :] = np.fromfile(f, dtype=np.float32, count=countl).reshape((lengththis, width))
                    cohpatch[cohpatch==0] = np.nan

            unwpatch = unwpatch.reshape((n_ifg, n_pt_all)).transpose() #(n_pt_all, n_ifg)

            ### Recalculate no-loop ifgs info to remove them - use only the 'ori files', i.e. before nullification. If no ori, we'll use the unw files (then unwpatch_ori = unwpatch)
            if nullify_noloops:
                print('Nullifying noloop ifgs')

                if not nullify_noloops_use_data_after_nullification:  # should be the default way
                    nullify_nl_use_oris = False
                    for i, ifgd in enumerate(ifgdates):
                        if sbovl:
                            unwfile_ori = os.path.join(ifgdir, ifgd, ifgd + '.sbovldiff.adf.mm.ori') ##this will be never happened bcz sbovl not running step 12
                        else:
                            unwfile_ori = os.path.join(ifgdir, ifgd, ifgd + '.unw.ori')
                        if os.path.exists(unwfile_ori):
                            nullify_nl_use_oris = True
                            print('(from data before the loop phase closure error nullification in step 12)')
                            break
                    if not nullify_nl_use_oris:
                        print('No ori files detected (step 12 was run without nullification)')
                else:
                    #print('(from data after loop phase closure error nullification if done in step 12)')
                    nullify_nl_use_oris = False

                if nullify_nl_use_oris:
                    try:
                        print('  identifying noloop_ifg data')
                        # step 2 for nullify_noloops: load the unw files
                        for i, ifgd in enumerate(ifgdates):
                            if sbovl:
                                unwfile_ori = os.path.join(ifgdir, ifgd, ifgd + '.sbovldiff.adf.mm.ori')
                            else:
                                unwfile_ori = os.path.join(ifgdir, ifgd, ifgd + '.unw.ori')
                            if not os.path.exists(unwfile_ori):
                                # only fixed unw data would keep the originals (ori).
                                if sbovl:
                                    unwfile_ori = os.path.join(ifgdir, ifgd, ifgd + '.sbovldiff.adf.mm')
                                else:
                                    unwfile_ori = os.path.join(ifgdir, ifgd, ifgd + '.unw')
                            f = open(unwfile_ori, 'rb')
                            f.seek(countf * 4, os.SEEK_SET)  # Seek for >=2nd patch, 4 means byte
                            unw_ori = np.fromfile(f, dtype=np.float32, count=countl).reshape((lengththis, width))  #* coef_r2m
                            unw_ori[unw_ori == 0] = np.nan  # Fill 0 with nan
                            hasdatapatch[i] = ~np.isnan(unw_ori)
                            f.close()
                        hasdatapatch = hasdatapatch.reshape((n_ifg, n_pt_all)).transpose()
                    except:
                        print("Some error loading unw data, skipping the nullify_noloops routine", flush=True)
                        nullify_noloops = False
                else:
                    hasdatapatch = ~np.isnan(unwpatch)
                    # in such case we will just use the unwpatch..

            # if still ok, perform the main noloop routine
            if nullify_noloops:
                print('  removing noloop_ifgs before inversion (in memory)')
                orignounw = hasdatapatch.sum()
                # step 2 for nullify_noloops: counting the noloops and nullying data from ifgs not forming any loop
                try:
                    print('  with {} parallel processing...'.format(n_para), flush=True)

                    p = q.Pool(n_para)
                    # ML: simultaneous write to np.array is possible (just careful not to use same rows/cols)
                    # _result = np.array(
                    p.map(nullify_noloops_wrapper, range(n_para)) #, dtype=float)
                    p.close()
                    afternounw = (~np.isnan(unwpatch)).sum()

                except Exception as e:
                    print("ERROR nullifying noloops data:")
                    print(traceback.format_exc())
                    nullify_noloops = False
                    return 1
                del hasdatapatch # no need anymore
                print('')
                print('  '+str(int(orignounw - afternounw))+'/'+str(int(orignounw))+' values dropped after noloop_ifg masking.')
                print('')


            ### Calc variance from coherence for WLS
            if inv_alg == 'WLS':
                cohpatch = cohpatch.reshape((n_ifg, n_pt_all)).transpose() #(n_pt_all, n_ifg)
                cohpatch[np.isnan(cohpatch)] = 0.0 # there still might be nans that would otherwise propagate - e.g. missing bursts...
                cohpatch[cohpatch<0.01] = 0.01 ## because negative value possible due to geocode
                cohpatch[cohpatch>0.99] = 0.99 ## because >1 possible due to geocode
                varpatch = (1-cohpatch**2)/(2*cohpatch**2)
                del cohpatch


            #%% Remove points with less valid data than n_unw_thre
            ix_unnan_pt = np.where(np.sum(~np.isnan(unwpatch), axis=1) > n_unw_thre)[0]
            n_pt_unnan = len(ix_unnan_pt)

            unwpatch = unwpatch[ix_unnan_pt,:] ## keep only unnan data
            if inv_alg == 'WLS':
                varpatch = varpatch[ix_unnan_pt,:] ## keep only unnan data

            print('  {}/{} points removed due to not enough ifg data...'.format(n_pt_all-n_pt_unnan, n_pt_all), flush=True)

            #%% Compute number of gaps, ifg_noloop, maxTlen point-by-point
            if n_pt_unnan != 0:
                ns_gap_patch = np.zeros((n_pt_all), dtype=np.float32)*np.nan
                gap_patch = np.zeros((n_im-1, n_pt_all), dtype=np.int8)
                ns_ifg_noloop_patch = np.zeros((n_pt_all), dtype=np.float32)*np.nan
                maxTlen_patch = np.zeros((n_pt_all), dtype=np.float32)*np.nan
                print('\n  Identifying gaps, and counting n_gap and n_ifg_noloop,')

                if gpu:
                    print('  using GPU...', flush=True)
                    n_loop, _ = Aloop.shape
                    unwpatch_cp = cp.asarray(unwpatch)
                    G_cp = cp.asarray(G)
                    Aloop_cp = cp.asarray(Aloop)

                    ns_unw_unnan4inc = cp.array(
                        [(G_cp[:, i]*(~cp.isnan(unwpatch_cp))).sum(
                            axis=1, dtype=cp.int16) for i in range(n_im-1)])
                    # n_ifg*(n_pt,n_ifg) -> (n_im-1,n_pt)
                    ns_gap_patch[ix_unnan_pt] = cp.asnumpy(
                        (ns_unw_unnan4inc==0).sum(axis=0)) #n_pt
                    gap_patch[:, ix_unnan_pt] = cp.asnumpy(ns_unw_unnan4inc==0)

                    del ns_unw_unnan4inc
                    del G_cp

                    ### n_ifg_noloop
                    # n_ifg*(n_pt,n_ifg)->(n_loop,n_pt)
                    # Number of ifgs for each loop at eath point.
                    # 3 means complete loop, 1 or 2 means broken loop.
                    ns_ifg4loop = cp.array([
                            (cp.abs(Aloop_cp[i, :])*(~cp.isnan(unwpatch_cp))).sum(axis=1)
                            for i in range(n_loop)])
                    bool_loop = (ns_ifg4loop==3)
                    #(n_loop,n_pt) identify complete loop only

                    # n_loop*(n_loop,n_pt)*n_pt->(n_ifg,n_pt)
                    # Number of loops for each ifg at eath point.
                    ns_loop4ifg = cp.array([(
                            (cp.abs(Aloop_cp[:, i])*bool_loop.T).T*
                            (~cp.isnan(unwpatch_cp[:, i]))
                            ).sum(axis=0) for i in range(n_ifg)]) #

                    ns_ifg_noloop_tmp = (ns_loop4ifg==0).sum(axis=0) #n_pt
                    ns_nan_ifg = cp.isnan(unwpatch_cp).sum(axis=1) #n_pt, nan ifg count
                    ns_ifg_noloop_patch[ix_unnan_pt] = cp.asnumpy(
                        ns_ifg_noloop_tmp - ns_nan_ifg)

                    del bool_loop, ns_ifg4loop, ns_loop4ifg
                    del ns_ifg_noloop_tmp, ns_nan_ifg
                    del unwpatch_cp, Aloop_cp

                else:
                    ### Determine n_para
                    n_pt_patch_min = 1000
                    if n_pt_patch_min*n_para > n_pt_unnan:
                        ## Too much n_para
                        n_para_gap = int(np.floor(n_pt_unnan/n_pt_patch_min))
                        if n_para_gap == 0: n_para_gap = 1
                    else:
                        n_para_gap = n_para

                    print('  with {} parallel processing...'.format(n_para_gap),
                        flush=True)

                    ### Devide unwpatch by n_para for parallel processing
                    p = q.Pool(n_para_gap)
                    _result = np.array(p.map(count_gaps_wrapper, range(n_para_gap)),
                                    dtype=object)
                    p.close()

                    ns_gap_patch[ix_unnan_pt] = np.hstack(_result[:, 0]) #n_pt
                    gap_patch[:, ix_unnan_pt] = np.hstack(_result[:, 1]) #n_im-1, n_pt
                    ns_ifg_noloop_patch[ix_unnan_pt] = np.hstack(_result[:, 2])

                ### maxTlen
                _maxTlen = np.zeros((n_pt_unnan), dtype=np.float32) #temporaly
                _Tlen = np.zeros((n_pt_unnan), dtype=np.float32) #temporaly
                for imx in range(n_im-1):
                    _Tlen = _Tlen + (dt_cum[imx+1]-dt_cum[imx]) ## Adding dt
                    _Tlen[gap_patch[imx, ix_unnan_pt]==1] = 0 ## reset to 0 if gap
                    _maxTlen[_maxTlen<_Tlen] = _Tlen[_maxTlen<_Tlen] ## Set Tlen to maxTlen
                maxTlen_patch[ix_unnan_pt] = _maxTlen


                #%% Time series inversion
                print('\n  Small Baseline inversion by {}...\n'.format(inv_alg), flush=True)

                if inv_alg == 'WLS':
                    wvars = varpatch
                else:
                    wvars = None

                if only_sb:
                    method = 'only_sb'
                elif singular_gauss:
                    method = 'singular_gauss'
                elif singular:
                    method = 'singular'
                else:
                    method = 'nsbas'
                print('...using method:   '+method+'\n', flush = True)

                # with offsets:
                # nsbas should invert with offsets, as in cum2vel - otherwise the gaps are wrongly estimated due to wrong velocity
                # only_sb can invert in the next step with offsets as there is no problem
                # (low priority): singular - as nsbas, need to invert with offsets, and use it as diff when getting velocity estimate (TODO: update it to use LS for vel?)
                # singular_gauss - must set weights for dt_cum to 0 for offset dates, then can invert with offsets in the next step
                # first load offsets (prepare LiCSBAS_eqoffsets.py -M 6 --buffer(? - no need if using extents) -o eqoffsets.txt)
                # dt_offsets should be True where the given dt_cum is an offset (means... the increment between that date and the previous contains the quake)
                #
                if offsetsflag and offsets_dt:
                    imdt_arr = np.array(imdates_dt)
                    offixs = []
                    for offset in offsets_dt:
                        offixs.append(np.argmax(imdt_arr >= offset.toordinal()))
                    dt_cum_offsets = np.zeros(len(dt_cum))
                    dt_cum_offsets[offixs] = 1
                    dt_cum_offsets = dt_cum_offsets==1
                else:
                    dt_cum_offsets = None
                
                inc_tmp, vel_tmp, vconst_tmp = inv_lib.invert_unws(unwpatch, G, dt_cum, gamma, n_para_inv, gpu, dt_offsets = dt_cum_offsets,
                                                                   wvars = wvars, method = method, inv_alg = inv_alg)
                #if inv_alg == 'WLS':
                #    inc_tmp, vel_tmp, vconst_tmp = inv_lib.invert_nsbas_wls(
                #        unwpatch, varpatch, G, dt_cum, gamma, n_para_inv)
                #else:
                #    inc_tmp, vel_tmp, vconst_tmp = inv_lib.invert_nsbas(
                #        unwpatch, G, dt_cum, gamma, n_para_inv, gpu, singular=singular, only_sb=only_sb, singular_gauss=singular_gauss)

                ### Set to valuables
                inc_patch = np.zeros((n_im-1, n_pt_all), dtype=np.float32)*np.nan
                vel_patch = np.zeros((n_pt_all), dtype=np.float32)*np.nan
                vconst_patch = np.zeros((n_pt_all), dtype=np.float32)*np.nan

                inc_patch[:, ix_unnan_pt] = inc_tmp
                vel_patch[ix_unnan_pt] = vel_tmp
                vconst_patch[ix_unnan_pt] = vconst_tmp

                ### Calculate residuals
                res_patch = np.zeros((n_ifg, n_pt_all), dtype=np.float32)*np.nan
                res_patch[:, ix_unnan_pt] = unwpatch.T-np.dot(G, inc_tmp)

                # Calculate RMSE of the inversion (should we add degrees of freedom?)
                res_sumsq = np.nansum(res_patch**2, axis=0)
                res_n = np.float32((~np.isnan(res_patch)).sum(axis=0))
                res_n[res_n==0] = np.nan # To avoid 0 division
                res_rms_patch = np.sqrt(res_sumsq/res_n)

                ### Cumulative displacememt
                cum_patch = np.zeros((n_im, n_pt_all), dtype=np.float32)*np.nan
                cum_patch[1:, :] = np.cumsum(inc_patch, axis=0)

                ## 2025/09: keep the nans between connections
                print('Setting NaNs to cum values that were not measured by interferograms')
                print('This is now under testing - might cause issues at reference area?')
                try:
                    for indexpx in range(unwpatch.shape[0]):
                        nonans = np.argwhere(~np.isnan(unwpatch[indexpx]))[:, 1]
                        Bm = B[nonans, :].sum(axis=0)
                        cum_patch[Bm == 0, indexpx] = np.nan
                except:
                    print('dev functionality on returning nans - error, please fix (let know Milan)')

                ## Fill 1st image with 0 at unnan points from 2nd images
                bool_unnan_pt = ~np.isnan(cum_patch[1, :])
                cum_patch[0, bool_unnan_pt] = 0

                # need this below only for methods that interpolate nans
                # NOTE, this will nullify increment if inbetween two gaps. In fact there is gapfilling through every gap..
                if method != 'only_sb':  # == 'nsbas':
                    ## Drop (fill with nan) interpolated cum by 2 continuous gaps
                    for i in range(n_im-2): ## from 1->n_im-1
                        gap2 = gap_patch[i, :]+gap_patch[i+1, :]
                        bool_gap2 = (gap2==2) ## true if 2 continuous gaps for each point
                        cum_patch[i+1, :][bool_gap2] = np.nan
                #
                ## Last (n_im th) image. 1 gap means interpolated
                cum_patch[-1, :][gap_patch[-1, :]==1] = np.nan

            #%% Fill by np.nan if n_pt_unnan == 0
            else:
                cum_patch = np.zeros((n_im, n_pt_all), dtype=np.float32)*np.nan
                vel_patch = np.zeros((n_pt_all), dtype=np.float32)*np.nan
                vconst_patch = np.zeros((n_pt_all), dtype=np.float32)*np.nan
                gap_patch = np.zeros((n_im-1, n_pt_all), dtype=np.int8)
                inc_patch = np.zeros((n_im-1, n_pt_all), dtype=np.float32)*np.nan
                res_patch = np.zeros((n_ifg, n_pt_all), dtype=np.float32)*np.nan
                res_rms_patch = np.zeros((n_pt_all), dtype=np.float32)*np.nan
                ns_gap_patch = np.zeros((n_pt_all), dtype=np.float32)*np.nan
                ns_ifg_noloop_patch = np.zeros((n_pt_all), dtype=np.float32)*np.nan
                maxTlen_patch = np.zeros((n_pt_all), dtype=np.float32)*np.nan


            #%% Output data and image
            ### cum.h5 file
            cum[:, rows[0]:rows[1], :] = cum_patch.reshape((n_im, lengththis, width))
            vel[rows[0]:rows[1], :] = vel_patch.reshape((lengththis, width))
            vconst[rows[0]:rows[1], :] = vconst_patch.reshape((lengththis, width))
            gap[:, rows[0]:rows[1], :] = gap_patch.reshape((n_im-1, lengththis, width))

            if store_patches and not save_mem:
                with open(cumfile, 'w') as f:
                    cum.tofile(f)

            print('   Saving processing results')

            ### Others
            openmode = 'w' if rows[0] == 0 else 'a' #w only 1st patch

            ## For each imd. cum and inc
            for imx, imd in enumerate(imdates):
                ## Incremental displacement
                if imd == imdates[-1]: continue #skip last
                incfile = os.path.join(incdir, '{0}_{1}.inc'.format(imd, imdates[imx+1]))
                with open(incfile, openmode) as f:
                    inc_patch[imx, :].tofile(f)

            ## For each ifgd. resid
            for i, ifgd in enumerate(ifgdates):
                resfile = os.path.join(resdir, '{0}.res'.format(ifgd))
                with open(resfile, openmode) as f:
                    res_patch[i, :].tofile(f)

            ## velocity and noise indecies in results dir
            names = ['vel', 'vintercept', 'resid_rms', 'n_gap', 'n_ifg_noloop', 'maxTlen']
            data = [vel_patch, vconst_patch, res_rms_patch, ns_gap_patch, ns_ifg_noloop_patch, maxTlen_patch]

            for i in range(len(names)):
                file = os.path.join(resultsdir, names[i])
                with open(file, openmode) as f:
                    data[i].tofile(f)
            # storing also the gap_patch matrix to be used later
            file = os.path.join(resultsdir, 'gap_patch')
            with open(file, openmode) as f:
                gap_patch[i].tofile(f)

            # cleaning patch variables from memory:
            varnames = ['res_patch', 'cum_patch', 'inc_patch', 'hasdatapatch', 'gap_patch', 'unwpatch', 'wvars', 'varpatch']
            varnames += ['vel_patch', 'vconst_patch', 'res_rms_patch', 'ns_gap_patch', 'ns_ifg_noloop_patch', 'maxTlen_patch']
            for vn in varnames:
                if (vn in globals() or vn in locals()):
                    try:
                        del globals()[vn]
                    except:
                        try:
                            del locals()[vn]
                            print('debug: removing '+vn+' from local vars')
                        except:
                            print('some issue removing '+vn+' from memory')

        #%% Finish patch
        elapsed_time2 = int(time.time()-start2)
        hour2 = int(elapsed_time2/3600)
        minite2 = int(np.mod((elapsed_time2/60),60))
        sec2 = int(np.mod(elapsed_time2,60))
        print("  Elapsed time for {0}th patch: {1:02}h {2:02}m {3:02}s".format(i_patch+1, hour2, minite2, sec2), flush=True)


    #%% Find stable ref point
    print('\nFind stable reference point...', flush=True)
    ### Compute RMS of time series with reference to all points
    sumsq_cum_wrt_med = np.zeros((length, width), dtype=np.float32)
    for i in range(n_im):
        sumsq_cum_wrt_med = sumsq_cum_wrt_med + (cum[i, :, :]-np.nanmedian(cum[i, :, :]))**2
    rms_cum_wrt_med = np.sqrt(sumsq_cum_wrt_med/n_im)

    ### Mask by minimum n_gap
    n_gap = io_lib.read_img(os.path.join(resultsdir, 'n_gap'), length, width)
    min_n_gap = np.nanmin(n_gap)
    mask_n_gap = np.float32(n_gap==min_n_gap)
    mask_n_gap[mask_n_gap==0] = np.nan
    rms_cum_wrt_med = rms_cum_wrt_med*mask_n_gap

    ### Find stable reference
    min_rms = np.nanmin(rms_cum_wrt_med)
    refy1s, refx1s = np.where(rms_cum_wrt_med==min_rms)
    refy1s, refx1s = refy1s[0], refx1s[0] ## Only first index
    refy2s, refx2s = refy1s+1, refx1s+1
    print('Selected ref: {}:{}/{}:{}'.format(refx1s, refx2s, refy1s, refy2s), flush=True)

    ### Rerferencing cumulative displacement  and vel to new stable ref
    if not sbovl:
        for i in range(n_im):
            cum[i, :, :] = cum[i, :, :] - cum[i, refy1s, refx1s]
        vel = vel - vel[refy1s, refx1s]
        vconst = vconst - vconst[refy1s, refx1s]
    else:
        print('  Skip rerferencing cumulative displacement and velocity for sbovl data.', flush=True)
        
    ### Save image
    rms_cum_wrt_med_file = os.path.join(infodir, '13rms_cum_wrt_med')
    with open(rms_cum_wrt_med_file, 'w') as f:
        rms_cum_wrt_med.tofile(f)

    pngfile = os.path.join(infodir, '13rms_cum_wrt_med.png')
    plot_lib.make_im_png(rms_cum_wrt_med, pngfile, cmap_noise_r, 'RMS of cum wrt median (mm)', np.nanpercentile(rms_cum_wrt_med, 1), np.nanpercentile(rms_cum_wrt_med, 99))

    ### Save ref
    cumh5.create_dataset('refarea', data='{}:{}/{}:{}'.format(refx1s, refx2s, refy1s, refy2s))
    refsfile = os.path.join(infodir, '13ref.txt')
    with open(refsfile, 'w') as f:
        print('{}:{}/{}:{}'.format(refx1s, refx2s, refy1s, refy2s), file=f)

    if width == width_geo and length == length_geo: ## Geocoded
        ### Make ref_stable.kml
        reflat = lat1+dlat*refy1s
        reflon = lon1+dlon*refx1s
        io_lib.make_point_kml(reflat, reflon, os.path.join(infodir, '13ref.kml'))



    #%% Close h5 file
    if not save_mem:
        print('\nWriting to HDF5 file...')
        cumh5.create_dataset('cum', data=cum, compression=compress)
        cumh5.create_dataset('vel', data=vel, compression=compress)
        cumh5.create_dataset('vintercept', data=vconst, compression=compress)
        if store_patches:
            os.remove(cumfile)

    indices = ['coh_avg', 'hgt', 'n_loop_err', 'n_unw', 'slc.mli',
               'maxTlen', 'n_gap', 'n_ifg_noloop', 'resid_rms']
    for index in indices:
        file = os.path.join(resultsdir, index)
        if os.path.exists(file):
            data = io_lib.read_img(file, length, width)
            cumh5.create_dataset(index, data=data, compression=compress)
        else:
            print('  {} not exist in results dir. Skip'.format(index))

    LOSvecs = ['E.geo', 'N.geo', 'U.geo']
    for LOSvec in LOSvecs:
        file = os.path.join(ifgdir, LOSvec)
        if os.path.exists(file):
            data = io_lib.read_img(file, length, width)
            cumh5.create_dataset(LOSvec, data=data, compression=compress)
        else:
            print('  {} not exist in GEOCml dir. Skip'.format(LOSvec))

    cumh5.close()


    #%% Output png images
    ### Incremental displacement
    if nopngs:
        print('skipping generating additional png images of increments and residuals - as sometimes taking too long (tutorial purposes)')
    else:
        _n_para = n_im-1 if n_para > n_im-1 else n_para
        print('\nOutput increment png images with {} parallel processing...'.format(_n_para), flush=True)
        # p = q.Pool(_n_para)
        # p.map(inc_png_wrapper, range(n_im-1))
        # p.close()
        # Create a list of (imx, sbovl) pairs for each index
        args_list = [(imx, sbovl) for imx in range(n_im - 1)]
    
        with q.Pool(_n_para) as p:
            p.starmap(inc_png_wrapper, args_list)


        
        ### Residual for each ifg. png and txt.
        with open(restxtfile, "w") as f:
            print('# RMS of residual (mm)', file=f)
        _n_para = n_ifg if n_para > n_ifg else n_para
        print('\nOutput residual png images with {} parallel processing...'.format(_n_para), flush=True)
        p = q.Pool(_n_para)
        p.map(resid_png_wrapper, range(n_ifg))
        p.close()

    ### Velocity and noise indices
    cmins = [None, None, None, None, None, None]
    cmaxs = [None, None, None, None, None, None]
    cmaps = [cmap_vel, cmap_vel, cmap_noise_r, cmap_noise_r, cmap_noise_r, cmap_noise]
    titles = ['Velocity (mm/yr)', 'Intercept of velocity (mm)', 'RMS of residual (mm)', 'Number of gaps in SB network', 'Number of ifgs with no loops', 'Max length of connected SB network (yr)']

    print('\nOutput results and noise png images...', flush=True)
    for i in range(len(names)):
        file = os.path.join(resultsdir, names[i])
        data = io_lib.read_img(file, length, width)

        pngfile = file+'.png'

        ## Get color range if None
        if cmins[i] is None:
            cmins[i] = np.nanpercentile(data, 1)
        if cmaxs[i] is None:
            cmaxs[i] = np.nanpercentile(data, 99)
        if cmins[i] == cmaxs[i]: cmins[i] = cmaxs[i]-1

        plot_lib.make_im_png(data, pngfile, cmaps[i], titles[i], cmins[i], cmaxs[i])

    # additionally run cum2vel where this is possible:
    if offsetsflag and (singular_gauss or only_sb):
        print('\nRe-estimating velocity with offsets..', flush = True)
        modelfile = os.path.join(tsadir, 'model.h5')
        cmd = 'LiCSBAS_cum2vel.py -i '+cumh5file+' --store_to_results --offsets '+offsetsfile+' --png --export_model '+modelfile+' --vstd'
        print('\n by running: ')
        print(cmd)
        os.system(cmd)
        if os.path.exists(os.path.join(resultsdir, 'stc')):
            print('\nNote vstd and stc were generated, step 14 is not needed. \n')
        else:
            print('\nWARNING, seems run of LiCSBAS_cum2vel failed')

    #%% Finish
    elapsed_time = time.time()-start
    hour = int(elapsed_time/3600)
    minite = int(np.mod((elapsed_time/60),60))
    sec = int(np.mod(elapsed_time,60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour,minite,sec))

    print('\n{} Successfully finished!!\n'.format(os.path.basename(argv[0])))
    print('Output directory: {}\n'.format(os.path.relpath(tsadir)))


#%%
def count_gaps_wrapper(i):
    print("    Running {:2}/{:2}th sub-patch...".format(i+1, n_para_gap), flush=True)
    n_pt_patch = int(np.ceil(unwpatch.shape[0]/n_para_gap))
    n_im = G.shape[1]+1
    n_loop, n_ifg = Aloop.shape

    if i*n_pt_patch >= unwpatch.shape[0]:
        # Nothing to do
        return

    ### n_gap and gap location
#    ns_unw_unnan4inc = (np.matmul(np.int8(G[:, :, None]), (~np.isnan(unwpatch.T))[:, None, :])).sum(axis=0, dtype=np.int16) #n_ifg, n_im-1, n_pt -> n_im-1, n_pt
    print('patch '+str(i)+', step 1/3: gaps identification')
    ns_unw_unnan4inc = np.array([(G[:, j]*
                          (~np.isnan(unwpatch[i*n_pt_patch:(i+1)*n_pt_patch])))
                         .sum(axis=1, dtype=np.int16) for j in range(n_im-1)])
                    #n_ifg*(n_pt,n_ifg) -> (n_im-1,n_pt)
    _ns_gap_patch = (ns_unw_unnan4inc==0).sum(axis=0) #n_pt
    _gap_patch = ns_unw_unnan4inc==0

    del ns_unw_unnan4inc

    ### n_ifg_noloop
    # n_ifg*(n_pt,n_ifg)->(n_loop,n_pt)
    # Number of ifgs for each loop at eath point.
    # 3 means complete loop, 1 or 2 means broken loop.
    print('patch ' + str(i) + ', step 2/3: n_ifg_noloop')
    ns_ifg4loop = np.array([(np.abs(Aloop[j, :])*
                         (~np.isnan(unwpatch[i*n_pt_patch:(i+1)*n_pt_patch])))
                            .sum(axis=1) for j in range(n_loop)])
    bool_loop = (ns_ifg4loop==3) #(n_loop,n_pt) identify complete loop only
    del ns_ifg4loop

    # n_loop*(n_loop,n_pt)*n_pt->(n_ifg,n_pt)
    # Number of loops for each ifg at eath point.
    print('patch ' + str(i) + ', step 3/3: n_loop per each ifg at each point')
    ns_loop4ifg = np.array([(
            (np.abs(Aloop[:, j])*bool_loop.T).T*
            (~np.isnan(unwpatch[i*n_pt_patch:(i+1)*n_pt_patch, j]))
            ).sum(axis=0) for j in range(n_ifg)]) #
    del bool_loop

    print('patch ' + str(i) + ': indices calculated')
    ns_ifg_noloop_tmp = (ns_loop4ifg==0).sum(axis=0) #n_pt
    del ns_loop4ifg

    ns_nan_ifg = np.isnan(unwpatch[i*n_pt_patch:(i+1)*n_pt_patch, :]).sum(axis=1)
    #n_pt, nan ifg count
    _ns_ifg_noloop_patch = ns_ifg_noloop_tmp - ns_nan_ifg

    return _ns_gap_patch, _gap_patch, _ns_ifg_noloop_patch

#%%
def nullify_noloops_wrapper(i):
    # must be run with both unwpatch and hasdatapatch already existing - i.e. works for either from ori or nulled unws
    print("    Running {:2}/{:2}th patch...".format(i+1, n_para), flush=True)
    n_pt_patch = int(np.ceil(unwpatch.shape[0]/n_para))
    #
    if i*n_pt_patch >= unwpatch.shape[0]:
        # Nothing to do
        return
    #
    ### n_ifg_noloop
    # n_ifg*(n_pt,n_ifg)->(n_loop,n_pt)
    # Number of ifgs for each loop at each point.
    # 3 means complete loop, 1 or 2 means broken loop. 0 means ifg_noloop (no loop formed)
    ns_ifg4loop = np.dot(np.abs(Aloop),(hasdatapatch[i*n_pt_patch:(i+1)*n_pt_patch]).T)
    bool_loop = (ns_ifg4loop==3)
    del ns_ifg4loop
    ns_loop4ifg = np.multiply((np.dot((np.abs(Aloop)).T,bool_loop)).T,
                              (hasdatapatch[i*n_pt_patch:(i+1)*n_pt_patch,:])
                )
    del bool_loop
    unwpatch_patch = unwpatch[i*n_pt_patch:(i+1)*n_pt_patch,:]
    # the line below will nullify pixels for ifgs that do not participate in a loop (ifg_noloop)
    unwpatch_patch[ns_loop4ifg==0] = np.nan
    unwpatch[i*n_pt_patch:(i+1)*n_pt_patch,:] = unwpatch_patch
    del unwpatch_patch
    #ns_ifg_noloop_tmp = (ns_loop4ifg==0).sum(axis=1) #n_pt
    #del ns_loop4ifg
    #_unwpatch = unwpatch
    #ns_nan_ifg = np.isnan(unwpatch[i*n_pt_patch:(i+1)*n_pt_patch, :]).sum(axis=1)
    #n_pt, nan ifg count
    #_ns_loop4ifg_patch = ns_ifg_noloop_tmp - ns_nan_ifg
    #_ns_loop4ifg_patch = _ns_loop4ifg_patch.transpose()
    #return unwpatch  #already written to unwpatch?

#%%
def inc_png_wrapper(imx, sbovl=False):
    imd = imdates[imx]
    if imd == imdates[-1]:
        return #skip last for increment

    ## Comparison of increment and daisy chain pair
    ifgd = '{}_{}'.format(imd, imdates[imx+1])
    incfile = os.path.join(incdir, '{}.inc'.format(ifgd))
    if sbovl:
        unwfile = os.path.join(ifgdir, ifgd, '{}.sbovldiff.adf.mm'.format(ifgd))
    else:
        unwfile = os.path.join(ifgdir, ifgd, '{}.unw'.format(ifgd))
    pngfile = os.path.join(incdir, '{}.inc_comp.png'.format(ifgd))

    inc = io_lib.read_img(incfile, length, width)

    try:
        unw = io_lib.read_img(unwfile, length, width)*coef_r2m
        ix_ifg = ifgdates.index(ifgd)
        if not sbovl:
            unw = unw - ref_unw[ix_ifg]
        else:
            print('  Skip subtracting reference for sbovl data.', flush=True)
    except:
        unw = np.zeros((length, width), dtype=np.float32)*np.nan

    ### Output png for comparison
    data3 = [np.angle(np.exp(1j*(data/coef_r2m/cycle))*cycle) for data in [unw, inc, inc-unw]]
    title3 = ['Daisy-chain IFG ({}pi/cycle)'.format(cycle*2), 'Inverted ({}pi/cycle)'.format(cycle*2), 'Difference ({}pi/cycle)'.format(cycle*2)]
    pngfile = os.path.join(incdir, '{}.increment.png'.format(ifgd))
    plot_lib.make_3im_png(data3, pngfile, cmap_wrap, title3, vmin=-np.pi, vmax=np.pi, cbar=False)

    if not keep_incfile:
        os.remove(incfile)

#%%
def resid_png_wrapper(i):
    ifgd = ifgdates[i]
    infile = os.path.join(resdir, '{}.res'.format(ifgd))
    resid = io_lib.read_img(infile, length, width)
    resid_rms = np.sqrt(np.nanmean(resid**2))
    with open(restxtfile, "a") as f:
        print('{} {:5.2f}'.format(ifgd, resid_rms), file=f)

    pngfile = infile+'.png'
    title = 'Residual (mm) of {} (RMS:{:.2f}mm)'.format(ifgd, resid_rms)
    plot_lib.make_im_png(resid, pngfile, cmap_vel, title, -wavelength/2*1000, wavelength/2*1000)

    if not keep_incfile:
        os.remove(infile)


#%% main
if __name__ == "__main__":
    sys.exit(main())
