#!/usr/bin/env python3
"""

This script converts GeoTIFF files of unw and cc to float32 and uint8 format, respectively, for further time series analysis, and also downsamples (multilooks) data if specified. Existing files are not re-created to save time, i.e., only the newly available data will be processed.

====================
Input & output files
====================
Inputs:
 - GEOC/
   - yyyymmdd_yyyymmdd/
     - yyyymmdd_yyyymmdd.geo.unw.tif
     - yyyymmdd_yyyymmdd.geo.cc.tif
     - yyyymmdd_yyyymmdd.geo.sbovldiff.adf.mm.tif (if --sbovl is used)
     - yyyymmdd_yyyymmdd.geo.sbovldiff.adf.cc.tif (if --sbovl is used)
  [- *.geo.mli.tif]
  [- *.geo.hgt.tif]
  [- *.geo.[E|N|U].tif]
  [- baselines]
  [- metadata.txt]

Outputs in GEOCml*/ (downsampled if indicated):
 - yyyymmdd_yyyymmdd/
   - yyyymmdd_yyyymmdd.unw[.png] (float32)
   - yyyymmdd_yyyymmdd.cc (uint8)
   - yyyymmdd_yyyymmdd.sbovldiff.adf.mm[.png] (float32) (if --sbovl is used)
   - yyyymmdd_yyyymmdd.sbovldiff.adf.cc (uint8) (if --sbovl is used)
 - baselines (may be dummy)
 - EQA.dem_par
 - slc.mli.par
 - slc.mli[.png] (if input exists)
 - hgt[.png] (if input exists)
 - [E|N|U].geo (if input exists)
 - no_unw_list.txt (if there are unavailable unw|cc)

=====
Usage
=====
LiCSBAS02_ml_prep.py -i GEOCdir [-o GEOCmldir] [-n nlook] [--freq float] [--n_para int] [--plot_cc] [--sbovl]

 -i  Path to the input GEOC dir containing stack of geotiff data
 -o  Path to the output GEOCml dir (Default: GEOCml[nlook])
 -n  Number of donwsampling factor (Default: 1, no downsampling)
 --freq    Radar frequency in Hz (Default: 5.405e9 for Sentinel-1)
           (e.g., 1.27e9 for ALOS, 1.2575e9 for ALOS-2/U, 1.2365e9 for ALOS-2/{F,W})
 --n_para  Number of parallel processing (Default: # of usable CPU)
 --plot_cc Plot coherence png image
 --sbovl multilook sbovl or bovl
 
"""
#%% Change log
'''
v1.14.2a 20231030 M Nergizci, UoL
 - sbovl flag addding
v1.14.2a 20230921 ML
 - Dimensions check
v1.7.5  20230803 Jack McGrath, Uni Leeds
 - Add cc png option
v1.7.4b 20211111 Milan Lazecky, UniLeeds
 - fix for rerunning
v1.7.4 20201119 Yu Morishita, GSI
 - Change default cmap for wrapped phase from insar to SCM.romaO
v1.7.3 20201118 Yu Morishita, GSI
 - Again Bug fix of multiprocessing
v1.7.2 20201116 Yu Morishita, GSI
 - Bug fix of multiprocessing in Mac python>=3.8
v1.7.1 20201028 Yu Morishita, GSI
 - Update how to get n_para
v1.7 20201020 Yu Morishita, GSI
 - Remove -f option and not download tifs here
v1.6.1 20201016 Yu Morishita, GSI
 - Deal with mli and hgt in other dtype
v1.6 20201008 Yu Morishita, GSI
 - Add --freq option
v1.5.1 20200916 Yu Morishita, GSI
 - Bug fix in handling cc float
v1.5 20200909 Yu Morishita, GSI
 - Parallel processing
v1.4 20200228 Yu Morishita, Uni of Leeds and GSI
 - Change format of output cc from float32 to uint8
 - Add center_time into slc.mli.par
v1.3 20191115 Yu Morishita, Uni of Leeds and GSI
 - Use mli and hgt
v1.2 20191014 Yu Morishita, Uni of Leeds and GSI
 - Deal with format of uint8 of cc.tif
 - Not available mli
v1.1 20190824 Yu Morishita, Uni of Leeds and GSI
 - Skip broken geotiff
v1.0 20190731 Yu Morishita, Uni of Leeds and GSI
 - Original implementation
'''

