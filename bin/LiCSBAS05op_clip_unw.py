#!/usr/bin/env python3
"""

This script clips a specified rectangular area of interest from unw and cc data. The clipping can make the data size smaller and processing faster, and improve the result of Step 1-2 (loop closure). Existing files are not re-created to save time, i.e., only the newly available data will be processed. This step is optional.
In case of TS* directory is the input, it will clip the results of step 13 instead.

===============
Input & output files
===============
Inputs in GEOCml*/ :
 - yyyymmdd_yyyymmdd/
   - yyyymmdd_yyyymmdd.unw
   - yyyymmdd_yyyymmdd.cc
 - slc.mli[.par|.png]
 - EQA.dem.par
 - Others (baselines, [E|N|U].geo, hgt[.png])

Outputs in GEOCml*clip/ :
 - yyyymmdd_yyyymmdd/
   - yyyymmdd_yyyymmdd.unw[.png] (clipped)
   - yyyymmdd_yyyymmdd.cc (clipped)
 - slc.mli[.par|.png] (clipped)
 - EQA.dem.par (clipped)
 - Other files in input directory if exist (copy or clipped)
 - cliparea.txt

=====
Usage
=====
LiCSBAS05op_clip_unw.py -i in_dir -o out_dir [-r x1:x2/y1:y2] [-g lon1/lon2/lat1/lat2] [-p polyfile.txt] [--n_para int]

 -i  Path to the GEOCml* dir containing stack of unw data.
 -o  Path to the output dir.
 -r  Range to be clipped. Index starts from 0.
     0 for x2/y2 means all. (i.e., 0:0/0:0 means whole area).
 -g  Range to be clipped in geographical coordinates (deg).
 -p  Text file containing polygon coords to be clipped (x1,y1,x2,y2,x3,y3....), 1 line per clip
     The whole image will be clipped to the extent of the polyclips unless -r or -g is selected
 --n_para  Number of parallel processing (Default: # of usable CPU)

"""
#%% Change log
'''
20241105 Milan Lazecky, Uni of Leeds
 - enabling cutting TS results
v1.2.6 20230804 Jack McGrath, Uni of Leeds
 - Add poly clipping
v1.2.5 20210105 Yu Morishita, GSI
 - Fill 0 by nan in unw
v1.2.4 20201119 Yu Morishita, GSI
 - Change default cmap for wrapped phase from insar to SCM.romaO
v1.2.3 20201118 Yu Morishita, GSI
 - Again Bug fix of multiprocessing
v1.2.2 20201116 Yu Morishita, GSI
 - Bug fix of multiprocessing in Mac python>=3.8
v1.2.1 20201028 Yu Morishita, GSI
 - Update how to get n_para
v1.2 20200909 Yu Morishita, GSI
 - Parallel processing
v1.1 20200302 Yu Morishita, Uni of Leeds and GSI
 - Bag fix for hgt.png and glob
 - Deal with cc file in uint8 format
v1.0 20190730 Yu Morishita, Uni of Leeds and GSI
 - Original implementation
'''

