#!/usr/bin/env python3
"""

========
Overview
========
This script makes a mask for time series using several noise indices. The pixel is masked if any of the values of the noise indices for a pixel is worse (larger or smaller) than a specified threshold.

===============
Input & output files
===============
Inputs in TS_GEOCml*/ :
 - results/[vel, coh_avg, n_unw, vstd, maxTlen, n_gap, stc,
            n_ifg_noloop, n_loop_err, resid_rms, n_nullify
            coh_avg_XX, n_loop_err_rat, loop_ph_avg_abs, n_gap_merged]
 - info/13parameters.txt
 
Outputs in TS_GEOCml*/
 - mask_ts[_mskd].png : Quick-look image of mask and noise indices
 - results/
   - vel.mskd[.png]   : Masked velocity
   - mask[.png]       : Mask
 - info/15parameters.txt : List of used parameters

=====
Usage
=====
LiCSBAS15_mask_ts.py -t tsadir [-c coh_thre] [-u n_unw_r_thre] [-v vstd_thre]
  [-T maxTlen_thre] [-g n_gap_thre] [-s stc_thre] [-i n_ifg_noloop_thre]
  [-l n_loop_err_thre] [-r resid_rms_thre] [--vmin float] [--vmax float]
  [--keep_isolated] [--noautoadjust] [--avg_phase_bias float] [--n_gap_use_merged]

 -t  Path to the TS_GEOCml* dir.
 -c  Threshold of coh_avg (average coherence)
 -u  Threshold of n_unw (number of used unwrap data)
     (Note this value is ratio to the number of images; i.e., 1.5*n_im)
 -v  Threshold of vstd (std of the velocity (mm/yr))
 -T  Threshold of maxTlen (max time length of connected network (year))
 -g  Threshold of n_gap (number of gaps in network)
 -s  Threshold of stc (spatio-temporal consistency (mm))
 -i  Threshold of n_ifg_noloop (number of pixels from ifgs with no loop)
 -l  Threshold of n_loop_err (number of loop_err) - in case of nullification in step 12, this will apply the threshold on n_nullify
 NOTE: we now test and will update the -l parameter to be a ratio (<=1 where 1 means all bad). Future: default: 0.7
 -L  Threshold of n_loop_err_ratio (number of loop_err divided by number of loops). Use number 0-1. (preferred solution)
 -r  Threshold of resid_rms (RMS of residuals in inversion (mm))
 --v[min|max]  Min|Max value for output figure of velocity (Default: auto)
 --avg_phase_bias  Threshold of the average absolute loop phase misclosure (phase bias) [rad] to use for masking (Default: not use. --avg_phase_bias 1 can be recommended)
 --n_gap_use_merged   Would use merged n_gaps instead of original (merging neighbouring gaps to one)
 --keep_isolated  Keep (not mask) isolated pixels
                  (Default: they are masked by stc)
 --noautoadjust  Do not auto adjust threshold when all pixels are masked
                 (Default: do auto adjust)

 Default thresholds for L-band:
   C-band : -c 0.05 -u 1.5 -v 100 -T 1 -g 10 -s 5  -i 50 -l 5 -r 2
   L-band : -c 0.01 -u 1   -v 200 -T 1 -g 1  -s 10 -i 50 -l 1 -r 10
 
"""
#%% Change log
'''
20241115 ML, UoL
 - use of n_gaps_merge
 20241103 MNergizci, UoL
 - add sbovl flag
20241107 ML, UoL
 - updated mask_ts.png
20240628 ML, UoL
 - use of avg_phase_bias
20231121 ML, UoL
 - use of n_nullify (with -l) and ratios of both loop_err and n_nullify with -L (should be better, will move to this, but now TO_CHECK status
v1.8.2 20211129 Milan Lazecky, Uni of Leeds
 - Change default -i as global number of no_loop_ifgs + 1
v1.8.1 20200911 Yu Morishita, GSI
 - Change default to -i 50
v1.8 20200902 Yu Morishita, GSI
 - Use nearest interpolation to avoid expanded nan
v1.7 20200224 Yu Morishita, Uni of Leeds and GSI
 - Change color of mask_ts.png
 - Update about parameters.txt
v1.6 20200124 Yu Morishita, Uni of Leeds and GSI
 - Increase default vstd threshold because vstd is not useful
v1.5 20200123 Yu Morishita, Uni of Leeds and GSI
 - Change default n_gap threshold for L-band to 1
v1.4 20200122 Yu Morishita, Uni of Leeds and GSI
 - Remove close fig which can cause error
v1.3 20191128 Yu Morishita, Uni of Leeds and GSI
 - Add noautoadjust option
v1.2 20190918 Yu Morishita, Uni of Leeds and GSI
 - Output mask_ts_mskd.png
v1.1 20190906 Yu Morishita, Uni of Leeds and GSI
 - tight_layout and auto ajust of size for png
v1.0 20190724 Yu Morishita, Uni of Leeds and GSI
 - Original implementation
'''

