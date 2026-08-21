#!/usr/bin/env python3
"""
2025-01-22 ML

========
Overview
========
This script will remove plate motion effect from cumulative displacement
Must be run from the folder containing GEOC with ENU.tif files. If this is not the case, please provide frame ID (works on LiCSAR only, for now).
Finally, note it expects you to have the filtered masked velocity calculated, i.e. please run step 16 first (on masked dataset)

=====
Usage
=====
LiCSBAS_cum_plate_motion.py -t tsdir [-f frame] [-o cum_pmm_fixed.tif] [--vstd_fix] [--keep_absolute]

 -t TS_GEOC_dir  TS folder with finished processing including step 16 (mandatory)
 -f frame_ID  In case your GEOC folder does not contain ENU tif files, provide frame ID
 -o  Output tif file (Default: cum_pmm_fixed.tif)
 --imd_p  First date
 --imd_s  Last date
 --vstd_fix  Would also perform reference fix in vstd
 --keep_absolute  Do not fix to a reference point

Note it will use the final output, i.e. masked filtered velocity after step 16.
"""
#%% Change log
'''
v1.0 20250122 Muhammet Nergizci, Uni of Leeds
 - Cumulative displacement plate motion effect removal

v1.0 20250122 Milan Lazecky, Uni of Leeds
 - Original implementation
'''

