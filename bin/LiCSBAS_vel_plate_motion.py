#!/usr/bin/env python3
"""
2025-01-22 ML

========
Overview
========
This script will remove plate motion effect from velocity and reference effect from vstd.
Must be run from the folder containing GEOC with ENU.tif files. If this is not the case, please provide frame ID (works on LiCSAR only, for now).
Finally, note it expects you to have the filtered masked velocity calculated, i.e. please run step 16 first (on masked dataset)

=====
Usage
=====
LiCSBAS_vel_plate_motion.py -t tsdir [-f frame] [-o vel_pmm_fixed.tif] [--vstd_fix] [--keep_absolute]

 -t TS_GEOC_dir  TS folder with finished processing including step 16 (mandatory)
 -f frame_ID  In case your GEOC folder does not contain ENU tif files, provide frame ID
 -o  Output tif file (Default: vel_pmm_fixed.tif)
 --vstd_fix  Would also perform reference fix in vstd
 --keep_absolute  Do not fix to a reference point

Note it will use the final output, i.e. masked filtered velocity after step 16.
"""
#%% Change log
'''
v1.0 20250122 Milan Lazecky, Uni of Leeds
 - Original implementation
'''

#%% Import
import getopt
import os
import re
import sys
import time
import numpy as np
import LiCSBAS_plot_lib as plot_lib
import lics_tstools as lts
import cmcrameri.cm as cmc

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
    pngflag = True
    cmap = cmc.roma.reversed()

    vstd_fix = False
    tsdir = ''
    outfile = 'vel_pmm_fixed.tif'
    frame = None
    keep_absolute = False
    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "ht:f:o:", ["help", "vstd_fix", "keep_absolute"])
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
            elif o == '--vstd_fix':
                vstd_fix = True
            elif o == '--keep_absolute':
                keep_absolute = True
            elif o == '-o':
                outfile = a

        if not tsdir:
            raise Usage('No tsdir given, -t is not optional!')
        elif not os.path.exists(tsdir):
            raise Usage('No {} exists! '.format(tsdir))
        elif not os.path.exists(tsdir+'/results/vel.filt.mskd'):
            raise Usage('Error, the vel_filt.mskd file does not exist - please finish processing incl step 16')

    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2


    #%%
    #vfilt_file = tsdir+'/results/vel_filt.mskd'
    vlos_eurfile = tsdir+'/results/vel_eurasia_los.tif'
    #if not os.path.exists(vlos_eurfile):
    vlos_eurasia = lts.generate_pmm_velocity(frame, 'Eurasia', 'GEOC', vlos_eurfile)
    #else:
    #    vlos_eurasia = lts.load_tif2xr(vlos_eurfile)
    vel_tiffile = tsdir+'/results/vel.filt.mskd.tif'
    # if not os.path.exists(vel_tiffile):   # why not to regenerate it....
    cmd = 'LiCSBAS_flt2geotiff.py -i {0}/results/vel.filt.mskd -p {0}/info/EQA.dem_par -o {0}/results/vel.filt.mskd.tif'.format(tsdir)
    os.system(cmd)
    if not os.path.exists(vel_tiffile):
        print('ERROR, cannot generate vlos tif file')
        exit()

    vlos = lts.load_tif2xr(vel_tiffile)
    vlos_eurasia_reshaped = vlos_eurasia.interp_like(vlos)

    vlos.values = vlos.values - vlos_eurasia_reshaped.values
    if not keep_absolute:
        print('\n Fixing to the reference area selected at step 16 \n')
        reffile = os.path.join(tsdir, 'info', '16ref.txt')
        if not os.path.exists(reffile):
            print('ERROR, no 16ref.txt file exists! Referring to the median of whole scene instead \n')
            vlos = vlos - vlos.where(vlos != 0).median()
        else:
            with open(reffile, "r") as f:
                refarea = f.read().split()[0]  # str, x1/x2/y1/y2
            refx1, refx2, refy1, refy2 = [int(s) for s in re.split('[:/]', refarea)]
            vlos.values = vlos.values - np.nanmean(vlos.values[refy1:refy2, refx1:refx2])
    lts.export_xr2tif(vlos, outfile, dogdal = False)

    # %% Make png if specified
    if pngflag:
        pngfile = outfile[:-4] + '.png'
        title = 'Velocity fixed towards Eurasia'
        cmin = np.nanpercentile(vlos.values, 1)
        cmax = np.nanpercentile(vlos.values, 99)
        plot_lib.make_im_png(vlos.values, pngfile, cmap, title, cmin, cmax)

        pngfile = vlos_eurfile[:-4] + '.png'
        title = 'Eurasia-fixed plate motion'
        cmin = np.nanpercentile(vlos_eurasia.values, 1)
        cmax = np.nanpercentile(vlos_eurasia.values, 99)
        plot_lib.make_im_png(vlos_eurasia.values, pngfile, cmap, title, cmin, cmax)

    if vstd_fix:
        # recalc vstd
        #if not os.path.exists(tsdir+'/results/vstd.tif'):
        print('generating vstd tif')
        cmd = 'LiCSBAS_flt2geotiff.py -i {0}/results/vstd -p {0}/info/EQA.dem_par -o {0}/results/vstd.tif'.format(tsdir)
        os.system(cmd)
        #
        print('updating vstd (removing reference effect)')
        cmd = 'cd {0}/results; LiCSBAS_remove_reference_effect_from_vstd.py'.format(tsdir)
        os.system(cmd)



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