#%% Import
from LiCSBAS_meta import *
import getopt
import os
import re
import sys
import glob
import shutil
import time
import numpy as np
import multiprocessing as multi
import cmcrameri.cm as cmc #SCM
import LiCSBAS_io_lib as io_lib
import LiCSBAS_tools_lib as tools_lib
import LiCSBAS_plot_lib as plot_lib

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

    ### For parallel processing
    global ifgdates2, in_dir, out_dir, length, width, x1, x2, y1, y2, cycle, cmap_wrap, bool_mask


    #%% Set default
    in_dir = []
    out_dir = []
    range_str = []
    range_geo_str = []
    poly_file = []
    try:
        n_para = len(os.sched_getaffinity(0))
    except:
        n_para = multi.cpu_count()

    q = multi.get_context('fork')
    cmap_wrap = cmc.romaO


    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hi:o:r:g:p:", ["help", "n_para="])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                return 0
            elif o == '-i':
                in_dir = a
            elif o == '-o':
                out_dir = a
            elif o == '-r':
                range_str = a
            elif o == '-g':
                range_geo_str = a
            elif o == '-p':
                poly_file = a
            elif o == '--n_para':
                n_para = int(a)

        if not in_dir:
            raise Usage('No input directory given, -i is not optional!')
        if not out_dir:
            raise Usage('No output directory given, -o is not optional!')
        if not range_str and not range_geo_str and not poly_file:
            raise Usage('No clip area given, use either -r, -g or -p!')
        if range_str and range_geo_str:
            raise Usage('Both -r and -g given, use either -r or -g not both!')
        elif not os.path.isdir(in_dir):
            raise Usage('No {} dir exists!'.format(in_dir))
        #elif not os.path.exists(os.path.join(in_dir, 'slc.mli.par')):
        #    raise Usage('No slc.mli.par file exists in {}!'.format(in_dir))

    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2


    #%% Read info and make dir
    in_dir = os.path.abspath(in_dir)
    out_dir = os.path.abspath(out_dir)
    if os.path.exists(os.path.join(in_dir, 'results')):
        tsdirflag = True
        print('the input is TS directory, clipping results and h5 files')
        in_dir_pars = os.path.join(in_dir, 'info')
        out_dir_pars = os.path.join(out_dir, 'info')
        in_dir_res = os.path.join(in_dir, 'results')
        out_dir_res = os.path.join(out_dir, 'results')
        if not os.path.exists(os.path.join(in_dir, 'cum.h5')):
            print('ERROR: No cum.h5 in the TS directory - please clip the GEOCmlX directory instead')
            return 2
    else:
        tsdirflag = False
        in_dir_pars = in_dir
        out_dir_pars = out_dir

    mlipar = os.path.join(in_dir_pars, 'slc.mli.par')
    if not os.path.exists(mlipar):
        print('ERROR: No slc.mli.par file exists in '+in_dir_pars)
        return 2

    width = int(io_lib.get_param_par(mlipar, 'range_samples'))
    length = int(io_lib.get_param_par(mlipar, 'azimuth_lines'))

    speed_of_light = 299792458 #m/s
    radar_frequency = float(io_lib.get_param_par(mlipar, 'radar_frequency')) #Hz
    wavelength = speed_of_light/radar_frequency #meter
    if wavelength > 0.2: ## L-band
        cycle = 1.5  # 2pi/cycle for png
    else: ## C-band
        cycle = 3  # 2pi*3/cycle for png

    dempar = os.path.join(in_dir_pars, 'EQA.dem_par')
    lat1 = float(io_lib.get_param_par(dempar, 'corner_lat')) # north
    lon1 = float(io_lib.get_param_par(dempar, 'corner_lon')) # west
    postlat = float(io_lib.get_param_par(dempar, 'post_lat')) # negative
    postlon = float(io_lib.get_param_par(dempar, 'post_lon')) # positive
    lat2 = lat1+postlat*(length-1) # south
    lon2 = lon1+postlon*(width-1) # east

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    if not os.path.exists(out_dir_pars):
        os.mkdir(out_dir_pars)

    if tsdirflag:
        if not os.path.exists(out_dir_res):
            os.mkdir(out_dir_res)

    if not tsdirflag:
        ifgdates = tools_lib.get_ifgdates(in_dir)
        n_ifg = len(ifgdates)

    #%% Check and set range to be clipped
    ### Read -r or -g option
    if range_str: ## -r
        if not tools_lib.read_range(range_str, width, length):
            print('\nERROR in {}\n'.format(range_str), file=sys.stderr)
            return 1
        else:
            x1, x2, y1, y2 = tools_lib.read_range(range_str, width, length)
    elif range_geo_str: ## -g
        if not tools_lib.read_range_geo(range_geo_str, width, length, lat1, postlat, lon1, postlon):
            print('\nERROR in {}\n'.format(range_geo_str), file=sys.stderr)
            return 1
        else:
            x1, x2, y1, y2 = tools_lib.read_range_geo(range_geo_str, width, length, lat1, postlat, lon1, postlon)
            range_str = '{}:{}/{}:{}'.format(x1, x2, y1, y2)

    bool_mask = np.zeros((length, width), dtype=bool)
    if poly_file: ## -p
        print('Clipping using polygon file: {}'.format(poly_file))
        with open(poly_file) as f:
            poly_strings_all = f.readlines()

        #dempar = os.path.join(in_dir, 'EQA.dem_par')
        #lat1 = float(io_lib.get_param_par(dempar, 'corner_lat')) # north
        #lon1 = float(io_lib.get_param_par(dempar, 'corner_lon')) # west
        #postlat = float(io_lib.get_param_par(dempar, 'post_lat')) # negative
        #postlon = float(io_lib.get_param_par(dempar, 'post_lon')) # positive
        #lat2 = lat1+postlat*(length-1) # south
        #lon2 = lon1+postlon*(width-1) # east
        #lon, lat = np.arange(lon1, lon2+postlon, postlon), np.arange(lat1, lat2+postlat, postlat)
        lon, lat = np.linspace(lon1, lon2, width), np.linspace(lat1, lat2, length)
        for poly_str in poly_strings_all:
            bool_mask = bool_mask + tools_lib.poly_mask(poly_str, lon, lat)
        
        clip_area = np.where(bool_mask)
        bool_mask = bool_mask == False # Invert bool mask, so True are areas to be dropped
        if not range_str and not range_geo_str:
            x1, x2, y1, y2 = min(clip_area[1]), max(clip_area[1]), min(clip_area[0]), max(clip_area[0])
            range_str = '{}:{}/{}:{}'.format(x1, x2, y1, y2)

    ### Calc clipped  info
    width_c = x2-x1
    length_c = y2-y1
    lat1_c = lat1+postlat*y1 # north
    lon1_c = lon1+postlon*x1 # west
    lat2_c = lat1_c+postlat*(length_c-1) # south
    lon2_c = lon1_c+postlon*(width_c-1) # east

    print("\nArea to be clipped:", flush=True)
    print("  0:{}/0:{} -> {}:{}/{}:{}".format(width, length, x1, x2, y1, y2))
    print("  {:.7f}/{:.7f}/{:.7f}/{:.7f} ->".format(lon1, lon2, lat2, lat1))
    print("  {:.7f}/{:.7f}/{:.7f}/{:.7f}".format(lon1_c, lon2_c, lat2_c, lat1_c))
    print("  Width/Length: {}/{} -> {}/{}".format(width, length, width_c, length_c))
    print("", flush=True)

    clipareafile = os.path.join(out_dir_pars, 'cliparea.txt')
    with open(clipareafile, 'w') as f: f.write(range_str)


    #%% Make clipped par files
    mlipar_c = os.path.join(out_dir_pars, 'slc.mli.par')
    dempar_c = os.path.join(out_dir_pars, 'EQA.dem_par')

    ### slc.mli.par
    with open(mlipar, 'r') as f: file = f.read()
    file = re.sub(r'range_samples:\s*{}'.format(width), 'range_samples: {}'.format(width_c), file)
    file = re.sub(r'azimuth_lines:\s*{}'.format(length), 'azimuth_lines: {}'.format(length_c), file)
    with open(mlipar_c, 'w') as f: f.write(file)

    ### EQA.dem_par
    with open(dempar, 'r') as f: file = f.read()
    file = re.sub(r'width:\s*{}'.format(width), 'width: {}'.format(width_c), file)
    file = re.sub(r'nlines:\s*{}'.format(length), 'nlines: {}'.format(length_c), file)
    file = re.sub(r'corner_lat:\s*{}'.format(lat1), 'corner_lat: {}'.format(lat1_c), file)
    file = re.sub(r'corner_lon:\s*{}'.format(lon1), 'corner_lon: {}'.format(lon1_c), file)
    with open(dempar_c, 'w') as f: f.write(file)

    if tsdirflag:
        # clip only results and h5 files to the new directory, copy 'info'
        print('Warning, resetting ref point to contain whole area aka mean (cum data are corrected but not step 12)')
        # results dir:
        files = sorted(glob.glob(os.path.join(in_dir_res, '*')))
        for file in files:
            if os.path.isdir(file):
                continue  #not copy directory
            elif os.path.getsize(file) == width*length*4: ##float file
                print('Clip {}'.format(os.path.basename(file)), flush=True)
                data = io_lib.read_img(file, length, width)
                data = data[y1:y2, x1:x2]
                filename = os.path.basename(file)
                outfile = os.path.join(out_dir_res, filename)
                data.tofile(outfile)
        # info dir:
        txtfiles = sorted(glob.glob(os.path.join(in_dir_pars, '*.txt')))
        for file in txtfiles:
            filename = os.path.basename(file)
            if filename[0] == '1':
                if int(filename[:2])<16:
                    if not os.path.exists(os.path.join(out_dir_pars, filename)):
                        shutil.copy(file, out_dir_pars)
        # setting the full ref area
        refstr = '0:'+str(width_c)+'/0:'+str(length_c)
        refnm = '13ref.txt'
        #reffiles = sorted(glob.glob(os.path.join(in_dir_pars, '*ref.txt')))
        #for reffile in reffiles:
        #    refnm = os.path.basename(reffile)
        refsfile = os.path.join(out_dir_pars, refnm)
        with open(refsfile, 'w') as f:
            print(refstr, file=f)
        # finally cum[_filt].h5
        import xarray as xr # TODO - add xarray to requirements and push this up
        a = os.path.join(in_dir, 'cum.h5')
        a = xr.open_dataset(a)
        dtype = a.refarea.values.dtype  # .replace('159','333')
        a['refarea'].values = np.array(refstr, dtype=dtype)
        # now.. it is weird but phony_dim_X differs in meaning! -- very fast ugly workaround (only assuming position 0 or 2+ for time):
        dim_l, dim_w = a.coh_avg.dims
        for dimc in a.cum.dims:
            if dimc not in [dim_l, dim_w]:
                dim_t = dimc
        if dim_t == 'phony_dim_0':
            b = a.sel(phony_dim_1=slice(y1, y2), phony_dim_2=slice(x1, x2))
            b['cum'].values = b['cum'].values - b['cum'].mean(dim=['phony_dim_1', 'phony_dim_2']).values[:, np.newaxis,
                                            np.newaxis]
        else:
            b = a.sel(phony_dim_0=slice(y1, y2), phony_dim_1=slice(x1, x2))
            b['cum'].values = b['cum'].values - b['cum'].mean(dim=['phony_dim_0', 'phony_dim_1']).values[:, np.newaxis,
                                            np.newaxis]
        b.vel.values = b.vel.values - b.vel.mean().values
        b.to_netcdf(out_dir+'/cum.h5')
        # np.array('159:160/254:255', dtype=dtype)
        # forgotten 13params file:
        inparmfile = os.path.join(in_dir_pars, '13parameters.txt')
        with open(os.path.join(out_dir_pars, '13parameters.txt'), "w") as f:
            print('range_samples:  {}'.format(width_c), file=f)
            print('azimuth_lines:  {}'.format(length_c), file=f)
            print('wavelength:     {}'.format(wavelength), file=f)
            for keyw in ['n_im_all', 'n_im', 'n_ifg_all', 'n_ifg', 'n_ifg_bad']:
                gg = int(io_lib.get_param_par(inparmfile, keyw))
                print(keyw+':     {}'.format(gg), file=f)
            n_unw_thre = float(io_lib.get_param_par(inparmfile, 'n_unw_thre'))
            print('n_unw_thre:     {}'.format(n_unw_thre), file=f)
            print('ref_area:       {}'.format(refstr), file=f)
            memory_size = io_lib.get_param_par(inparmfile, 'memory_size')
            print('memory_size:    {} MB'.format(memory_size), file=f)
            n_patch = int(io_lib.get_param_par(inparmfile, 'n_patch'))
            print('n_patch:        {}'.format(n_patch), file=f)
            inv_alg = io_lib.get_param_par(inparmfile, 'inv_alg')
            print('inv_alg:        {}'.format(inv_alg), file=f)
            gamma = float(io_lib.get_param_par(inparmfile, 'gamma'))
            print('gamma:          {}'.format(gamma), file=f)
            pixsp_r = float(io_lib.get_param_par(inparmfile, 'pixel_spacing_r'))
            print('pixel_spacing_r: {:.2f} m'.format(pixsp_r), file=f)
            pixsp_a = float(io_lib.get_param_par(inparmfile, 'pixel_spacing_a'))
            print('pixel_spacing_a: {:.2f} m'.format(pixsp_a), file=f)
    else:
        #%% Clip or copy other files than unw and cc
        files = sorted(glob.glob(os.path.join(in_dir, '*')))
        for file in files:
            if os.path.isdir(file):
                continue  #not copy directory
            elif file==mlipar or file==dempar:
                continue  #not copy
            elif os.path.getsize(file) == width*length*4: ##float file
                print('Clip {}'.format(os.path.basename(file)), flush=True)
                data = io_lib.read_img(file, length, width)
                data = data[y1:y2, x1:x2]
                filename = os.path.basename(file)
                outfile = os.path.join(out_dir, filename)
                data.tofile(outfile)
            elif file==os.path.join(in_dir, 'slc.mli.png'):
                print('Recreate slc.mli.png', flush=True)
                mli = io_lib.read_img(os.path.join(out_dir, 'slc.mli'), length_c, width_c)
                pngfile = os.path.join(out_dir, 'slc.mli.png')
                plot_lib.make_im_png(mli, pngfile, 'gray', 'MLI', cbar=False)
            elif file==os.path.join(in_dir, 'hgt.png'):
                print('Recreate hgt.png', flush=True)
                hgt = io_lib.read_img(os.path.join(out_dir, 'hgt'), length_c, width_c)
                vmax = np.nanpercentile(hgt, 99)
                vmin = -vmax/3 ## bnecause 1/4 of terrain is blue
                pngfile = os.path.join(out_dir, 'hgt.png')
                plot_lib.make_im_png(hgt, pngfile, 'terrain', 'DEM (m)', vmin, vmax, cbar=True)
            else:
                print('Copy {}'.format(os.path.basename(file)), flush=True)
                shutil.copy(file, out_dir)


        #%% Clip unw and cc
        print('\nClip unw and cc', flush=True)
        ### First, check if already exist
        ifgdates2 = []
        for ifgix, ifgd in enumerate(ifgdates):
            out_dir1 = os.path.join(out_dir, ifgd)
            unwfile_c = os.path.join(out_dir1, ifgd+'.unw')
            ccfile_c = os.path.join(out_dir1, ifgd+'.cc')
            compfile_c = os.path.join(out_dir1, ifgd+'.conncomp')
            if not (os.path.exists(unwfile_c) and os.path.exists(ccfile_c)):
                ifgdates2.append(ifgd)

        n_ifg2 = len(ifgdates2)
        if n_ifg-n_ifg2 > 0:
            print("  {0:3}/{1:3} clipped unw and cc already exist. Skip".format(n_ifg-n_ifg2, n_ifg), flush=True)

        if n_ifg2 > 0:
            ### Clip with parallel processing
            if n_para > n_ifg2:
                n_para = n_ifg2

            print('  {} parallel processing...'.format(n_para), flush=True)
            p = q.Pool(n_para)
            p.map(clip_wrapper, range(n_ifg2))
            p.close()


    #%% Finish
    elapsed_time = time.time()-start
    hour = int(elapsed_time/3600)
    minite = int(np.mod((elapsed_time/60),60))
    sec = int(np.mod(elapsed_time,60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour,minite,sec))

    print('\n{} Successfully finished!!\n'.format(os.path.basename(argv[0])))
    print('Output directory: {}\n'.format(os.path.relpath(out_dir)))


