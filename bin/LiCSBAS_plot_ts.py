#!/usr/bin/env python3
"""
========
Overview
========
This script displays the velocity, cumulative displacement, and noise indices,
and plots the time series of displacement. You can interactively change the
displayed image/area and select a point for the time series plot. The reference
area can also be changed by right dragging.

===============
Inputs
===============
 - cum_filt.h5 and/or cum.h5
[- mask, coh_avg, n_unw, vstd, n_gap, n_ifg_noloop, n_loop_err, resid_rms,
   maxTlen, stc, scl.mli, hgt in results dir]

=====
Usage
=====
LiCSBAS_plot_ts.py [-i cum[_filt].h5] [--i2 cum*.h5] [-m yyyymmdd] [-d results_dir]
    [-u U.geo] [-r x1:x2/y1:y2] [--ref_geo lon1/lon2/lat1/lat2] [-p x/y]
    [--p_geo lon/lat] [-c cmap] [--nomask] [--vmin float] [--vmax float]
    [--auto_crange float] [--dmin float] [--dmax float] [--ylen float]
    [--ts_png pngfile] [--dem_background]

 -i    Input cum hdf5 file (Default: ./cum_filt.h5 or ./cum.h5)
 --i2  Input 2nd cum hdf5 file
       (Default: cum.h5 if -i cum_filt.h5, otherwise none)
 -m    Refereference (master) date for time series (Default: first date)
 -d    Directory containing noise indices (e.g., mask, coh_avg, etc.)
       (Default: "results" at the same dir as cum[_filt].h5)
 -u    Input U.geo file to show incidence angle (Default: ../GEOCml*/U.geo)
 -r    Initial reference area (Default: same as info/*ref.txt)
       0 for x2/y2 means all. (i.e., 0:0/0:0 means whole area).
 --ref_geo   Initial reference area in geographical coordinates.
 -p    Initial selected point for time series plot (Default: ref point)
 --p_geo     Initial selected point in geographical coordinates.
 -c    Color map for velocity and cumulative displacement.
       See help of LiCSBAS_disp_img.py.
       (Default: SCM.roma_r, reverse of SCM.roma)
 --nomask     Not use mask (Default: use mask)
 --vmin|vmax  Min|max values of color for velocity map (Default: auto)
 --dmin|dmax  Min|max values of color for cumulative displacement map
              (Default: auto)
 --auto_crange  Percentage of color range used for automatic determination
              (Default: 99 %)
 --ylen       Y Length of time series plot in mm (Default: auto)
 --ts_png     Output png file of time series plot (not display interactive viewers)
 --corrections Show corrections (tide, iono, gacos, etc.) if exist in cum file in another subplot of time series plot
 --cum_name, cum_name2, cum_name3  Dataset name in cum hdf5 file for cumulative displacement to show in time series plot (Default: cum or cum_model). If --corrections is specified, you can specify the dataset name for the corrections to show. For example, if you have tide correction data in your cum hdf5 file, you can specify --cum_name2 tide to show the time series of tide correction. You can specify up to 3 datasets with these options. The labels of the time series plot will be set to the dataset names.
 --dem_background  Uses project hgt file to plot a hillshade background. Uses earthpy and rasterio.

 ##TODO here is testing for absolute referencign and plotting, so please contact developers if you want to use or modify these options #MN
 --abs       Show absolute cumulative displacement and velocity if exist in cum file. If not exist, show cum and vel but set title and color range based on absolute values. This is for the scenario like sbovl where the cumulative displacement and velocity are already corrected for plate motion and show the absolute values. In this scenario, the relative cumulative displacement and velocity (i.e., not corrected for plate motion) can be shown by specifying the cum file with relative values with --i2 option.
 --no_velocity  Not show velocity in title and not use velocity for color range setting
  
example:  LiCSBAS_plot_ts.py -i TS_GEOCml10GACOSmask/cum_filt_interpolate.h5 --cum_name cum --cum_name2 cum_corr_minus_plate --cum_name3 cum_corr_minus_plate_inter
"""
#%% Change log
'''
20260410 Pedro Espin Bedon, UoL (+ML)
 - added --dem_background and fix for updated matplotlib
20260211 Muhammet Nergizci, COMET University of Leeds
 - adding the show corrections option to show the corrections in the time series plot, and cum_name options to specify the dataset name for the cumulative displacement and corrections to show in the time series plot
v1.13.4 20210910 Yu Morishita, GSI
 - Avoid error for refarea in bytes
v1.13.3 20210205 Yu Morishita, GSI
 - More cmap available
v1.13.2 20210126 Yu Morishita, GSI
 - Small bug fix in -r and noise indices
 - Change initial point to center of ref area
v1.13.1 20201016 Yu Morishita, GSI
 - Use log10 to display mli
v1.13 20200902 Yu Morishita, GSI
 - Use nearest interpolation to avoid expanded nan
v1.12 20200827 Yu Morishita, GSI
 - Bug fix for new matplotlib (>=3.3); shift epoch and use datetime instead of ordinal
   (https://matplotlib.org/3.3.1/api/dates_api.html)
v1.11 20200707 Yu Morishita, GSI
 - Add --ts_png option
v1.10 20200703 Yu Morishita, GSI
 - Add --ref_geo and --p_geo options
v1.9 20200527 Yu Morishita, GSI
 - Add -u option to show incidence angle
v1.8 20200408 Yu Morishita, GSI
 - Avoid garbled characters in ja_JP environment
v1.7 20200227 Yu Morishita, Uni of Leeds and GSI
 - Use SCM instead of SCM5
 - Change option from --cmap to -c
 - Add initial point selection option for time series plot
 - Read hgt_linear flag
v1.6 20200210 Yu Morishita, Uni of Leeds and GSI
 - Adjust figure size and ax location
v1.5 20200203 Yu Morishita, Uni of Leeds and GSI
 - Immediate update of image and ts plot when change ref or mask
v1.4 20191213 Yu Morishita, Uni of Leeds and GSI
 - Bag fix for deramp_flag
v1.3 20191120 Yu Morishita, Uni of Leeds and GSI
 - Add mark of selected point and set aspect in image window
 - Display values and unit of noise indices in time seires window
v1.2 20191115 Yu Morishita, Uni of Leeds and GSI
 - Add hgt
v1.1 20190815 Yu Morishita, Uni of Leeds and GSI
 - Add -r option
 - Not use i2 if not exist
 - Bug fix about lines2
v1.0 20190730 Yu Morishita, Uni of Leeds and GSI
 - Created, originating from GIAnT
'''

#%% Import
import getopt
import sys
import os
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.backend_bases
import numpy as np
from matplotlib.widgets import Slider, RadioButtons, RectangleSelector, CheckButtons
import h5py as h5
import datetime as dt
import statsmodels.api as sm
import cmcrameri.cm as cmc
import warnings
import LiCSBAS_io_lib as io_lib
import LiCSBAS_tools_lib as tools_lib
import subprocess

os.environ['LANG'] = 'en_US.UTF-8'

try:
    from pandas.plotting import register_matplotlib_converters
    register_matplotlib_converters()
except:
    pass

class Usage(Exception):
    """Usage context manager"""
    def __init__(self, msg):
        self.msg = msg

#%% Calc model
def calc_model(dph, imdates_ordinal, xvalues, model):

    imdates_years = imdates_ordinal/365.25 ## dont care abs
    xvalues_years = xvalues/365.25

    #models = ['Linear', 'Annual+L', 'Quad', 'Annual+Q']
    A = sm.add_constant(imdates_years) #[1, t]
    An = sm.add_constant(xvalues_years) #[1, t]
    if model == 0: # Linear
        pass
    if model == 1: # Annual+L
        sin = np.sin(2*np.pi*imdates_years)
        cos = np.cos(2*np.pi*imdates_years)
        A = np.concatenate((A, sin[:, np.newaxis], cos[:, np.newaxis]), axis=1)
        sin = np.sin(2*np.pi*xvalues_years)
        cos = np.cos(2*np.pi*xvalues_years)
        An = np.concatenate((An, sin[:, np.newaxis], cos[:, np.newaxis]), axis=1)
    if model == 2: # Quad
        A = np.concatenate((A, (imdates_years**2)[:, np.newaxis]), axis=1)
        An = np.concatenate((An, (xvalues_years**2)[:, np.newaxis]), axis=1)
    if model == 3: # Annual+Q
        sin = np.sin(2*np.pi*imdates_years)
        cos = np.cos(2*np.pi*imdates_years)
        A = np.concatenate((A, (imdates_years**2)[:, np.newaxis],
                            sin[:, np.newaxis], cos[:, np.newaxis]), axis=1)
        sin = np.sin(2*np.pi*xvalues_years)
        cos = np.cos(2*np.pi*xvalues_years)
        An = np.concatenate((An, (xvalues_years**2)[:, np.newaxis],
                             sin[:, np.newaxis], cos[:, np.newaxis]), axis=1)

    result = sm.OLS(dph, A, missing='drop').fit()
    yvalues = result.predict(An)

    return yvalues