#%% Import
from LiCSBAS_meta import *
import getopt
import os, glob, re
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys
import time
import numpy as np
import cmcrameri.cm as cmc
import LiCSBAS_io_lib as io_lib
import LiCSBAS_plot_lib as plot_lib
import re
import warnings
import matplotlib
with warnings.catch_warnings(): ## To silence user warning
    warnings.simplefilter('ignore', UserWarning)
    matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams['axes.titlesize'] = 10

class Usage(Exception):
    """Usage context manager"""
    def __init__(self, msg):
        self.msg = msg


#%%
def add_subplot(fig, i, data, vmin, vmax, cmap, title, refarea = None, refcolor = 'red'):
    ''' refarea should be as tuple, e.g. (refx1, refx2, refy1, refy2)'''
    ax = fig.add_subplot(3, 5, i+1) #index start from 1
    im = ax.imshow(data, vmin=vmin, vmax=vmax, cmap=cmap, interpolation='nearest')
    fig.colorbar(im)
    ### replace the title n_ifg_noloop to n_pxl_noloop because using nullify ?
    if title.startswith("n_ifg_noloop"):
        title = re.sub(r"^n_ifg_noloop", "n_pxl_noloop", title)
 
    ax.set_title('{0}'.format(title))
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    if refarea:
        refx1, refx2, refy1, refy2 = refarea
        if refx2-refx1 < 5 and refy2-refy1 < 5:
            linewidth = 2
            refx1-=1
            refx2 += 1
            refy1 -= 1
            refy2 += 1
        else:
            linewidth = 1
        rect = Rectangle((refx1-0.5, refy1-0.5), refx2-refx1, refy2-refy1, fill=False, edgecolor=refcolor, linewidth=linewidth)
        ax.add_patch(rect)
    return ax

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
    thre_dict = {}
    vmin = []
    vmax = []
    use_coh_freq = False
    keep_isolated = False
    auto_adjust = True
    n_gap_use_merged = False
    sbovl = False
    cmap_vel = cmc.roma.reversed()
    cmap_noise = 'viridis'
    cmap_noise_r = 'viridis_r'
    
    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "ht:c:u:v:g:i:l:L:r:T:s:", ["version", "help", "vmin=", "vmax=", "avg_phase_bias=", "use_coh_freq", "keep_isolated", "noautoadjust","n_gap_use_merged","sbovl"])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                return 0
            elif o == '-t':
                tsadir = a
            elif o == '-c':
                thre_dict['coh_avg'] = float(a)
            elif o == '-u':
                thre_dict['n_unw_r'] = float(a)
            elif o == '-v':
                thre_dict['vstd'] = float(a)
            elif o == '-T':
                thre_dict['maxTlen'] = float(a)
            elif o == '-g':
                thre_dict['n_gap'] = int(a)
            elif o == '-s':
                thre_dict['stc'] = float(a)
            elif o == '-i':
                thre_dict['n_ifg_noloop'] = int(a)
            elif o == '-l':
                thre_dict['n_loop_err'] = int(a)   # TODO: after checking use of the ratio, remove this param and use the ratio only (below)
            elif o == '-L':
                thre_dict['n_loop_err_rat'] = float(a)
                #thre_dict['n_nullify_rat'] = float(a)  # 2024/01: n_loop_err_Rat is now before nullification
            elif o == '-r':
                thre_dict['resid_rms'] = float(a)
            elif o == '--avg_phase_bias':
                thre_dict['loop_ph_avg_abs'] = float(a)
            elif o == '--vmin':
                vmin = float(a)
            elif o == '--vmax':
                vmax = float(a)
            elif o == '--use_coh_freq':
                use_coh_freq = True
                print('not used yet')
            elif o == '--keep_isolated':
                keep_isolated = True
            elif o == '--noautoadjust':
                auto_adjust = False
            elif o == '--n_gap_use_merged':
                n_gap_use_merged = True
            elif o == '--sbovl':
                sbovl = True

        if not tsadir:
            raise Usage('No tsa directory given, -t is not optional!')
        elif not os.path.isdir(tsadir):
            raise Usage('No {} dir exists!'.format(tsadir))
        elif not os.path.isdir(os.path.join(tsadir, 'results')):
            raise Usage('No results dir exists in {}!'.format(tsadir))

    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2
 

    #%% Directory and file setting and get info
    tsadir = os.path.abspath(tsadir)
    resultsdir = os.path.join(tsadir,'results')

    inparmfile = os.path.join(tsadir, 'info', '13parameters.txt')
    if not os.path.exists(inparmfile):  ## for old LiCSBAS13 <v1.2
        inparmfile = os.path.join(tsadir, 'info', 'parameters.txt')
    outparmfile = os.path.join(tsadir, 'info', '15parameters.txt')
    maskts_png = os.path.join(tsadir,'mask_ts.png')
    maskts2_png = os.path.join(tsadir,'mask_ts_masked.png')
    
    if not n_gap_use_merged:
        ngapfile = 'n_gap'
    else:
        ngapfile = 'n_gap_merged'
    
    # rearranging:
    if sbovl:
        print(f'sbovl active so there is no n_loop_err_rat threshold')
        names = ['coh_avg', 'n_unw', 'vstd', 'maxTlen', ngapfile, 'stc', 'n_ifg_noloop', 'resid_rms']
        units = ['', '', 'mm/yr', 'yr', '', 'mm', '', 'mm']
    elif os.path.exists(os.path.join(resultsdir, 'n_loop_err_rat')):
        names = ['coh_avg', 'n_unw', 'vstd', 'maxTlen', ngapfile, 'stc', 'n_ifg_noloop', 'n_loop_err_rat', 'resid_rms']
    elif os.path.exists(os.path.join(resultsdir, 'n_loop_err')):
        names = ['coh_avg', 'n_unw', 'vstd', 'maxTlen', ngapfile, 'stc', 'n_ifg_noloop', 'n_loop_err', 'resid_rms']
        names = ['coh_avg', 'n_unw', 'vstd', 'maxTlen', ngapfile, 'stc', 'n_ifg_noloop', 'n_loop_err', 'resid_rms']
    else:
        raise Usage('no n_loop_err information - cancelling. Please rerun step 12 or contact dev team on recommendations how to skip this step.')
    units = ['', '', 'mm/yr', 'yr', '', 'mm', '', '', 'mm']
    if sbovl:
        gt_lt = ['lt', 'lt', 'gt', 'lt', 'gt', 'gt', 'gt', 'gt'] 
    else:    
        gt_lt = ['lt', 'lt', 'gt', 'lt', 'gt', 'gt', 'gt', 'gt', 'gt']  ## > or <
    ## gt: greater values than thre are masked
    ## lt: more little values than thre are masked (coh_avg, n_unw, maxTlen)

    if 'n_loop_err' in thre_dict and 'n_loop_err' not in names:
        names += ['n_loop_err']
        units += ['']
        gt_lt += ['gt']

    if 'loop_ph_avg_abs' in thre_dict:
        names += ['loop_ph_avg_abs']
        units += ['rad']
        gt_lt += ['gt']

    ### Get size and ref
    width = int(io_lib.get_param_par(inparmfile, 'range_samples'))
    length = int(io_lib.get_param_par(inparmfile, 'azimuth_lines'))
    wavelength = float(io_lib.get_param_par(inparmfile, 'wavelength'))

    n_im = int(io_lib.get_param_par(inparmfile, 'n_im'))

    # %% Get both 12 and 13 ref points, used only for plotting:
    infodir = os.path.join(tsadir, 'info')
    ref12file = os.path.join(infodir, '120ref.txt') # first checking if the 120ref exists (would be prioritised by step 12)
    if not os.path.exists(ref12file):
        ref12file = os.path.join(infodir, '12ref.txt')
    ref13file = os.path.join(infodir, '13ref.txt')

    with open(ref12file, "r") as f:
        ref12area = f.read().split()[0]  # str, x1/x2/y1/y2

    ref12x1, ref12x2, ref12y1, ref12y2 = [int(s) for s in re.split('[:/]', ref12area)]

    with open(ref13file, "r") as f:
        ref13area = f.read().split()[0]  # str, x1/x2/y1/y2

    ref13x1, ref13x2, ref13y1, ref13y2 = [int(s) for s in re.split('[:/]', ref13area)]


    #%% Determine default thresholds depending on frequency band
    if not 'maxTlen' in thre_dict: thre_dict['maxTlen'] = 1

    if (not 'n_loop_err_rat' in thre_dict) and ('n_loop_err_rat' in names):
        thre_dict['n_loop_err_rat'] = 0.7
    if not 'n_ifg_noloop' in thre_dict:
        try:
            thre_dict['n_ifg_noloop'] = len(os.listdir(os.path.join(tsadir, '12no_loop_ifg_ras')))+1
        except:
            thre_dict['n_ifg_noloop'] = 500

    if wavelength > 0.2: ## L-band
        if not 'coh_avg' in thre_dict: thre_dict['coh_avg'] = 0.01
        if not 'n_unw_r' in thre_dict: thre_dict['n_unw_r'] = 1.0
        if not 'vstd' in thre_dict: thre_dict['vstd'] = 200
        if not 'n_gap' in thre_dict: thre_dict['n_gap'] = 1
        if not 'stc' in thre_dict: thre_dict['stc'] = 10
        if (not 'n_loop_err' in thre_dict) and ('n_loop_err' in names): thre_dict['n_loop_err'] = 1
        if not 'resid_rms' in thre_dict: thre_dict['resid_rms'] = 10
    if wavelength < 0.2: ## C-band
        if not 'coh_avg' in thre_dict: thre_dict['coh_avg'] = 0.05
        if not 'n_unw_r' in thre_dict: thre_dict['n_unw_r'] = 1.5
        if not 'vstd' in thre_dict: thre_dict['vstd'] = 100
        if not 'n_gap' in thre_dict: thre_dict['n_gap'] = 10
        if not 'stc' in thre_dict: thre_dict['stc'] = 10 # tested as more appropriate
        if not sbovl:
            if (not 'n_loop_err' in thre_dict) and ('n_loop_err' in names): thre_dict['n_loop_err'] = 5
        if not 'resid_rms' in thre_dict: thre_dict['resid_rms'] = 15
    
    thre_dict['n_unw'] = int(n_im*thre_dict['n_unw_r'])
    if n_gap_use_merged:
        thre_dict['n_gap_merged'] = thre_dict.pop('n_gap')
    
    #%% Read data
    velfile = os.path.join(resultsdir,'vel')
    vel = io_lib.read_img(velfile, length, width)
    bool_nan = np.isnan(vel)
    bool_nan[vel==0] = True ## Ref point. Unmask later
    n_pt_all = (~bool_nan).sum() ## Number of unnan points

    data_dict = {}
    for name in names:
        file = os.path.join(resultsdir, name)
        data_dict[name] = io_lib.read_img(file, length, width)

    ## stc is always nan at isolted pixels.
    if keep_isolated:
        ## Give 0 to keep isolated pixels
        data_dict['stc'][np.isnan(data_dict['stc'])] = 0
    else:
        ## Give stc_thre to remove isolated pixels
        data_dict['stc'][np.isnan(data_dict['stc'])] = thre_dict['stc']+1
        

    #%% Make mask
    ### Evaluate only valid pixels in vel
    mask_pt = np.ones_like(vel)[~bool_nan]
    mskd_rate = []
    
    for i, name in enumerate(names):
        _data = data_dict[name][~bool_nan]
        _thre = thre_dict[name]

        if gt_lt[i] == 'lt': ## coh_avg, n_unw, maxTlen
            ## Multiply -1 to treat as if gt
            _data = -1*_data
            _thre = -1*_thre

        ### First check if the thre masks not all pixels
        ### If all pixels are masked, change thre to the max/min value
        if auto_adjust:
            minvalue = np.nanmin(_data)
            if minvalue > _thre:
                print('\nAll pixels would be masked with {} thre of {}'.format(name, thre_dict[name]), flush=True)
                thre_dict[name] = np.ceil(minvalue)
                _thre = thre_dict[name]
                if gt_lt[i] == 'lt':
                    thre_dict[name] = -1*thre_dict[name]
                print('Automatically change the thre to {} (ceil of min value)'.format(thre_dict[name]), flush=True)

        ### Make mask for this index
        with warnings.catch_warnings(): ## To silence RuntimeWarning of nan<thre
            warnings.simplefilter('ignore', RuntimeWarning)
            _mask_pt = (_data <= _thre) # nan returns false
        mskd_rate.append((1-_mask_pt.sum()/n_pt_all)*100)
        mask_pt = mask_pt*_mask_pt
    
    ### Make total mask
    mask = np.ones_like(vel)*np.nan
    mask[~bool_nan] = mask_pt  #1:valid, 0:masked, nan:originally nan
    mask[vel==0] = 1 ## Retrieve ref point

    ### Apply mask
    vel_mskd = vel*mask
    vel_mskd[mask==0] = np.nan
        
    ### Count total mask
    n_nomask = int(np.nansum(mask))
    rate_nomask = n_nomask/n_pt_all*100


    #%% Stdout and save info
    with open(outparmfile, "w") as f:
        print('')
        print('Noise index    : Threshold  (rate to be masked)')
        print('Noise index    : Threshold  (rate to be masked)', file=f)
        for i, name in enumerate(names):
            print('- {:12s} : {:4} {:5} ({:4.1f}%)'.format(name, thre_dict[name], units[i], mskd_rate[i]))
            print('- {:12s} : {:4} {:5} ({:4.1f}%)'.format(name, thre_dict[name], units[i], mskd_rate[i]), file=f)
        print('')
        print('', file=f)
        print('Masked pixels  : {}/{} ({:.1f}%)'.format(n_pt_all-n_nomask, n_pt_all, 100-rate_nomask))
        print('Masked pixels  : {}/{} ({:.1f}%)'.format(n_pt_all-n_nomask, n_pt_all, 100-rate_nomask), file=f)
        print('Kept pixels    : {}/{} ({:.1f}%)\n'.format(n_nomask, n_pt_all, rate_nomask), flush=True)
        print('Kept pixels    : {}/{} ({:.1f}%)\n'.format(n_nomask, n_pt_all, rate_nomask), file=f)

    if n_nomask == 1:
        print('All pixels are masked!!', file=sys.stderr)
        print('Try again with different threshold.\n', file=sys.stderr)
        return 1


    #%% Prepare for png
    ## Set color range for vel
    if not vmin: ## auto
        vmin = np.nanpercentile(vel_mskd, 1)
        if np.isnan(vmin): ## In case no data in vel_mskd
            vmin = np.nanpercentile(vel, 1)
    if not vmax: ## auto
        vmax = np.nanpercentile(vel_mskd, 99)
        if np.isnan(vmax): ## In case no data in vel_mskd 
            vmax = np.nanpercentile(vel, 1)
        

    #%% Output thumbnail png
    if length > width:
        figsize_y = 9
        if len(names) == 12:
            figsize_x = int(figsize_y*4/3*width/length+2)
        else:
            figsize_x = int(figsize_y * 5 / 3 * width / length + 2)   # adding extra column
        if figsize_x < 6: figsize_x = 6
    else:
        figsize_x = 12
        if len(names) == 12:
            figsize_y = int(figsize_x/4*3*length/width)
        else:
            figsize_y = int(figsize_x / 5 * 3 * length / width)
        if figsize_y < 4: figsize_y = 4
    
    fig = plt.figure(figsize = (figsize_x, figsize_y))
    fig2 = plt.figure(figsize = (figsize_x, figsize_y))

    ##First 3; vel.mskd, vel, mask
    data = [vel_mskd, vel, mask]
    titles = ['vel.mskd', 'vel', 'mask']
    vmins = [vmin, vmin, 0]
    vmaxs = [vmax, vmax, 1]
    cmaps = [cmap_vel, cmap_vel, cmap_noise]
    refarea = (ref13x1, ref13x2, ref13y1, ref13y2)
    refcolor = 'black'
    for i in range(3):
        ax1 = add_subplot(fig, i, data[i], vmins[i], vmaxs[i], cmaps[i], titles[i], refarea, refcolor)
        i2 = 0 if i==1 else 1 if i==0 else 2 # inv vel and vel.mskd
        ax2 = add_subplot(fig2, i2, data[i], vmins[i], vmaxs[i], cmaps[i], titles[i], refarea, refcolor)
    # for mask, also show the previous refarea from step 12:
    rect1 = Rectangle((ref12x1 - 0.5, ref12y1 - 0.5), ref12x2 - ref12x1, ref12y2 - ref12y1, fill=False, edgecolor='red',
                     linewidth=1)
    rect2 = Rectangle((ref12x1 - 0.5, ref12y1 - 0.5), ref12x2 - ref12x1, ref12y2 - ref12y1, fill=False, edgecolor='red',
                      linewidth=1)
    ax1.add_patch(rect1)
    ax2.add_patch(rect2)


    ## Next 9+ noise indices
    mask_nan = mask.copy()
    mask_nan[mask==0] = np.nan
    for i, name in enumerate(names):
        data = data_dict[name]
        ## Mask nan in vel for each indeces except coh_avg and n_unw
        if not name == 'coh_avg' and not name == 'n_unw':
            data[bool_nan] = np.nan
        
        if gt_lt[i] == 'lt': ## coh_avg, n_unw, maxTlen
            cmap = cmap_noise
            vmin_n = thre_dict[name]*0.8
            vmax_n = np.nanmax(data)
        else:
            cmap = cmap_noise_r
            vmin_n = 0
            vmax_n = thre_dict[name]*1.2

        # add refp12(0) for loop_err, and refp13 for resid_rms:
        # max: # names = ['coh_avg', 'n_unw', 'vstd', 'maxTlen', 'n_gap', 'stc', 'n_ifg_noloop', 'n_loop_err_rat', 'resid_rms', 'loop_ph_avg_abs', 'n_loop_err' ]
        if name in ['n_loop_err_rat', 'loop_ph_avg_abs', 'n_loop_err']:
            refarea = (ref12x1, ref12x2, ref12y1, ref12y2)
            refcolor = 'red'
        elif name in ['resid_rms', 'vstd']:
            refarea = (ref13x1, ref13x2, ref13y1, ref13y2)
            refcolor = 'black'
        else:
            refarea = None
            refcolor = None

        title = '{} {}({})'.format(name, units[i], thre_dict[name])
        add_subplot(fig, i+3, data, vmin_n, vmax_n, cmap, title, refarea, refcolor)
        add_subplot(fig2, i+3, data*mask_nan, vmin_n, vmax_n, cmap, title, refarea, refcolor)
        #i+3 because 3 data already plotted
              

    fig.tight_layout()
    fig.savefig(maskts_png)
    fig2.tight_layout()
    fig2.savefig(maskts2_png)
    
#    plt.close(fig=fig)

    
    #%% Output vel.mskd and mask
    velmskdfile = os.path.join(resultsdir,'vel.mskd')
    vel_mskd.tofile(velmskdfile)

    pngfile = velmskdfile+'.png'
    title = 'Masked velocity (mm/yr)'
    plot_lib.make_im_png(vel_mskd, pngfile, cmap_vel, title, vmin, vmax)


    maskfile = os.path.join(resultsdir,'mask')
    mask.tofile(maskfile)

    pngfile = maskfile+'.png'
    title = 'Mask'
    plot_lib.make_im_png(mask, pngfile, cmap_noise, title, 0, 1)

    
    #%% Finish
    elapsed_time = time.time()-start
    hour = int(elapsed_time/3600)
    minite = int(np.mod((elapsed_time/60),60))
    sec = int(np.mod(elapsed_time,60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour,minite,sec))

    print('\n{} Successfully finished!!\n'.format(os.path.basename(argv[0])))
    print('Output png: {}\n'.format(os.path.relpath(maskts_png)), flush=True)


#%% main
if __name__ == "__main__":
    sys.exit(main())