print('Starting')
#%% Import
from LiCSBAS_meta import *
import getopt
import os
import sys
import time
import shutil
from osgeo import gdal
import glob
import numpy as np
import subprocess as subp
import multiprocessing as multi
import cmcrameri.cm as cmc #SCM
import LiCSBAS_io_lib as io_lib
import LiCSBAS_tools_lib as tools_lib
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
    print("\n{} ver{} {} {}".format(os.path.basename(argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(argv[0]), ' '.join(argv[1:])), flush=True)

    ### For parallel processing
    global ifgdates2, geocdir, outdir, nlook, n_valid_thre, cycle, cmap_wrap, plot_cc, cmap_cc, width, length


    #%% Set default
    geocdir = []
    outdir = []
    nlook = 1
    plot_cc = False
    sbovl = False
    rngoff = False
    radar_freq = 5.405e9
    try:
        n_para = len(os.sched_getaffinity(0))
    except:
        n_para = multi.cpu_count()

    cmap_wrap = cmc.romaO #SCM.romaO
    cmap_cc = cmc.batlow #SCM.batlow
    cycle = 3 #default of ifg, (75 for sbovl)
    n_valid_thre = 0.5
    q = multi.get_context('fork')


    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hi:o:n:", ["help", "plot_cc", "freq=", "n_para=", "sbovl", "rngoff"])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                return 0
            elif o == '-i':
                geocdir = a
            elif o == '-o':
                outdir = a
            elif o == '-n':
                nlook = int(a)
            elif o == '--freq':
                radar_freq = float(a)
            elif o == '--n_para':
                n_para = int(a)
            elif o == '--plot_cc':
                plot_cc = True
            elif o == '--sbovl':
                sbovl = True
            elif o == '--rngoff':
                rngoff = True
                raise Usage('The --rngoff functionality has to be yet implemented. Cancelling now.')

        if not geocdir:
            raise Usage('No GEOC directory given, -d is not optional!')
        elif not os.path.isdir(geocdir):
            raise Usage('No {} dir exists!'.format(geocdir))

    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2


    #%% Directory and file setting
    geocdir = os.path.abspath(geocdir)
    if not outdir:
        outdir = os.path.join(os.path.dirname(geocdir), 'GEOCml{}'.format(nlook))
    if not os.path.exists(outdir): os.mkdir(outdir)

    mlipar = os.path.join(outdir, 'slc.mli.par')
    dempar = os.path.join(outdir, 'EQA.dem_par')

    no_unw_list = os.path.join(outdir, 'no_unw_list.txt')
    if os.path.exists(no_unw_list): os.remove(no_unw_list)

    bperp_file_in = os.path.join(geocdir, 'baselines')
    bperp_file_out = os.path.join(outdir, 'baselines')

    metadata_file = os.path.join(geocdir, 'metadata.txt')
    if os.path.exists(metadata_file):
        center_time = subp.check_output(['grep', 'center_time', metadata_file]).decode().split('=')[1].strip()
    else:
        center_time = None


    #%% ENU
    for ENU in ['E', 'N', 'U']:
        print('\nCreate {}'.format(ENU+'.geo'), flush=True)
        enutif = glob.glob(os.path.join(geocdir, '*.geo.{}.tif'.format(ENU)))

        ### Download if not exist
        if len(enutif)==0:
            print('  No *.geo.{}.tif found in {}'.format(ENU, os.path.basename(geocdir)), flush=True)
            continue

        else:
            enutif = enutif[0] ## first one

        ### Create float
        data = gdal.Open(enutif).ReadAsArray()
        data[data==0] = np.nan

        if nlook != 1:
            ### Multilook
            data = tools_lib.multilook(data, nlook, nlook)

        outfile = os.path.join(outdir, ENU+'.geo')
        data.tofile(outfile)
        print('  {}.geo created'.format(ENU), flush=True)


    #%% mli
    print('\nCreate slc.mli', flush=True)
    mlitif = glob.glob(os.path.join(geocdir, '*.geo.mli.tif'))
    if len(mlitif)>0:
        mlitif = mlitif[0] ## First one
        mli = np.float32(gdal.Open(mlitif).ReadAsArray())
        mli[mli==0] = np.nan

        if nlook != 1:
            ### Multilook
            mli = tools_lib.multilook(mli, nlook, nlook)

        mlifile = os.path.join(outdir, 'slc.mli')
        mli.tofile(mlifile)
        mlipngfile = mlifile+'.png'
        mli = np.log10(mli)
        vmin = np.nanpercentile(mli, 5)
        vmax = np.nanpercentile(mli, 95)
        plot_lib.make_im_png(mli, mlipngfile, 'gray', 'MLI (log10)', vmin, vmax, cbar=True)
        print('  slc.mli[.png] created', flush=True)
    else:
        print('  No *.geo.mli.tif found in {}'.format(os.path.basename(geocdir)), flush=True)


    #%% hgt
    print('\nCreate hgt', flush=True)
    hgttif = glob.glob(os.path.join(geocdir, '*.geo.hgt.tif'))
    if len(hgttif)>0:
        hgttif = hgttif[0] ## First one
        hgt = np.float32(gdal.Open(hgttif).ReadAsArray())
        hgt[hgt==0] = np.nan

        if nlook != 1:
            ### Multilook
            hgt = tools_lib.multilook(hgt, nlook, nlook)

        hgtfile = os.path.join(outdir, 'hgt')
        hgt.tofile(hgtfile)
        hgtpngfile = hgtfile+'.png'
        vmax = np.nanpercentile(hgt, 99)
        vmin = -vmax/3 ## bnecause 1/4 of terrain is blue
        plot_lib.make_im_png(hgt, hgtpngfile, 'terrain', 'DEM (m)', vmin, vmax, cbar=True)
        print('  hgt[.png] created', flush=True)
    else:
        print('  No *.geo.hgt.tif found in {}'.format(os.path.basename(geocdir)), flush=True)


    #%% tif -> float (with multilook/downsampling)
    print('\nCreate unw and cc', flush=True)
    ifgdates = tools_lib.get_ifgdates(geocdir)
    n_ifg = len(ifgdates)

    ### First check if float already exist
    ifgdates2 = []
    if sbovl:
        sbovldates = []
    for i, ifgd in enumerate(ifgdates):
        ifgdir1 = os.path.join(outdir, ifgd)
        unwfile = os.path.join(ifgdir1, ifgd+'.unw')
        ccfile = os.path.join(ifgdir1, ifgd+'.cc')
        if not (os.path.exists(unwfile) and os.path.exists(ccfile)):
            ifgdates2.append(ifgd)
        if sbovl:
            sbovlmmfile = os.path.join(ifgdir1, ifgd+'.sbovldiff.adf.mm')
            sbovlccfile = os.path.join(ifgdir1, ifgd+'.sbovldiff.adf.cc')
            bovlmmfile = os.path.join(ifgdir1, ifgd+'.bovldiff.adf.mm')  # in case only bovl exists.
            bovlccfile = os.path.join(ifgdir1, ifgd+'.bovldiff.adf.cc')
            
            if not ((os.path.exists(sbovlmmfile) and os.path.exists(sbovlccfile)) or (os.path.exists(bovlmmfile) and os.path.exists(bovlccfile))):
                sbovldates.append(ifgd)

    n_ifg2 = len(ifgdates2)
    if sbovl:
        n_sbovl = len(sbovldates)
    
    # Print existing status for unw and cc files
    if not sbovl:
        if n_ifg - n_ifg2 > 0:
            print("  {0:3}/{1:3} unw and cc already exist. Skip".format(n_ifg - n_ifg2, n_ifg), flush=True)
    else:
        # Print existing status for sbovldiff.adf.mm and sbovldiff.adf.cc files
        if n_ifg - n_sbovl > 0:
            print("  {0:3}/{1:3} sbovldiff.adf.mm and sbovldiff.adf.cc already exist. Skip".format(n_ifg - n_sbovl, n_ifg), flush=True)
           
                   
    width = None
    ifgd_ok = []
    sbovl_ok = []
    if sbovl and n_sbovl > 0:
        if n_ifg2 > 0:
            if n_para > n_sbovl:
                n_para = n_sbovl

        # Perform size check
        try:
            tif = glob.glob(os.path.join(geocdir, '*.tif'))[0]
            geotiff = gdal.Open(tif)
            width = geotiff.RasterXSize
            length = geotiff.RasterYSize
            geotiff = None
        except:
            print('no other-than-ifg tif is found')
            width = None

        # Parallel processing for sbovl data
        print('  {} parallel processing for sbovl...'.format(n_para), flush=True)
        p = q.Pool(n_para)
        rc_sbovl = p.starmap(convert_wrapper, [(sbovldates[i], True) for i in range(n_sbovl)])  # Pass sbovldates
        p.close()


        # Parallel processing for `sbovl` data if flag is set
        for i, _rc in enumerate(rc_sbovl):
            if _rc == 1:
                with open(no_unw_list, 'a') as f:
                    print('{}'.format(sbovldates[i]), file=f)
            elif _rc == 0:
                sbovl_ok.append(sbovldates[i])
        
    else:
        if n_ifg2 > 0:
            if n_para > n_ifg2:
                n_para = n_ifg2

            # Perform size check for unw
            try:
                tif = glob.glob(os.path.join(geocdir, '*.tif'))[0]
                geotiff = gdal.Open(tif)
                width = geotiff.RasterXSize
                length = geotiff.RasterYSize
                geotiff = None
            except:
                print('no other-than-ifg tif is found')
                width = None    
        
            # Parallel processing for ifg data
            print('  {} parallel processing for ifg...'.format(n_para), flush=True)
            p = q.Pool(n_para)
            rc_ifg = p.starmap(convert_wrapper, [(ifgdates2[i], False) for i in range(n_ifg2)])  # Pass ifgdates2
            p.close()
        
            # Process results for ifg
            for i, _rc in enumerate(rc_ifg):
                if _rc == 1:
                    with open(no_unw_list, 'a') as f:
                        print('{}'.format(ifgdates2[i]), file=f)
                elif _rc == 0:
                    ifgd_ok.append(ifgdates2[i])
                    
    ### Read info
    ## If all float already exist, this will not be done, but no problem because
    ## par files should alerady exist!
    if ifgd_ok:
        example_date = ifgd_ok[0]
        unw_tiffile = os.path.join(geocdir, example_date, example_date+'.geo.unw.tif')
        geotiff = gdal.Open(unw_tiffile)
        width = geotiff.RasterXSize
        length = geotiff.RasterYSize
        lon_w_p, dlon, _, lat_n_p, _, dlat = geotiff.GetGeoTransform()
        ## lat lon are in pixel registration. dlat is negative
        lon_w_g = lon_w_p + dlon/2
        lat_n_g = lat_n_p + dlat/2
        ## to grit registration by shifting half pixel inside
        if nlook != 1:
            width = int(width/nlook)
            length = int(length/nlook)
            dlon = dlon*nlook
            dlat = dlat*nlook
    elif sbovl_ok:
        example_date = None
        for pair in sbovl_ok:
            unw_tiffile = os.path.join(geocdir, pair, f"{pair}.geo.sbovldiff.adf.mm.tif")
            geotiff = gdal.Open(unw_tiffile)
            if geotiff is not None:
                example_date = date
                width = geotiff.RasterXSize
                length = geotiff.RasterYSize
                lon_w_p, dlon, _, lat_n_p, _, dlat = geotiff.GetGeoTransform()
                lon_w_g = lon_w_p + dlon / 2
                lat_n_g = lat_n_p + dlat / 2

                if nlook != 1:
                    width = int(width / nlook)
                    length = int(length / nlook)
                    dlon *= nlook
                    dlat *= nlook
                break  # Exit loop when a valid file is found
        if example_date is None:
            print("No valid sbovl data found. Exiting.")
            sys.exit(1)
    else:
        print(f"No valid interferogram data found for processing or already processed, please check {outdir} exist or not!", flush=True)
        example_date = ifgdates2[i]
        unw_tiffile = os.path.join(geocdir, example_date, example_date+'.geo.unw.tif')
        geotiff = gdal.Open(unw_tiffile)
        width = geotiff.RasterXSize
        length = geotiff.RasterYSize
        lon_w_p, dlon, _, lat_n_p, _, dlat = geotiff.GetGeoTransform()
        ## lat lon are in pixel registration. dlat is negative
        lon_w_g = lon_w_p + dlon/2
        lat_n_g = lat_n_p + dlat/2
        ## to grit registration by shifting half pixel inside
        if nlook != 1:
            width = int(width/nlook)
            length = int(length/nlook)
            dlon = dlon*nlook
            dlat = dlat*nlook
                    
    # 2021-11-11 fix for case where all is done except of par files..
    if not width:
        tif = glob.glob(os.path.join(geocdir,'*.tif'))[0]
        geotiff = gdal.Open(tif)
        width = geotiff.RasterXSize
        length = geotiff.RasterYSize
        lon_w_p, dlon, _, lat_n_p, _, dlat = geotiff.GetGeoTransform()
        lon_w_g = lon_w_p + dlon/2
        lat_n_g = lat_n_p + dlat/2
        if nlook != 1:
            width = int(width/nlook)
            length = int(length/nlook)
            dlon = dlon*nlook
            dlat = dlat*nlook
    #%% EQA.dem_par, slc.mli.par
    if not os.path.exists(mlipar):
        print('\nCreate slc.mli.par', flush=True)
#        radar_freq = 5.405e9 ## fixed for Sentnel-1
        with open(mlipar, 'w') as f:
            print('range_samples:   {}'.format(width), file=f)
            print('azimuth_lines:   {}'.format(length), file=f)
            print('radar_frequency: {} Hz'.format(radar_freq), file=f)
            if center_time is not None:
                print('center_time: {}'.format(center_time), file=f)

    if not os.path.exists(dempar):
        print('\nCreate EQA.dem_par', flush=True)

        text = ["Gamma DIFF&GEO DEM/MAP parameter file",
              "title: DEM",
              "DEM_projection:     EQA",
              "data_format:        REAL*4",
              "DEM_hgt_offset:          0.00000",
              "DEM_scale:               1.00000",
              "width: {}".format(width),
              "nlines: {}".format(length),
              "corner_lat:     {}  decimal degrees".format(lat_n_g),
              "corner_lon:    {}  decimal degrees".format(lon_w_g),
              "post_lat: {} decimal degrees".format(dlat),
              "post_lon: {} decimal degrees".format(dlon),
              "",
              "ellipsoid_name: WGS 84",
              "ellipsoid_ra:        6378137.000   m",
              "ellipsoid_reciprocal_flattening:  298.2572236",
              "",
              "datum_name: WGS 1984",
              "datum_shift_dx:              0.000   m",
              "datum_shift_dy:              0.000   m",
              "datum_shift_dz:              0.000   m",
              "datum_scale_m:         0.00000e+00",
              "datum_rotation_alpha:  0.00000e+00   arc-sec",
              "datum_rotation_beta:   0.00000e+00   arc-sec",
              "datum_rotation_gamma:  0.00000e+00   arc-sec",
              "datum_country_list: Global Definition, WGS84, World\n"]

        with open(dempar, 'w') as f:
            f.write('\n'.join(text))


    #%% bperp
    print('\nCopy baselines file', flush=True)
    imdates = tools_lib.ifgdates2imdates(ifgdates)
    if os.path.exists(bperp_file_in) and os.path.getsize(bperp_file_in) > 0:
        ## Check exisiting bperp_file
        if not io_lib.read_bperp_file(bperp_file_in, imdates):
            print('  baselines file found, but not complete. Make dummy', flush=True)
            io_lib.make_dummy_bperp(bperp_file_out, imdates)
        else:
            shutil.copyfile(bperp_file_in, bperp_file_out)
    else:
        print('  No valid baselines file exists. Make dummy.', flush=True)
        io_lib.make_dummy_bperp(bperp_file_out, imdates)


    #%% Finish
    elapsed_time = time.time()-start
    hour = int(elapsed_time/3600)
    minite = int(np.mod((elapsed_time/60),60))
    sec = int(np.mod(elapsed_time,60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour,minite,sec))

    print('\n{} Successfully finished!!\n'.format(os.path.basename(argv[0])))
    print('Output directory: {}\n'.format(os.path.relpath(outdir)))


#%%
# Wrapper function with `is_sbovl` parameter
def convert_wrapper(ifgd, is_sbovl=False):
    # if np.mod(ifgd, 10) == 0:
    print(f"  Processing {ifgd}...", flush=True)

    # Initialize suffix and cycle based on type
    if is_sbovl:
        suffix = ['.geo.sbovldiff.adf.mm.tif', '.geo.sbovldiff.adf.cc.tif', '.sbovldiff.adf.mm', '.sbovldiff.adf.cc']
        cycle = 75

        # Check for sbovldiff files first
        unw_tiffile = os.path.join(geocdir, ifgd, ifgd + suffix[0])
        cc_tiffile = os.path.join(geocdir, ifgd, ifgd + suffix[1])

        if not os.path.exists(unw_tiffile) or not os.path.exists(cc_tiffile):
            print(f'  No {ifgd + suffix[0]} or {ifgd + suffix[1]} found. Checking bovldiff files...', flush=True)

            # Fall back to bovldiff if sbovldiff not found
            unw_tiffile = os.path.join(geocdir, ifgd, ifgd + '.geo.bovldiff.adf.mm.tif')
            cc_tiffile = os.path.join(geocdir, ifgd, ifgd + '.geo.bovldiff.adf.cc.tif')

            if not os.path.exists(unw_tiffile) or not os.path.exists(cc_tiffile):
                print(f'  No {ifgd + ".geo.bovldiff.adf.mm.tif"} or {ifgd + ".geo.bovldiff.adf.cc.tif"} found. Skip.', flush=True)
                return 1

    else:
        # Default case for non-sbovl processing
        suffix = ['.geo.unw.tif', '.geo.cc.tif', '.unw', '.cc']
        cycle = 3
        unw_tiffile = os.path.join(geocdir, ifgd, ifgd + suffix[0])
        cc_tiffile = os.path.join(geocdir, ifgd, ifgd + suffix[1])

        if not os.path.exists(unw_tiffile) or not os.path.exists(cc_tiffile):
            print(f'  No {ifgd + suffix[0]} or {ifgd + suffix[1]} found. Skip.', flush=True)
            return 1

    # Output directories and files
    ifgdir1 = os.path.join(outdir, ifgd)
    if not os.path.exists(ifgdir1):
        os.mkdir(ifgdir1)
    unwfile = os.path.join(ifgdir1, ifgd + suffix[2])
    ccfile = os.path.join(ifgdir1, ifgd + suffix[3])

    # Read data from GeoTIFF
    try:
        unw = gdal.Open(unw_tiffile).ReadAsArray()
        unw[unw == 0] = np.nan
    except:
        print(f'  {unw_tiffile} cannot open. Skip.', flush=True)
        shutil.rmtree(ifgdir1)
        return 1

    try:
        cc = gdal.Open(cc_tiffile).ReadAsArray()
        if cc.dtype == np.float32:
            cc = cc * 255  # Convert 0-1 to 0-255 for uint8
    except:
        print(f'  {cc_tiffile} cannot open. Skip.', flush=True)
        shutil.rmtree(ifgdir1)
        return 1

    # Dimension check
    if width:
        if (cc.shape != (length, width)) or (unw.shape != (length, width)):
            print(f'pair {ifgd} has different dimensions. Skipping.', flush=True)
            return 1

    # Multilook processing if needed
    if nlook != 1:
        cc = cc.astype(np.float32)
        cc[cc == 0] = np.nan  # Treat zero coherence as missing data (NaN)

        # Apply weighted multilook to `unw` using coherence as weights
        unw = tools_lib.multilook_weighted(unw, cc, nlook, nlook, n_valid_thre)

        # Apply weighted multilook to `cc`, using itself as the coherence weight
        cc = tools_lib.multilook_weighted(cc, cc, nlook, nlook, n_valid_thre)

    # Save float outputs
    unw.tofile(unwfile)
    cc = np.nan_to_num(cc, nan=0)
    cc = cc.astype(np.uint8)  # Convert NaNs to 0, auto-floor to max 255
    cc.tofile(ccfile)

    # Generate png images
    if plot_cc:
        ccpngfile = os.path.join(ifgdir1, ifgd + suffix[3] + '.png')
        cc = cc.astype(np.float32)
        cc[np.where(np.isnan(unw))] = np.nan
        plot_lib.make_im_png(cc / 255, ccpngfile, cmap_cc, ifgd + suffix[3], vmin=0.03, vmax=1, cbar=True, logscale=True)

    unwpngfile = os.path.join(ifgdir1, ifgd + suffix[2] + '.png')
    plot_lib.make_im_png(np.angle(np.exp(1j * unw / cycle) * cycle), unwpngfile, cmap_wrap, ifgd + suffix[2], vmin=-np.pi, vmax=np.pi, cbar=False)

    return 0

# Run main
if __name__ == "__main__":
    sys.exit(main())