def create_hgt_tif(resultsdir: str):
    """
    Creates hgt tif if does not exist

    Args:
        resultsdir (str): The base directory for the results.

    Returns:
        str: The stdef run_licsbass_script(resultsdir: str):
    """
    out_path = f"{resultsdir}/results/hgt.geo.tif"
    if not os.path.isfile(out_path):
        print('creating '+out_path)
        # Construct the input and parameter file paths
        input_path = f"{resultsdir}/results/hgt"
        parameter_file = f"{resultsdir}/info/EQA.dem_par"
        # Define the command
        command = [
            "LiCSBAS_flt2geotiff.py",  # The script to execute
            "-i", input_path,  # Input path
            "-p", parameter_file  # Parameter file path
        ]
        try:
            # Run the command
            result = subprocess.run(command, check=True, text=True, capture_output=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            # Raise an error if the script fails
            raise RuntimeError(f"Script execution failed: {e.stderr}") from e


#%% Main
## Not use def main to use global valuables
if __name__ == "__main__":
    argv = sys.argv

    ver="1.13.4"; date=20210910; author="Y. Morishita"
    print("\n{} ver{} {} {}".format(os.path.basename(argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(argv[0]), ' '.join(argv[1:])), flush=True)

    #%% Set default
    cumfile = []
    cumfile2 = []
    resultsdir = []
    LOSufile = []
    mdate = []
    refarea = []
    refarea_geo = []
    point = []
    point_geo = []
    maskflag = True
    dmin = None
    dmax = None
    ylen = []
    ts_pngfile = []
    vmin = None
    vmax = None
    cmap_name = "cmc.roma_r"
    auto_crange = 99.0
    correction_flag = False
    cum_name = None
    cum_name2 = None
    cum_name3 = None
    
    #TODO here is testing for absolute referencign and plotting, so please contact developers if you want to use or modify these options #MN
    absolute= False
    novel_flag = False
    tsstd = None

    dem_background = False
    ##--cum_name2 cum_corr_minus_plate --cum_name3 cum_corr_minus_plate_inter
    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hi:d:u:m:r:p:c:",
               ["help", "i2=", "ref_geo=", "p_geo=", "nomask", "dmin=", "dmax=",
                "vmin=", "vmax=", "auto_crange=", "ylen=", "ts_png=", "abs", "corrections", "cum_name=",
                "cum_name2=", "cum_name3=", "no_velocity", "dem_background"])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                sys.exit(0)
            elif o == '-i':
                cumfile = a
            elif o == '--i2':
                cumfile2 = a
            elif o == '-m':
                mdate = a
            elif o == '-d':
                resultsdir = a
            elif o == '-u':
                LOSufile = a
            elif o == '-r':
                refarea = a
            elif o == '--ref_geo':
                refarea_geo = a
            elif o == '-p':
                point = a
            elif o == '--p_geo':
                point_geo = a
            elif o == '-c':
                cmap_name = a
            elif o == '--nomask':
                maskflag = False
            elif o == '--dem_background':
                dem_background = True
            elif o == '--vmin':
                vmin = float(a)
            elif o == '--vmax':
                vmax = float(a)
            elif o == '--dmin':
                dmin = float(a)
            elif o == '--dmax':
                dmax = float(a)
            elif o == '--auto_crange':
                auto_crange = float(a)
            elif o == '--ylen':
                ylen = float(a)
            elif o == '--ts_png':
                ts_pngfile = a
            elif o == '--abs':
                absolute = True
            elif o == '--corrections':
                correction_flag = True
            elif o == '--no_velocity':
                novel_flag = True
            elif o == '--cum_name':
                cum_name = a
            elif o == '--cum_name2':
                cum_name2 = a
            elif o == '--cum_name3':
                cum_name3 = a

    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        sys.exit(2)


    #%% Set cmap
    cmap = tools_lib.get_cmap(cmap_name)

    
    #%% Set files
    ### cumfile
    if not cumfile: ## if not given
        if os.path.exists('cum_filt.h5'):
            cumfile = 'cum_filt.h5'
        elif os.path.exists('cum.h5'):
            cumfile = 'cum.h5'
        else:
            print('\nNo cum_filt.h5/cum.h5 found!', file=sys.stderr)
            print('Use -i option or change directory.')
            sys.exit(2)
    else: ##if given
        if not os.path.exists(cumfile):
            print('\nNo {} found!'.format(cumfile), file=sys.stderr)
            sys.exit(2)

    cumdir = os.path.dirname(os.path.abspath(cumfile))
    # checks
    if dem_background:
        try:
            import earthpy.spatial as es
            import rasterio as rio
        except:
            print('earthpy or rasterio not installed - disabling DEM background')
            dem_background = False
        try:
            out = create_hgt_tif(cumdir)
        except RuntimeError as e:
            print(e)
            dem_background = False

    ### cumfile2
    if not cumfile2 and os.path.basename(cumfile) == 'cum_filt.h5' and os.path.exists(os.path.join(cumdir, 'cum.h5')):
        cumfile2 = os.path.join(cumdir, 'cum.h5')

    if cumfile2 and not os.path.exists(cumfile2):
        print('\nNo {} found. Not use.'.format(cumfile2))
        cumfile2 = []

    ### results dir
    if not resultsdir: # if not given
        resultsdir = os.path.join(cumdir, 'results')

    ### mask
    maskfile = os.path.join(resultsdir, 'mask')
    if not os.path.exists(maskfile):
        print('\nNo mask file found. Not use.')
        maskflag = False
        maskfile = []

    ### Noise indecis
    coh_avgfile = os.path.join(resultsdir, 'coh_avg')
    n_unwfile = os.path.join(resultsdir, 'n_unw')
    vstdfile = os.path.join(resultsdir, 'vstd')
    n_gapfile = os.path.join(resultsdir, 'n_gap')
    n_ifg_noloopfile = os.path.join(resultsdir, 'n_ifg_noloop')
    n_loop_errfile = os.path.join(resultsdir, 'n_loop_err')
    residfile = os.path.join(resultsdir, 'resid_rms')
    maxTlenfile = os.path.join(resultsdir, 'maxTlen')
    stcfile = os.path.join(resultsdir, 'stc')
    mlifile = os.path.join(resultsdir, 'slc.mli')
    hgtfile = os.path.join(resultsdir, 'hgt')


    ### U.geo
    if not LOSufile: #if not given
        LOSufile = os.path.join(os.path.dirname(cumdir),
           os.path.basename(cumdir).replace('TS_', ''), 'U.geo') ## Default
    if not os.path.exists(LOSufile):
        print('\nNo U.geo file found. Not use.')
        LOSuflag = False
    else:
        LOSuflag = True

    
    #%% Read data
    ### cumfile
    print('\nReading {}'.format(os.path.relpath(cumfile)))
    cumh5 = h5.File(cumfile,'r')
    vel = cumh5['vel']
    try:
        if cum_name is not None:
            cum = cumh5[cum_name]
            print(f'{cum_name} found in {cumfile}.')
        else:
            cum = cumh5['cum']
            print('loading model cum data')
    except:
        cum = cumh5['cum_model']
        print('loading model cum data')
    
    n_im, length, width = cum.shape

    try:
        gap = cumh5['gap']
        label_gap = 'Gap of ifg network'
    except:
        gap = []
        print('No gap field found in {}. Skip.'.format(cumfile))

    if 'tsstd' in cumh5:
        tsstd = cumh5['tsstd']
        print('Found std estimates - adding to plot')

    try:
        geocod_flag = True
        lat1 = float(cumh5['corner_lat'][()])
        lon1 = float(cumh5['corner_lon'][()])
        dlat = float(cumh5['post_lat'][()])
        dlon = float(cumh5['post_lon'][()])
        aspect = np.abs(dlat/dlon/np.cos(np.deg2rad(lat1+dlat*length/2)))
    except:
        geocod_flag = False
        aspect = 1
        print('No latlon field found in {}. Skip.'.format(cumfile))
    
    
    ### Add the corrections
    if correction_flag:
        # tide correction
        try:
            tide = cumh5['tide'][:]
            label_tide = 'SET correction'
            print('Tide correction found.')
        except KeyError:
            tide = None
            print('No tide correction found in {}. Skip.'.format(cumfile))

        # iono correction
        try:
            iono = cumh5['iono'][:]
            label_iono = 'Iono correction'
            print('Ionospheric correction found.')
        except KeyError:
            iono = None
            print('No iono correction found in {}. Skip.'.format(cumfile))
        
        # gacos correction
        # 
        try:
            gacos = cumh5['sltd'][:] #'gacos'
            label_gacos = 'Gacos correction'
            print('Gacos correction found.')
        except KeyError:
            try:
                gacos = cumh5['external_data'][:]
                label_gacos = 'Gacos correction'
                print('External data used as Gacos correction.')
            except KeyError:
                gacos = None
                print(f'No gacos correction found in {cumfile}. Skip.')
            
  
        # iono correction 2 (if exists) low ress CODE GIM    
        try:
            if 'geo.iono.code.sTECA.tif' in cumh5:
                iono2 = cumh5['geo.iono.code.sTECA.tif'][:]
                label_iono2 = 'Iono2 correction (sTECA)'
                print('Second Ionospheric correction (sTECA) found.')
                # breakpoint()
            elif 'geo.iono.code.tif' in cumh5:
                iono2 = cumh5['geo.iono.code.tif'][:]
                label_iono2 = 'Iono2 correction (CODE)'
                print('Second Ionospheric correction (CODE) found.')
            else:
                iono2 = None
                print(f'No iono2 correction found in {cumfile}. Skip.')
        except Exception as e:
            iono2 = None
            print(f'Error checking iono2 in {cumfile}: {e}')   
            
    if absolute:
        cum_abs = cum_name
        vel = None
        # Check for absolute displacement
        if cum_name is not None:
            if 'cum_abs' in cumh5:
                cum_abs = cumh5['cum_abs'][()]
                print('Absolute displacement (cum_abs) found.')
            else:
                cum_abs = cumh5['cum'][()]
                print('No absolute displacement (cum_abs) found in {}. cum setted.'.format(cumfile))
        else:
            cum_abs = cumh5[cum_name][()]
        # Check for absolute velocity
        if 'vel_abs' in cumh5:
            vel = cumh5['vel_abs']
            print('Absolute velocity (vel_abs) found.')
        else:
            vel = cumh5['vel']
            print('No absolute velocity found in {}. vel setted.'.format(cumfile))        
   
    ### Set initial ref area
    if refarea:
        if not tools_lib.read_range(refarea, width, length):
            print('\nERROR in {}\n'.format(refarea), file=sys.stderr)
            sys.exit(2)
        else:
            refx1, refx2, refy1, refy2 = tools_lib.read_range(refarea, width, length)
    elif refarea_geo and geocod_flag:
        if not tools_lib.read_range_geo(refarea_geo, width, length, lat1, dlat, lon1, dlon):
            print('\nERROR in {}\n'.format(refarea_geo), file=sys.stderr)
            sys.exit(2)
        else:
            refx1, refx2, refy1, refy2 = tools_lib.read_range_geo(refarea_geo, width, length, lat1, dlat, lon1, dlon)
    else:
        refarea = cumh5['refarea'][()]
        if type(refarea) is bytes:
            refarea = refarea.decode('utf-8')
        refx1, refx2, refy1, refy2 = [int(s) for s in re.split('[:/]', refarea)]

    print(refarea)
    refx1h = refx1-0.5; refx2h = refx2-0.5 ## Shift half for plot
    refy1h = refy1-0.5; refy2h = refy2-0.5

    ### Set initial point
    if point:
        if not tools_lib.read_point(point, width, length):
            print('\nERROR in {}\n'.format(point), file=sys.stderr)
            sys.exit(2)
        else:
            point_x, point_y = tools_lib.read_point(point, width, length)
    elif point_geo and geocod_flag:
        point_lon, point_lat = [float(s) for s in re.split('[/]', point_geo)]
        if not tools_lib.bl2xy(point_lon, point_lat, width, length, lat1, dlat, lon1, dlon):
            print('\nERROR in {}\n'.format(point), file=sys.stderr)
            sys.exit(2)
        else:
            point_x, point_y = tools_lib.bl2xy(point_lon, point_lat, width, length, lat1, dlat, lon1, dlon)
    else:
        point_x = int((refx2+refx1)/2)
        point_y = int((refy2+refy1)/2)


    ### Filter info
    if 'deramp_flag' in list(cumh5.keys()):
        deramp_flag = cumh5['deramp_flag'][()]
        if len(deramp_flag) == 0: # no deramp
            deramp = ''
        else:
            deramp = ', drmp={}'.format(deramp_flag)

        if 'hgt_linear_flag' in list(cumh5.keys()):
            if cumh5['hgt_linear_flag'][()] == 1:
                deramp = deramp+', hgt-linear'

        filtwidth_km = float(cumh5['filtwidth_km'][()])
        filtwidth_yr = float(cumh5['filtwidth_yr'][()])
        filtwidth_day = int(np.round(filtwidth_yr*365.25))
        label1 = '1: s={:.1f}km, t={:.2f}yr ({}d){}'.format(filtwidth_km, filtwidth_yr, filtwidth_day, deramp)
    else:
        label1 = '1: No filter'


    ### Set master (reference) date
    imdates = cumh5['imdates'][()].astype(str).tolist()
    if not mdate: ## Not specified or no mdate found in imdates
        ix_m = 0
    elif not mdate in imdates:
        print('No {} found in dates. Set reference to {}'.format(mdate, imdates[0]))
        ix_m = 0
    else:
        print('Reference date set to {}'.format(mdate))
        ix_m = imdates.index(mdate)

    cum_ref = cum[ix_m, :, :]
    if correction_flag:
        if tide is not None:
            tide_ref = tide[ix_m, :, :]
        if iono is not None:
            iono_ref = iono[ix_m, :, :]
        if gacos is not None:
            gacos_ref = gacos[ix_m, :, :]
        if iono2 is not None:
            iono2_ref = iono2[ix_m, :, :]
        
    if absolute:
        if cum_abs is not None:
            cum_abs_ref = cum_abs[ix_m, :, :]
            
    ### cumfile2
    if cumfile2:
        if absolute:  #sbovl scenario for InSAR LoS plotting
            print('Reading {} as 2nd'.format(os.path.relpath(cumfile2)))
            cumh52 = h5.File(cumfile2,'r')
            if  'cum_abs' in cumh52:
                cum2 = cumh52['cum_abs'][()]
                vel2 = cumh52['vel_abs'][()]
                print('Absolute displacement (cum_abs) found.')
            else:
                cum2 = None
                vel2 = None
                print('No absolute displacement (cum_abs) found in {}. Skip.'.format(cumfile))
            
            cum2_ref = cum2[ix_m, :, :]

            if 'deramp_flag' in list(cumh52.keys()):
                deramp_flag2 = cumh52['deramp_flag'][()]
                if len(deramp_flag2) == 0: # no deramp
                    deramp2 = ''
                else:
                    deramp2 = ', drmp={}'.format(deramp_flag2)
                filtwidth_km2 = float(cumh52['filtwidth_km'][()])
                filtwidth_yr2 = float(cumh52['filtwidth_yr'][()])
                filtwidth_day2 = int(np.round(filtwidth_yr2*365.25))
                label2 = '2: s={:.1f}km, t={:.2f}yr ({}d){}'.format(filtwidth_km2, filtwidth_yr2, filtwidth_day2, deramp2)
            else:
                label2 = '2: No filter'
                
        else: ###Normal scenerio for InSAR LoS plotting
            print('Reading {} as 2nd'.format(os.path.relpath(cumfile2)))
            cumh52 = h5.File(cumfile2,'r')

            try:
                cum2 = cumh52['cum']
            except:
                cum2 = cumh52['cum_model']
                print('loading model cum data')

            cum2_ref = cum2[ix_m, :, :]
            vel2 = cumh52['vel']

            if 'deramp_flag' in list(cumh52.keys()):
                deramp_flag2 = cumh52['deramp_flag'][()]
                if len(deramp_flag2) == 0: # no deramp
                    deramp2 = ''
                else:
                    deramp2 = ', drmp={}'.format(deramp_flag2)
                filtwidth_km2 = float(cumh52['filtwidth_km'][()])
                filtwidth_yr2 = float(cumh52['filtwidth_yr'][()])
                filtwidth_day2 = int(np.round(filtwidth_yr2*365.25))
                label2 = '2: s={:.1f}km, t={:.2f}yr ({}d){}'.format(filtwidth_km2, filtwidth_yr2, filtwidth_day2, deramp2)
            else:
                label2 = '2: No filter'
        
    if cum_name2:
        cumname2 = cumh5[cum_name2][()]
        cumname2_ref = cumname2[ix_m, :, :]
        label3 = f'{cum_name2}'
    
    if cum_name3:
        cumname3 = cumh5[cum_name3][()]
        cumname3_ref = cumname3[ix_m, :, :]
        label4 = f'{cum_name3}'

    # 
    #%% Read Mask (1: unmask, 0: mask, nan: no cum data)
    mask_base = np.ones((length, width), dtype=np.float32)
    mask_base[np.isnan(cum[ix_m, :, :])] = np.nan

    if maskflag:
        print('Reading {} as mask'.format(os.path.relpath(maskfile)))
        mask_vel = io_lib.read_img(maskfile, length, width)

        mask_vel[mask_vel==0] = np.nan ## 0->nan
        mask = mask_vel
    else:
        mask = mask_base


    #%% Read U.geo file
    if LOSuflag:
        print('Reading {}'.format(os.path.relpath(LOSufile)))
        LOSu = io_lib.read_img(LOSufile, length, width)
        inc_agl_deg = np.rad2deg(np.arccos(LOSu))


    #%% Read noise indecies
    mapdict_data = {}
    mapdict_unit = {}
    names = ['mask', 'coh_avg', 'n_unw', 'vstd', 'maxTlen', 'n_gap', 'stc',
             'n_ifg_noloop', 'n_loop_err', 'resid', 'mli', 'hgt']
    units = ['', '', '', 'mm/yr', 'yr', '', 'mm', '', '', 'mm', 'log10', 'm']
    files = [maskfile, coh_avgfile, n_unwfile, vstdfile, maxTlenfile, n_gapfile,
             stcfile, n_ifg_noloopfile, n_loop_errfile, residfile, mlifile, hgtfile]
#    for name, file in zip(names, files):
    for i, name in enumerate(names):
        try:
            data = io_lib.read_img(files[i], length, width)
            mapdict_data[name] = data
            mapdict_unit[name] = units[i]
            print('Reading {}'.format(os.path.basename(files[i])))
        except:
            print('No {} found, not use.'.format(files[i]))


    #%% Calc time in datetime and ordinal
    imdates_dt = np.array(([dt.datetime.strptime(imd, '%Y%m%d') for imd in imdates])) ##datetime
    imdates_ordinal = np.array(([dt.datetime.strptime(imd, '%Y%m%d').toordinal() for imd in imdates])) ##73????
    imdates_ordinal = imdates_ordinal + mdates.date2num(np.datetime64('0000-12-31'))

    #%% Set color range for displacement and vel
    refvalue_lastcum = np.nanmean((cum[-1, refy1:refy2, refx1:refx2]
                                   -cum_ref[refy1:refy2, refx1:refx2])*mask[refy1:refy2, refx1:refx2])
    dmin_auto = np.nanpercentile((cum[-1, :, :]-cum_ref)*mask, 100-auto_crange)
    dmax_auto = np.nanpercentile((cum[-1, :, :]-cum_ref)*mask, auto_crange)
    if dmin is None and dmax is None: ## auto
        climauto = True
        dmin = dmin_auto - refvalue_lastcum
        dmax = dmax_auto - refvalue_lastcum
    else:
        climauto = False
        if dmin is None: dmin = dmin_auto - refvalue_lastcum
        if dmax is None: dmax = dmax_auto - refvalue_lastcum
    if not absolute:
        refvalue_vel = np.nanmean((vel*mask)[refy1:refy2+1, refx1:refx2+1])
    else:
        refvalue_vel = 0
    vmin_auto = np.nanpercentile(vel*mask, 100-auto_crange)
    vmax_auto = np.nanpercentile(vel*mask, auto_crange)
    if vmin is None and vmax is None: ## auto
        vlimauto = True
        vmin = vmin_auto - refvalue_vel
        vmax = vmax_auto - refvalue_vel
    else:
        vlimauto = False
        if vmin is None:
            vmin = vmin_auto - refvalue_vel
        if vmax is None:
            vmax = vmax_auto - refvalue_vel


    #%% Plot figure of cumulative displacement and velocity
    figsize_x = 6 if length > width else 9
    figsize_y = (figsize_x-2)*length*aspect/width+1
    if figsize_y < 5: figsize_y = 5
    figsize = (figsize_x, figsize_y)
    pv = plt.figure('Velocity / Cumulative Displacement', figsize)
    axv = pv.add_axes([0.15,0.15,0.83,0.83])
    axt2 = pv.text(0.01, 0.99, 'Left-doubleclick:\n Plot time series\nRight-drag:\n Change ref area', fontsize=8, va='top')
    axt = pv.text(0.01, 0.78, 'Ref area:\n X {}:{}\n Y {}:{}\n (start from 0)'.format(refx1, refx2, refy1, refy2), fontsize=8, va='bottom')

    ### background DEM
    if dem_background:
        alphamain = 0.8
        demtif=os.path.join(resultsdir,"hgt.geo.tif")
        print('Shadow DEM', demtif)
        az=-167.92738 # could rotate based on A/D
        ### Create hillshade
        with rio.open(demtif) as srca:
            elevationa = srca.read(1)
            h_dem = es.hillshade(elevationa,azimuth=az)
            axv.imshow(h_dem, cmap='Greys', alpha=0.8)
    else:
        alphamain = 1
    ### main plot
    rax, = axv.plot([refx1h, refx2h, refx2h, refx1h, refx1h],
                    [refy1h, refy1h, refy2h, refy2h, refy1h], '--k', alpha=0.8)
    if not absolute:
        data = vel*mask-np.nanmean((vel*mask)[refy1:refy2+1, refx1:refx2+1])
    else:
        data = vel*mask

    cax = axv.imshow(data, clim=[vmin, vmax], cmap=cmap, aspect=aspect, interpolation='nearest', alpha = alphamain)

    axv.set_title('vel')

    cbr = pv.colorbar(cax, orientation='vertical')
    cbr.set_label('mm/yr')

    cum_disp_flag = False


    #%% Set ref function
    def line_select_callback(eclick, erelease):
        global refx1, refx2, refy1, refy2, dmin, dmax
        ## global cannot change existing values... why?

        refx1p, refx2p, refy1p, refy2p = refx1, refx2, refy1, refy2 ## Previous

        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata
        if x1 <= x2: refx1, refx2 = [int(np.round(x1)), int(np.round(x2))]
        elif x1 > x2: refx1, refx2 = [int(np.round(x1)), int(np.round(x2))]
        if y1 <= y2: refy1, refy2 = [int(np.round(y1)), int(np.round(y2))]
        elif y1 > y2: refy1, refy2 = [int(np.round(y1)), int(np.round(y2))]

        if np.all(np.isnan(mask[refy1:refy2, refx1:refx2])): ## All nan
            print('Selected ref {}:{}/{}:{} has all nan!! Reselect different ref area.'.format(refx1, refx2, refy1, refy2))
            refx1, refx2, refy1, refy2 = refx1p, refx2p, refy1p, refy2p ## Get back
            return  ## No change

        refx1h = refx1-0.5; refx2h = refx2-0.5 ## Shift half for plot
        refy1h = refy1-0.5; refy2h = refy2-0.5

        axt.set_text('Ref area:\n X {}:{}\n Y {}:{}\n (start from 0)'.format(refx1, refx2, refy1, refy2))
        rax.set_data([refx1h, refx2h, refx2h, refx1h, refx1h],
            [refy1h, refy1h, refy2h, refy2h, refy1h])
        pv.canvas.draw()

        ### Change clim
        if climauto: ## auto
            refvalue_lastcum = np.nanmean((cum[-1, refy1:refy2, refx1:refx2]-cum_ref[refy1:refy2, refx1:refx2])*mask[refy1:refy2, refx1:refx2])
            dmin = dmin_auto - refvalue_lastcum
            dmax = dmax_auto - refvalue_lastcum

        ### Update draw
        if not cum_disp_flag:  ## vel or noise indice
            val_selected = radio_vel.value_selected
            val_ind = list(mapdict_data.keys()).index(val_selected)
            radio_vel.set_active(val_ind)
        else:  ## cumulative displacement
            time_selected = tslider.val
            tslider.set_val(time_selected)

        if lastevent:  ## Time series plot
            printcoords(lastevent)

    RS = RectangleSelector(axv, line_select_callback, useblit=True, button=[3], spancoords='pixels', interactive=False)

    plt.connect('key_press_event', RS)


    #%% Check box for mask ON/OFF
    if maskflag:
        axbox = pv.add_axes([0.01, 0.2, 0.1, 0.08])
        visibility = True
        check = CheckButtons(axbox, ['mask', ], [visibility, ])

        def func(label):
            global mask, visibility
            if visibility:
                mask = mask_base
                visibility = False

            else:
                mask = mask_vel
                visibility = True

            ### Update draw
            val_selected = radio_vel.value_selected
            val_ind = list(mapdict_data.keys()).index(val_selected)
            radio_vel.set_active(val_ind)

        check.on_clicked(func)


    #%% Radio buttom for velocity selection
    ## Add vel to mapdict
    if cumfile2:
        mapdict_vel = {'vel(1)': vel, 'vel(2)': vel2}
        mapdict_unit.update([('vel(1)', 'mm/yr'), ('vel(2)', 'mm/yr')])
    else:
        mapdict_vel = {'vel': vel}
        mapdict_unit.update([('vel', 'mm/yr')])

    mapdict_vel.update(mapdict_data)
    mapdict_data = mapdict_vel  ## To move vel to top
    axrad_vel = pv.add_axes([0.01, 0.3, 0.11, len(mapdict_data)*0.025+0.04])

    ### Radio buttons
    radio_vel = RadioButtons(axrad_vel, tuple(mapdict_data.keys()))
    for label in radio_vel.labels:
        label.set_fontsize(8)

    def show_vel(val_ind):
        global vmin, vmax, cum_disp_flag
        cum_disp_flag = False

        if 'vel' in val_ind:  ## Velocity
            data = mapdict_data[val_ind]*mask
            if not absolute:
                data = data-np.nanmean(data[refy1:refy2, refx1:refx2])
            if vlimauto: ## auto
                vmin = np.nanpercentile(data*mask, 100-auto_crange)
                vmax = np.nanpercentile(data*mask, auto_crange)
            cax.set_cmap(cmap)
            cax.set_clim(vmin, vmax)
            cbr.set_label('mm/yr')

        elif val_ind == 'mask':
            data = mapdict_data[val_ind]
            cax.set_cmap('viridis')
            cax.set_clim(0, 1)
            cbr.set_label('')

        else:  ## Other noise indices
            data = mapdict_data[val_ind]*mask
            if val_ind=='mli': data = np.log10(data)
            cmin_ind = np.nanpercentile(data*mask, 100-auto_crange)
            cmax_ind = np.nanpercentile(data*mask, auto_crange)
            if val_ind=='hgt': cmin_ind = -cmax_ind/3 ## bnecause 1/4 of terrain is blue
            cmap2 = 'viridis_r'
            if val_ind in ['coh_avg', 'n_unw', 'mask', 'maxTlen']:
                cmap2 = 'viridis'
            elif val_ind=='mli': cmap2 = cmc.grayC.reversed()
            elif val_ind=='hgt': cmap2 = 'terrain'
            cax.set_cmap(cmap2)
            cax.set_clim(cmin_ind, cmax_ind)

        cbr.set_label(mapdict_unit[val_ind])
        cax.set_data(data)
        axv.set_title(val_ind)

        pv.canvas.draw()

    radio_vel.on_clicked(show_vel)


    #%% Slider for cumulative displacement
    axtim = pv.add_axes([0.1, 0.08, 0.8, 0.05], yticks=[])
    tslider = Slider(axtim, 'yr', imdates_ordinal[0]-3, imdates_ordinal[-1]+3, valinit=imdates_ordinal[ix_m], valfmt='') #%0.0f
    tslider.ax.bar(imdates_ordinal, np.ones(len(imdates_ordinal)), facecolor='black', width=4)
    tslider.ax.bar(imdates_ordinal[ix_m], 1, facecolor='red', width=8)

    loc_tslider =  tslider.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    try: # Only support from Matplotlib 3.1!
        tslider.ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc_tslider))
    except:
        tslider.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m/%d'))
        for label in tslider.ax.get_xticklabels():
            label.set_rotation(20)
            label.set_horizontalalignment('right')

    dstr_ref = imdates_dt[ix_m].strftime('%Y/%m/%d')
    ### Slide bar action
    def tim_slidupdate(val):
        global cum_disp_flag
        timein = tslider.val
        timenearest = np.argmin(np.abs(mdates.date2num(imdates_dt)-timein))
        dstr = imdates_dt[timenearest].strftime('%Y/%m/%d')