#%%
def clip_wrapper(ifgix):
    if np.mod(ifgix, 100) == 0:
        print("  {0:3}/{1:3}th unw...".format(ifgix, len(ifgdates2)), flush=True)

    ifgd = ifgdates2[ifgix]
    unwfile = os.path.join(in_dir, ifgd, ifgd+'.unw')
    ccfile = os.path.join(in_dir, ifgd, ifgd+'.cc')
    compfile = os.path.join(in_dir, ifgd, ifgd + '.conncomp')

    unw = io_lib.read_img(unwfile, length, width)
    unw[unw==0] = np.nan
    if os.path.getsize(ccfile) == length*width:
        ccformat = np.uint8
    elif os.path.getsize(ccfile) == length*width*4:
        ccformat = np.float32
    else:
        print("ERROR: unkown file format for {}".format(ccfile), file=sys.stderr)
        return
    coh = io_lib.read_img(ccfile, length, width, dtype=ccformat)

    ### Clip
    unw[bool_mask] = 0 # np.nan
    coh[bool_mask] = 0 # Can't convert int coh to nan
    
    unw = unw[y1:y2, x1:x2]
    coh = coh[y1:y2, x1:x2]

    ### Output
    out_dir1 = os.path.join(out_dir, ifgd)
    if not os.path.exists(out_dir1): os.mkdir(out_dir1)

    unw.tofile(os.path.join(out_dir1, ifgd+'.unw'))
    coh.tofile(os.path.join(out_dir1, ifgd+'.cc'))

    if os.path.exists(compfile):
        comp = io_lib.read_img(compfile, length, width, dtype=ccformat)
        comp[bool_mask] = 0 #np.nan
        comp = comp[y1:y2, x1:x2]
        comp.tofile(os.path.join(out_dir1, ifgd + '.conncomp'))

    ## Output png for corrected unw
    pngfile = os.path.join(out_dir1, ifgd+'.unw.png')
    title = '{} ({}pi/cycle)'.format(ifgd, cycle*2)
    plot_lib.make_im_png(np.angle(np.exp(1j*unw/cycle)*cycle), pngfile, cmap_wrap, title, -np.pi, np.pi, cbar=False)


#%% main
if __name__ == "__main__":
    sys.exit(main())
