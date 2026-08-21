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
LiCSBAS_vel_plate_motion.py -t tsdir [-f frame] [-o vel_pmm_fixed.tif] [--plate auto] [--vstd_fix] [--keep_absolute] [--azimuth]

 -t TS_GEOC_dir  TS folder with finished processing including step 16 (mandatory)
 -f frame_ID  In case your GEOC folder does not contain ENU tif files, provide frame ID
 -o  Output tif file (Default: vel_pmm_fixed.tif)
 --input Input vel file to be found inside tsdir/results folder (Default: vel.filt.mskd)
 --plate  Fix to given plate (Default: auto - based on centre coordinates) - must be one of:
  ['auto', 'Antartica', 'Arabia', 'Australia', 'Eurasia', 'India', 'Nazca', 'NorthAmerica', 'Nubia', 'Pacific', 'SouthAmerica', 'Somalia']
 --vstd_fix  Would also perform reference fix in vstd
 --keep_absolute  Do not fix to a reference point
 --azimuth   Use ENU files for azimuth directions (for sbovls)

Note it will use the final output, i.e. masked filtered velocity after step 16.
"""
#%% Change log
'''
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
    outfile = 'vel_pmm_fixed_los.tif'
    frame = None
    keep_absolute = False
    sbovl = False
    sbovl_abs = False  # if True, absolute velocity will be kept, otherwise it will be fixed to the reference area selected at step 16
    input = 'vel.filt.mskd'
    plate = 'auto'
    plates = ['auto', 'Antartica', 'Arabia', 'Australia', 'Eurasia', 'India', 'Nazca', 'NorthAmerica', 'Nubia',
              'Pacific', 'SouthAmerica', 'Somalia']
    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "ht:f:o:", ["help", "vstd_fix", "keep_absolute", "plate=", "sbovl", "sbovl_abs", "input="])
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
            elif o == '--sbovl':
                sbovl= True
            elif o == '--plate':
                plate = a
            elif o == '--sbovl_abs':
                sbovl = True
                sbovl_abs = True
                keep_absolute = True
                print("Running in sbovl mode, also absolute velocity will be kept.")
            elif o == '--input':
                input= a

        if sbovl:
            print("Running in sbovl mode")
            # keep_absolute = True
            if outfile == 'vel_pmm_fixed_los.tif':
                outfile = 'vel_pmm_fixed_azi.tif'

        if not tsdir:
            raise Usage('No tsdir given, -t is not optional!')
        elif not os.path.exists(tsdir):
            raise Usage('No {} exists! '.format(tsdir))
        elif not os.path.exists(os.path.join(tsdir, 'results', 'vel.filt.mskd')):
            if os.path.exists(os.path.join(tsdir, 'results', 'vel.mskd')):
                print('Warning, vel.filt.mskd does not exist, but vel.mskd exists. Will use it instead.')
                input = 'vel.mskd'
            elif sbovl_abs:
                if not os.path.exists(os.path.join(tsdir, 'results', input)):
                    raise Usage(f'Error, the {input} file does not exist - please check sbovl processing.')
            else:
                raise Usage('Error, the vel_filt.mskd file does not exist - please finish processing incl step 16')
        if plate not in plates:
            raise Usage('Error, please choose one of plates: '+plates)
    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2

    print(f'{input} will be processed for plate motion correction')
    #%%
    vel_tiffile = tsdir + '/results/' + input + '.tif'
    if plate == 'auto':
        print('loading additional libraries')
        try:
            import rioxarray
        except:
            raise RuntimeError('please install rioxarray')
        try:
            from licsbas_mintpy_PMM import get_plate_in_coord
        except:
            raise RuntimeError('please install licsar_extra')
        print('We will identify the plate based on centre lon, lat')
        vel = rioxarray.open_rasterio(vel_tiffile)
        clon, clat = float(vel.x.mean()), float(vel.y.mean())
        vel.close()
        plate = get_plate_in_coord(clon, clat)
        if not plate:
            raise Usage('No plate was found at the central coordinates - please set manually')
        print('Identified plate: '+plate)
        if plate not in plates:
            raise Usage('The selected plate is not supported')
        print('')

    #vfilt_file = tsdir+'/results/vel_filt.mskd'
    platesm = plate.lower()
    if sbovl:
        vel_platefile = tsdir+'/results/vel_'+platesm+'_azi.tif'
    else:
        vel_platefile = tsdir+'/results/vel_'+platesm+'_los.tif'
    vel_plate = lts.generate_pmm_velocity(frame, plate, 'GEOC', vel_platefile, azi=sbovl)
    # if not os.path.exists(vel_tiffile):   # why not to regenerate it....
    cmd = 'LiCSBAS_flt2geotiff.py -i {0}/results/{1} -p {0}/info/EQA.dem_par -o {2}'.format(tsdir, input, vel_tiffile)
    os.system(cmd)
    if not os.path.exists(vel_tiffile):
        print('ERROR, cannot generate '+vel_tiffile)
        exit()

    vel = lts.load_tif2xr(vel_tiffile)
    vel_plate_reshaped = vel_plate.interp_like(vel)

    vel.values = vel.values - vel_plate_reshaped.values
    # breakpoint()
    if not keep_absolute:
        print('\n Fixing to the reference area selected at step 16 \n')
        infodir = os.path.join(tsdir, 'info')
        reffile = os.path.join(infodir, '16ref.txt')
        if not os.path.exists(reffile):
            print('ERROR, no 16ref.txt file exists! Referring to the median of whole scene instead \n')
            vel = vel - vel.where(vel != 0).median()
        else:
            with open(reffile, "r") as f:
                refarea = f.read().split()[0]  # str, x1/x2/y1/y2
            refx1, refx2, refy1, refy2 = [int(s) for s in re.split('[:/]', refarea)]
            vel.values = vel.values - np.nanmean(vel.values[refy1:refy2, refx1:refx2])
    else:
        print('\n Keeping absolute velocity \n')
    lts.export_xr2tif(vel, outfile, dogdal = False)

    # %% Make png if specified
    if pngflag:
        pngfile = outfile[:-4] + '.png'
        if sbovl:
            title = 'Velocity fixed towards '+plate+' - Azimuth'
        else:
            title = 'Velocity fixed towards '+plate+' - LOS'
        cmin = np.nanpercentile(vel.values, 1)
        cmax = np.nanpercentile(vel.values, 99)
        plot_lib.make_im_png(vel.values, pngfile, cmap, title, cmin, cmax)

        pngfile = vel_platefile[:-4] + '.png'
        if sbovl:
            title = plate+'-fixed plate motion - Azimuth'
        else:
            title = plate+'-fixed plate motion - LOS'
        cmin = np.nanpercentile(vel_plate.values, 1)
        cmax = np.nanpercentile(vel_plate.values, 99)
        plot_lib.make_im_png(vel_plate.values, pngfile, cmap, title, cmin, cmax)

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