#        axv.set_title('Time = %s'%(dstr))
        axv.set_title('%s (Ref: %s)'%(dstr, dstr_ref))
        newv = (cum[timenearest, :, :]-cum_ref)*mask
        if not absolute:
            newv = newv-np.nanmean(newv[refy1:refy2, refx1:refx2])

        cax.set_data(newv)
        cax.set_cmap(cmap)
        cax.set_clim(dmin, dmax)
        cbr.set_label('mm')
        cum_disp_flag = True

        pv.canvas.draw()


    tslider.on_changed(tim_slidupdate)


    
    if not correction_flag:
        #%% Plot figure of time series at a point
        pts = plt.figure('Time-series')
        axts = pts.add_axes([0.12, 0.14, 0.7,0.8])

        axts.scatter(imdates_dt, np.zeros(len(imdates_dt)), c='b', alpha=0.6)
        axts.grid()

        axts.set_xlabel('Time')
        axts.set_ylabel('Displacement (mm)')

        loc_ts = axts.xaxis.set_major_locator(mdates.AutoDateLocator())
        try:  # Only support from Matplotlib 3.1
            axts.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc_ts))
        except:
            axts.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m/%d'))
            for label in axts.get_xticklabels():
                label.set_rotation(20)
                label.set_horizontalalignment('right')

        ### Ref info at side
        axtref = pts.text(0.91, 0.95, 'Ref area:\n X {}:{}\n Y {}:{}\n (start from 0)\nRef date:\n {}'.format(refx1, refx2, refy1, refy2, imdates[ix_m]), fontsize=8, va='top')


        ### Fit function for time series
        fitbox = pts.add_axes([0.91, 0.10, 0.11, 0.25])
        models = ['Linear', 'Annual+L', 'Quad', 'Annual+Q']
        visibilities = [True, True, False, False]
        fitcheck = CheckButtons(fitbox, models, visibilities)
        
        def fitfunc(label):
            index = models.index(label)
            visibilities[index] = not visibilities[index]
            lines1[index].set_visible(not lines1[index].get_visible())
            if cumfile2:
                lines2[index].set_visible(not lines2[index].get_visible())

            pts.canvas.draw()

        fitcheck.on_clicked(fitfunc)

        ### First show of selected point in image window
        pax, = axv.plot([point_y], [point_x], 'k', linewidth=3)
        pax2, = axv.plot([point_y], [point_x], 'Pk')

        ### Plot time series at clicked point
        lastevent = []
        def printcoords(event):
            global dph, lines1, lines2, lastevent
            #outputting x and y coords to console
            if event.inaxes != axv:
                return
            elif event.button != 1: ## Only left click
                return
            elif not event.dblclick: ## Only double click
                return
            else:
                lastevent = event  ## Update last event

            ii = int(np.round(event.ydata))
            jj = int(np.round(event.xdata))

            ### Plot on image window
            ii1h = ii-0.5; ii2h = ii+1-0.5 ## Shift half for plot
            jj1h = jj-0.5; jj2h = jj+1-0.5
            pax.set_data([jj1h, jj2h, jj2h, jj1h, jj1h], [ii1h, ii1h, ii2h, ii2h, ii1h])
            pax2.set_data([jj], [ii])
            pv.canvas.draw()

            axts.cla()
            axts.grid(zorder=0)
            axts.set_axisbelow(True)
            axts.set_xlabel('Time')
            axts.set_ylabel('Displacement (mm)')

            ### Get values of noise indices and incidence angle
            noisetxt = ''
            for key in mapdict_data:
                val = mapdict_data[key][ii, jj]
                unit = mapdict_unit[key]
                if key.startswith('vel'): ## Not plot here
                    continue
                elif key.startswith('n_') or key=='mask':
                    val = 'nan' if np.isnan(val) else int(val)
                    noisetxt = noisetxt+'{}: {} {}\n'.format(key, val, unit)
                else:
                    noisetxt = noisetxt+'{}: {:.2f} {}\n'.format(key, val, unit)

            if LOSuflag:
                noisetxt = noisetxt+'Inc_agl: {:.1f} deg\n'.format(inc_agl_deg[ii, jj])
                noisetxt = noisetxt+'LOS u: {:.3f}\n'.format(LOSu[ii, jj])

            ### Get lat lon and show Ref info at side
            if geocod_flag:
                lat, lon = tools_lib.xy2bl(jj, ii, lat1, dlat, lon1, dlon)
                axtref.set_text('Lat:{:.5f}\nLon:{:.5f}\n\nRef area:\n X {}:{}\n Y {}:{}\n (start from 0)\nRef date:\n {}\n\n{}'.format(lat, lon, refx1, refx2, refy1, refy2, imdates[ix_m], noisetxt))
            else:
                axtref.set_text('Ref area:\n X {}:{}\n Y {}:{}\n (start from 0)\nRef date:\n {}\n\n{}'.format(refx1, refx2, refy1, refy2, imdates[ix_m], noisetxt))

            ### If masked
            if np.isnan(mask[ii, jj]):
                axts.set_title('NaN @({}, {})'.format(jj, ii), fontsize=10)
                pts.canvas.draw()
                return

            try: # Only support from Matplotlib 3.1!
                axts.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc_ts))
            except:
                axts.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m/%d'))
                for label in axts.get_xticklabels():
                    label.set_rotation(20)
                    label.set_horizontalalignment('right')


            ### If not masked
            ### cumfile
            if not absolute:
                vel1p = vel[ii, jj]-np.nanmean((vel*mask)[refy1:refy2, refx1:refx2])

                dcum_ref = cum_ref[ii, jj]-np.nanmean(cum_ref[refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2])
                #dcum_ref = 0
                dph = cum[:, ii, jj]-np.nanmean(cum[:, refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2], axis=(1, 2)) - dcum_ref
                if tsstd is not None:
                    std_ref = tsstd[:,refy1:refy2, refx1:refx2] * mask[refy1:refy2, refx1:refx2]
                    std_ref[std_ref==0] = np.nan
                    if np.isnan(std_ref).all():
                        std_ref = 0
                    else:
                        std_ref = np.sqrt(np.nansum(std_ref**2, axis=(1, 2))) / np.sum(~np.isnan(std_ref), axis=(1, 2))
                    #
                    std_point = np.sqrt(tsstd[:,ii,jj] ** 2 + std_ref ** 2)
            else:
                vel1p = vel[ii, jj]
                dph = cum_abs[:, ii, jj] # - cum_abs_ref[ii, jj]
                if tsstd is not None:
                    std_point = tsstd[:, ii, jj]
            ## fit function
            lines1 = [0, 0, 0, 0]
            xvalues = np.arange(imdates_ordinal[0], imdates_ordinal[-1], 10)
            td10day = dt.timedelta(days=10)
            xvalues_dt = np.arange(imdates_dt[0], imdates_dt[-1], td10day)
            for model, vis in enumerate(visibilities):
                yvalues = calc_model(dph, imdates_ordinal, xvalues, model)
                if not novel_flag:
                    lines1[model], = axts.plot(xvalues_dt, yvalues, 'b-', visible=vis, alpha=0.6, zorder=3)
            if not novel_flag:
                axts.scatter(imdates_dt, dph, label=label1, c='b', alpha=0.6, zorder=5)
                axts.set_title('vel = {:.1f} mm/yr @({}, {})'.format(vel1p, jj, ii), fontsize=10)

            ### cumfile2
            if cumfile2:
                if not absolute:
                    vel2p = vel2[ii, jj]-np.nanmean((vel2*mask)[refy1:refy2, refx1:refx2])
                    dcum2_ref = cum2_ref[ii, jj]-np.nanmean(cum2_ref[refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2])
                    dphf = cum2[:, ii, jj]-np.nanmean(cum2[:, refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2], axis=(1, 2)) - dcum2_ref
                else:
                    vel2p = vel2[ii, jj]
                    # dcum2_ref = cum2_ref[ii, jj]
                    dphf = cum2[:, ii, jj] # - dcum2_ref
                ## fit function
                lines2 = [0, 0, 0, 0]
                for model, vis in enumerate(visibilities):
                    yvalues = calc_model(dphf, imdates_ordinal, xvalues, model)
                    if not novel_flag:
                        lines2[model], = axts.plot(xvalues_dt, yvalues, 'r-', visible=vis, alpha=0.6, zorder=2)
                if not novel_flag:
                    axts.scatter(imdates_dt, dphf, c='r', label=label2, alpha=0.6, zorder=4)
                    axts.set_title('vel(1) = {:.1f} mm/yr, vel(2) = {:.1f} mm/yr @({}, {})'.format(vel1p, vel2p, jj, ii), fontsize=10)

            if tsstd is not None:
                axts.errorbar(imdates_dt[1:], dph[1:], yerr=2*std_point,
                            fmt='none', ecolor='blue', capsize = 3, zorder=3, alpha=0.5, label='±2σ')
                #
                #axts.fill_between(imdates_dt[1:], dph[1:] - 2*stds, dph[1:] + 2*stds, color='blue',alpha=0.25,linewidth=0,zorder=3,
                #                  label='±2σ')
                # axts.scatter(imdates_dt[1:], stds, c='purple', label='1-sigma', alpha=0.6, zorder=4)
                if not ylen:
                    vlim = [np.nanmin(dph) - 5, np.nanmax(dph) + 5]
                    axts.set_ylim(vlim)

            if cum_name2:
                dcumname2_ref = cumname2_ref[ii, jj]-np.nanmean(cumname2_ref[refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2])
                dphf = cumname2[:, ii, jj]-np.nanmean(cumname2[:, refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2], axis=(1, 2)) - dcumname2_ref
                axts.scatter(imdates_dt, dphf, c='orange', label=label3, alpha=0.6, zorder=4)
                # axts.set_title('vel(1) = {:.1f} mm/yr, vel(2) = {:.1f} mm/yr @({}, {})'.format(vel1p, vel2p, jj, ii), fontsize=10)
            
            if cum_name3:
                dcumname3_ref = cumname3_ref[ii, jj]-np.nanmean(cumname3_ref[refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2])
                dphf = cumname3[:, ii, jj]-np.nanmean(cumname3[:, refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2], axis=(1, 2)) - dcumname3_ref
                axts.scatter(imdates_dt, dphf, c='purple', label=label4, alpha=0.6, zorder=4)
                # axts.set_title('vel(1) = {:.1f} mm/yr, vel(2) = {:.1f} mm/yr @({}, {})'.format(vel1p, vel2p, jj, ii), fontsize=10)



            ## gap
            if gap:
                gap1p = (gap[:, ii, jj]==1) # n_im-1, bool
                if not np.all(~gap1p): ## Not plot if no gap
                    gap_dates_dt = imdates_dt[0:-1][gap1p]-imdates_dt[1:][gap1p]
                    gap_dt = imdates_dt[1:][gap1p]+gap_dates_dt/2
                    axts.vlines(gap_dt, 0, 1, transform=axts.get_xaxis_transform(), zorder=1, label=label_gap, alpha=0.6, colors='k')

            ### Y axis
            if ylen:
                vlim = [np.nanmedian(dph)-ylen/2, np.nanmedian(dph)+ylen/2]
                axts.set_ylim(vlim)

            ### Legend
            axts.legend()
            #
            locator = mdates.AutoDateLocator()
            axts.xaxis.set_major_locator(locator)
            axts.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
            pts.canvas.draw()

    if correction_flag:
        #%% Plot figure of time series at a point
        # Create a figure with 2 rows and 1 column
        fig, axs = plt.subplots(2, 1, figsize=(8, 8), sharex=True)
        # fig.suptitle('Time-Series and Corrections', fontsize=14)
        axts_corr = axs[0]
        axts = axs[1]
        axts.scatter(imdates_dt, np.zeros(len(imdates_dt)), c='b', alpha=0.6)
        axts_corr.scatter(imdates_dt, np.zeros(len(imdates_dt)), c='b', alpha=0.6)
                
        loc_ts = mdates.AutoDateLocator()
        axts.xaxis.set_major_locator(loc_ts)
        try:
            axts.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc_ts))
        except:
            axts.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m/%d'))
            for label in axts.get_xticklabels():
                label.set_rotation(20)
                label.set_horizontalalignment('right')

        ### Ref info at side
        if absolute:
            axtref = fig.text(0.91, 0.95, 'Ref date:\n {}'.format(imdates[ix_m]), fontsize=8, va='top')
        else:
            axtref = fig.text(0.91, 0.95, 'Ref area:\n X {}:{}\n Y {}:{}\n (start from 0)\nRef date:\n {}'.format(refx1, refx2, refy1, refy2, imdates[ix_m]), fontsize=8, va='top')


        ### Fit function for time series
        fitbox = fig.add_axes([0.91, 0.10, 0.11, 0.25])
        models = ['Linear', 'Annual+L', 'Quad', 'Annual+Q']
        visibilities = [True, True, False, False]
        fitcheck = CheckButtons(fitbox, models, visibilities)

        def fitfunc(label):
            index = models.index(label)
            visibilities[index] = not visibilities[index]
            lines1[index].set_visible(not lines1[index].get_visible())
            if cumfile2:
                lines2[index].set_visible(not lines2[index].get_visible())

            fig.canvas.draw()

        fitcheck.on_clicked(fitfunc)

        ### First show of selected point in image window
        pax, = axv.plot([point_y], [point_x], 'k', linewidth=3)
        pax2, = axv.plot([point_y], [point_x], 'Pk')

        ### Plot time series at clicked point
        lastevent = []
        def printcoords(event):
            global dph, dphf, iono_adjusted, tide_adjusted, lines1, lines2, lastevent
            #outputting x and y coords to console
            if event.inaxes != axv:
                return
            elif event.button != 1: ## Only left click
                return
            elif not event.dblclick: ## Only double click
                return
            else:
                lastevent = event  ## Update last event

            ii = int(np.round(event.ydata))
            jj = int(np.round(event.xdata))

            ### Plot on image window
            ii1h = ii-0.5; ii2h = ii+1-0.5 ## Shift half for plot
            jj1h = jj-0.5; jj2h = jj+1-0.5
            pax.set_data([jj1h, jj2h, jj2h, jj1h, jj1h], [ii1h, ii1h, ii2h, ii2h, ii1h])
            pax2.set_data([jj], [ii])
            pv.canvas.draw()

            # First subplot: Plot corrections (tide and iono)
            axts_corr.cla()
            axts_corr.set_ylabel('Correction (mm)')
            axts_corr.grid(zorder=0)
            axts_corr.set_axisbelow(True)
            axts_corr.set_title('Tide and Ionospheric Corrections')
            # axts_corr.set_ylim(-75, 75)

            # Second subplot: Plot cumulative displacement
            axts.cla()
            axts.set_xlabel('Time')
            axts.set_ylabel('Displacement (mm)')
            axts.grid(zorder=0)
            axts.set_axisbelow(True)
            axts.set_title('Cumulative Displacement and Corrected Displacement')

            ### Get values of noise indices and incidence angle
            noisetxt = ''
            for key in mapdict_data:
                val = mapdict_data[key][ii, jj]
                unit = mapdict_unit[key]
                if key.startswith('vel'): ## Not plot here
                    continue
                elif key.startswith('n_') or key=='mask':
                    val = 'nan' if np.isnan(val) else int(val)
                    noisetxt = noisetxt+'{}: {} {}\n'.format(key, val, unit)
                else:
                    noisetxt = noisetxt+'{}: {:.2f} {}\n'.format(key, val, unit)

            if LOSuflag:
                noisetxt = noisetxt+'Inc_agl: {:.1f} deg\n'.format(inc_agl_deg[ii, jj])
                noisetxt = noisetxt+'LOS u: {:.3f}\n'.format(LOSu[ii, jj])

            ### Get lat lon and show Ref info at side
            if geocod_flag:
                lat, lon = tools_lib.xy2bl(jj, ii, lat1, dlat, lon1, dlon)
                if not absolute:
                    axtref.set_text('Lat:{:.5f}\nLon:{:.5f}\n\nRef area:\n X {}:{}\n Y {}:{}\n (start from 0)\nRef date:\n {}\n\n{}'.format(lat, lon, refx1, refx2, refy1, refy2, imdates[ix_m], noisetxt))
                if absolute:
                    axtref.set_text('Lat:{:.5f}\nLon:{:.5f}\n\nRef date:\n {}\n\n{}'.format(lat, lon, imdates[ix_m], noisetxt))
            else:
                if not absolute:
                    axtref.set_text('Ref area:\n X {}:{}\n Y {}:{}\n (start from 0)\nRef date:\n {}\n\n{}'.format(refx1, refx2, refy1, refy2, imdates[ix_m], noisetxt))
                if absolute:
                    axtref.set_text('Ref date:\n {}\n\n{}'.format(imdates[ix_m], noisetxt))
            ### If masked
            if np.isnan(mask[ii, jj]):
                axts.set_title('NaN @({}, {})'.format(jj, ii), fontsize=10)
                fig.canvas.draw()
                return

            try: # Only support from Matplotlib 3.1!
                axts.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc_ts))
            except:
                axts.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m/%d'))
                for label in axts.get_xticklabels():
                    label.set_rotation(20)
                    label.set_horizontalalignment('right')


            ##plot tide and iono separately in the top panel
            if tide is not None:
                if not absolute:
                    tide_ref_value = tide_ref[ii, jj]-np.nanmean(tide_ref[refy1:refy2, refx1:refx2] * mask[refy1:refy2, refx1:refx2])
                    tide_adjusted = tide[:, ii, jj]-np.nanmean(tide[:, refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2], axis=(1, 2)) - tide_ref_value
                else:
                    tide_adjusted = tide[:, ii, jj]-tide_ref[ii, jj]
                    
                # Plot adjusted tide correction
                axts_corr.scatter(imdates_dt, tide_adjusted, label=label_tide, c='#FFA500', alpha=0.8, zorder=4, marker="o")  # Orange
                axts_corr.plot(imdates_dt, tide_adjusted, color='#FFA500', alpha=0.8, linestyle='-', zorder=4)  # Orange line
                
            if iono is not None:
                # Adjust iono correction by subtracting the reference value
                if not absolute:
                    iono_ref_value = iono_ref[ii, jj]-np.nanmean(iono_ref[refy1:refy2, refx1:refx2] * mask[refy1:refy2, refx1:refx2])
                    iono_adjusted = iono[:, ii, jj]-np.nanmean(iono[:, refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2], axis=(1, 2)) - iono_ref_value
                else:
                    iono_adjusted = iono[:, ii, jj]-iono_ref[ii, jj]
                # Plot adjusted iono correction
                axts_corr.scatter(imdates_dt, iono_adjusted, label=label_iono, c='#800080', alpha=0.8, zorder=4, marker="^")  # Purple
                axts_corr.plot(imdates_dt, iono_adjusted, color='#800080', alpha=0.8, linestyle='-', zorder=4)  # Purple line 
            
            if gacos is not None:
                # Adjust gacos correction by subtracting the reference value
                if not absolute:
                    gacos_ref_value = gacos_ref[ii, jj]-np.nanmean(gacos_ref[refy1:refy2, refx1:refx2] * mask[refy1:refy2, refx1:refx2])
                    gacos_adjusted = gacos[:, ii, jj]-np.nanmean(gacos[:, refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2], axis=(1, 2)) - gacos_ref_value
                else:
                    gacos_adjusted = gacos[:, ii, jj]-gacos_ref[ii, jj]
                # Plot adjusted gacos correction
                axts_corr.scatter(imdates_dt, gacos_adjusted, label=label_gacos, c='green', alpha=0.8, zorder=4, marker="s")
                axts_corr.plot(imdates_dt, gacos_adjusted, color='green', alpha=0.8, linestyle='-', zorder=4)  # Green line
            
            if iono2 is not None:
                # Adjust iono2 correction by subtracting the reference value
                if not absolute:
                    iono2_ref_value = iono2_ref[ii, jj]-np.nanmean(iono2_ref[refy1:refy2, refx1:refx2] * mask[refy1:refy2, refx1:refx2])
                    iono2_adjusted = iono2[:, ii, jj]-np.nanmean(iono2[:, refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2], axis=(1, 2)) - iono2_ref_value
                else:
                    iono2_adjusted = iono2[:, ii, jj] #-iono2_ref[ii, jj]
                # Plot adjusted iono2 correction
                axts_corr.scatter(imdates_dt, iono2_adjusted, label=label_iono2, c='red', alpha=0.8, zorder=4, marker="p")  # Purple
                axts_corr.plot(imdates_dt, iono2_adjusted, color='red', alpha=0.8, linestyle='-', zorder=4)  # Purple line       
            
            ##plot cum and cum_corr in the bottom panel
            ### cumfile
            if not absolute:
                vel1p = vel[ii, jj]-np.nanmean((vel*mask)[refy1:refy2, refx1:refx2])

                dcum_ref = cum_ref[ii, jj]-np.nanmean(cum_ref[refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2])
    #           dcum_ref = 0
                dph = cum[:, ii, jj]-np.nanmean(cum[:, refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2], axis=(1, 2)) - dcum_ref
            else:
                vel1p = vel[ii, jj]
                dph = cum_abs[:, ii, jj] # - cum_abs_ref[ii, jj]
            ## fit function
            lines1 = [0, 0, 0, 0]
            xvalues = np.arange(imdates_ordinal[0], imdates_ordinal[-1], 10)
            td10day = dt.timedelta(days=10)
            xvalues_dt = np.arange(imdates_dt[0], imdates_dt[-1], td10day)
            for model, vis in enumerate(visibilities):
                yvalues = calc_model(dph, imdates_ordinal, xvalues, model)
                if not novel_flag:
                    lines1[model], = axts.plot(xvalues_dt, yvalues, 'b-', visible=vis, alpha=0.6, zorder=3)
            if not novel_flag:
                axts.scatter(imdates_dt, dph, label=label1, c='b', alpha=0.6, zorder=5)
                axts.set_title('vel = {:.1f} mm/yr @({}, {})'.format(vel1p, jj, ii), fontsize=10)
            
            ### cumfile2
            if cumfile2:
                if not absolute:
                    vel2p = vel2[ii, jj]-np.nanmean((vel2*mask)[refy1:refy2, refx1:refx2])
                    dcum2_ref = cum2_ref[ii, jj]-np.nanmean(cum2_ref[refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2])
                    dphf = cum2[:, ii, jj]-np.nanmean(cum2[:, refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2], axis=(1, 2)) - dcum2_ref
                else:
                    vel2p = vel2[ii, jj]
                    dcum2_ref = cum2_ref[ii, jj]
                    dphf = cum2[:, ii, jj]-dcum2_ref
                ## fit function
                lines2 = [0, 0, 0, 0]
                for model, vis in enumerate(visibilities):
                    yvalues = calc_model(dphf, imdates_ordinal, xvalues, model)
                    if not novel_flag:
                        lines2[model], = axts.plot(xvalues_dt, yvalues, 'r-', visible=vis, alpha=0.6, zorder=2)
                if not novel_flag:
                    axts.scatter(imdates_dt, dphf, c='r', label=label2, alpha=0.6, zorder=4)
                    axts.set_title('vel(1) = {:.1f} mm/yr, vel(2) = {:.1f} mm/yr @({}, {})'.format(vel1p, vel2p, jj, ii), fontsize=10)
            
            if cum_name2:
                dcumname2_ref = cumname2_ref[ii, jj]-np.nanmean(cumname2_ref[refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2])
                dphf = cumname2[:, ii, jj]-np.nanmean(cumname2[:, refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2], axis=(1, 2)) - dcumname2_ref
                axts.scatter(imdates_dt, dphf, c='orange', label=label3, alpha=0.6, zorder=4)
                # axts.set_title('vel(1) = {:.1f} mm/yr, vel(2) = {:.1f} mm/yr @({}, {})'.format(vel1p, vel2p, jj, ii), fontsize=10)
            
            if cum_name3:
                dcumname3_ref = cumname3_ref[ii, jj]-np.nanmean(cumname3_ref[refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2])
                dphf = cumname3[:, ii, jj]-np.nanmean(cumname3[:, refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2], axis=(1, 2)) - dcumname3_ref
                axts.scatter(imdates_dt, dphf, c='purple', label=label4, alpha=0.6, zorder=4)
                # axts.set_title('vel(1) = {:.1f} mm/yr, vel(2) = {:.1f} mm/yr @({}, {})'.format(vel1p, vel2p, jj, ii), fontsize=10)

            
            ## gap
            if gap:
                gap1p = (gap[:, ii, jj]==1) # n_im-1, bool
                if not np.all(~gap1p): ## Not plot if no gap
                    gap_dates_dt = imdates_dt[0:-1][gap1p]-imdates_dt[1:][gap1p]
                    gap_dt = imdates_dt[1:][gap1p]+gap_dates_dt/2
                    axts.vlines(gap_dt, 0, 1, transform=axts.get_xaxis_transform(), zorder=1, label=label_gap, alpha=0.6, colors='k')

            ### Y axis
            if ylen:
                vlim = [np.nanmedian(dph)-ylen/2, np.nanmedian(dph)+ylen/2]
                axts.set_ylim(vlim)

            ### Legend
            axts.legend()
            axts_corr.legend()
            
            fig.canvas.draw()




    #%% First show of time series window
    event = matplotlib.backend_bases.LocationEvent
    event.xdata = point_x
    event.ydata = point_y
    event.inaxes = axv
    event.button = 1
    event.dblclick = True
    #lastevent = event
    #printcoords(lastevent)
    printcoords(event)

    #%%
    if ts_pngfile:
        print('\nCreate {} for time seires plot\n'.format(ts_pngfile))
        fig.savefig(ts_pngfile)
        sys.exit(0)


    #%% Final linking of the canvas to the plots.
    cid = pv.canvas.mpl_connect('button_press_event', printcoords)
    with warnings.catch_warnings(): ## To silence user warning
        warnings.simplefilter('ignore', UserWarning)
        plt.show()
    pv.canvas.mpl_disconnect(cid)