#%% Import
import getopt
import re
import os
import re
import sys
import time
import numpy as np
import LiCSBAS_plot_lib as plot_lib
import lics_tstools as lts
import cmcrameri.cm as cmc
from datetime import datetime

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

    #%% Set default
    pngflag = False
    cmap = cmc.roma.reversed()

    vstd_fix = False
    tsdir = ''
    outfile = 'cum_pmm_fixed_los.tif'
    frame = None
    keep_absolute = False
    sbovl = False
    sbovl_abs = False  # if True, absolute velocity will be kept, otherwise it will be fixed to the reference area selected at step 16
    imd_p = ''
    imd_s = ''
    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "ht:f:o:p:s:", ["help", "vstd_fix", "keep_absolute", "sbovl", "sbovl_abs", "imd_p=", "imd_s="])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                return 0
            elif o == '-t':
                tsdir = a
            elif o == '-f':
                frame = a
            elif o == '--keep_absolute':
                keep_absolute = True
            elif o == '-o':
                outfile = a
            elif o == '-p':
                imd_p = a
            elif o == '-s':
                imd_s = a
            elif o == '--sbovl':
                sbovl= True
            elif o == '--sbovl_abs':
                sbovl = True
                sbovl_abs = True
                keep_absolute = True
                print("Running in sbovl mode, also absolute velocity will be kept.")

        if sbovl:
            print("Running in sbovl mode")
            # keep_absolute = True
            if outfile == 'vel_pmm_fixed_los.tif':
                outfile = 'vel_pmm_fixed_azi.tif'

        if not imd_p or not imd_s:
            raise Usage('No imd_p or imd_s given, -p and -s are not optional!')
        input = f'cum_filt_{imd_p}-{imd_s}.mask'
        
        if not tsdir:
            raise Usage('No tsdir given, -t is not optional!')
        elif not os.path.exists(tsdir):
            raise Usage('No {} exists! '.format(tsdir))
        elif not os.path.exists(os.path.join(tsdir, 'results', input)):
            if os.path.exists(os.path.join(tsdir, 'results', f'cum_{imd_p}-{imd_s}.mask')):
                print('Warning, cum_filt does not exist, but cum exists. Will use it instead.')
                input = f'cum_{imd_p}-{imd_s}.mask'
            elif sbovl_abs:
                if not os.path.exists(os.path.join(tsdir, 'results', input)):
                    raise Usage(f'Error, the {input} file does not exist - please check sbovl processing.')
            else:
                raise Usage('Error, the cum_filt.mskd file does not exist - please finish processing incl step 16')

    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2

    print(f'{input} will be processed for plate motion correction')
    #%%
    #vfilt_file = tsdir+'/results/vel_filt.mskd'
    if sbovl:
        vlos_eurfile = tsdir+'/results/vel_eurasia_azi.tif'
    else:
        vlos_eurfile = tsdir+'/results/vel_eurasia_los.tif'
    #if not os.path.exists(vlos_eurfile):
    vlos_eurasia = lts.generate_pmm_velocity(frame, 'Eurasia', 'GEOC', vlos_eurfile, sbovl=sbovl)
    #else:
    #    vlos_eurasia = lts.load_tif2xr(vlos_eurfile)
    cum_tiffile = tsdir+f'/results/cum_filt_{imd_p}-{imd_s}.mask.tif'
    # if not os.path.exists(vel_tiffile):   # why not to regenerate it....
    cmd = f'LiCSBAS_flt2geotiff.py -i {tsdir}/results/{input} -p {tsdir}/info/EQA.dem_par -o {tsdir}/results/cum_filt_{imd_p}-{imd_s}.mask.tif'
    # breakpoint()
    os.system(cmd)
    if not os.path.exists(cum_tiffile):
        print('ERROR, cannot generate vlos tif file')
        exit()

    # breakpoint()
    cumlos = lts.load_tif2xr(cum_tiffile)
    delta_days = (datetime.strptime(imd_s, "%Y%m%d") - datetime.strptime(imd_p, "%Y%m%d")).days
    cumlos_eurasia = vlos_eurasia / 365 * delta_days
    cumlos_eurasia_reshaped = cumlos_eurasia.interp_like(cumlos)
    
    ##save and plot
    cumlos_eurasia_reshaped_file = os.path.join(tsdir, f'results/cum_eurasia_{imd_p}-{imd_s}')
    # breakpoint()
    cumlos_eurasia_reshaped.values.astype('float32').tofile(cumlos_eurasia_reshaped_file)
    os.system(f"LiCSBAS_disp_img.py -i {cumlos_eurasia_reshaped_file} -p {tsdir}/info/EQA.dem_par --png {tsdir}/results/cum_eurasia_{imd_p}-{imd_s}.png --title cum_eurasia_{imd_p}-{imd_s}")
    # breakpoint()   
    
    cumlos.values = cumlos.values - cumlos_eurasia_reshaped.values
    # breakpoint()
    if not keep_absolute:
        print('\n Fixing to the reference area selected at step 16 \n')
        infodir = os.path.join(tsdir, 'info')
        reffile = os.path.join(infodir, '16ref.txt')
        if not os.path.exists(reffile):
            print('ERROR, no 16ref.txt file exists! Referring to the median of whole scene instead \n')
            cumlos = cumlos - cumlos.where(cumlos != 0).median()
        else:
            with open(reffile, "r") as f:
                refarea = f.read().split()[0]  # str, x1/x2/y1/y2
            refx1, refx2, refy1, refy2 = [int(s) for s in re.split('[:/]', refarea)]
            cumlos.values = cumlos.values - np.nanmean(cumlos.values[refy1:refy2, refx1:refx2])
    else:
        print('\n Keeping absolute velocity \n')
    lts.export_xr2tif(cumlos, outfile, dogdal = False)

    # %% Make png if specified
    if pngflag:
        pngfile = outfile[:-4] + '.png'
        if sbovl:
            title = 'Cum fixed towards Eurasia - Azimuth'
        else:
            title = 'Cum fixed towards Eurasia  - LOS'
        cmin = -100
        cmax =  100
        plot_lib.make_im_png(cumlos.values, pngfile, cmap, title, cmin, cmax)

        pngfile = vlos_eurfile[:-4] + '.png'
        if sbovl:
            title = 'Eurasia-fixed plate motion - Azimuth'
        else:
            title = 'Eurasia-fixed plate motion - LOS'
        cmin = np.nanpercentile(cumlos_eurasia.values, 1)
        cmax = np.nanpercentile(cumlos_eurasia.values, 99)
        plot_lib.make_im_png(cumlos_eurasia.values, pngfile, cmap, title, cmin, cmax)


    #%% Finish
    elapsed_time = time.time()-start
    hour = int(elapsed_time/3600)
    minite = int(np.mod((elapsed_time/60),60))
    sec = int(np.mod(elapsed_time,60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour,minite,sec))

    print('\n{} Successfully finished!!\n'.format(os.path.basename(argv[0])))
    print('Output: {}\n'.format(outfile), flush=True)


#%% main
if __name__ == "__main__":
    sys.exit(main())
