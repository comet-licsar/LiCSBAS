#!/usr/bin/env python3
"""

========
Overview
========
This script calculates velocity and its standard deviation from cum*.h5 and outputs them as a float32 file.
Amplitude and time offset of the annual displacement can also be calculated by --sin option.
It can estimate offsets based on earthquake event datetime or external offsets.txt file. This will not work with --sin. However --vstd would in such case be calculated from residuals.

=====
Usage
=====
LiCSBAS_cum2vel.py [-s yyyymmdd] [-e yyyymmdd] [-i infile] [-o outfilenamestr] [-r x1:x2/y1:y2]
    [--ref_geo lon1/lon2/lat1/lat2] [--vstd] [--sin] [--mask maskfile] [--png] [--eqoffsets minmag] [--offsets offsets.txt]
    [--export_model outmodelfile.h5]

 -s  Start date of period to calculate velocity (Default: first date)
 -e  End date of period to calculate velocity (Default: last date)
 -i  Path to input cum file (Default: cum_filt.h5)
 -o  Output filename root string - will use to name modeled variables (Default: yyyymmdd_yyyymmdd -> yyyymmdd_yyyymmdd.vel[.mskd])
 -r  Reference area (Default: same as info/*ref.txt)
     Note: x1/y1 range 0 to width-1, while x2/y2 range 1 to width
     0 for x2/y2 means all. (i.e., 0:0/0:0 means whole area).
 --ref_geo  Reference area in geographical coordinates.
 --vstd  Calculate vstd (+ stc and RMSE) (Default: No)
 --sin   Add sin (annual) funcsion to linear model (Default: No)
         *.amp and *.dt (time difference wrt Jan 1) are output
 --mask  Path to mask file for ref phase calculation (Default: No mask)
 --png   Make png file (Default: Not make png)
 --eqoffsets  minmag  Estimate also offsets for earthquakes above minmag (float) in the region (defaults to M6.5+)
 --offsets offsets.txt  Estimate offsets read from external txt file - both yyyymmdd and yyyy-mm-dd form is supported
 --export_model modelfile.h5  Export the model time series to H5 file. Can be used for step 16 (Default: not export)
 --store_to_results  Setting this parameter, outputs will be stored to the results directory (overwriting existing files)
 --datavar cum   Option to change the input data variable name (standard is 'cum' - will work for any with the expected shape)
"""
#%% Change log
'''
2024-12 ML, ULeeds:
 - added calc of RMSE
2024-11 ML, ULeeds:
 - added also offsets 
2024-10-22 Milan Lazecky, ULeeds
 - added eqoffsets
 - recalc vstd and stc based on residuals from the model with offsets
v1.3.3 20210910 Yu Morishita, GSI
 - Avoid error for refarea in bytes
v1.3.2 20210125 Yu Morishita, GSI
 - Change cmap for vstd, amp, dt
v1.3.1 20210107 Yu Morishita, GSI
 - Replace jet with SCM.roma_r
v1.3 20200703 Yu Morishita, GSI
 - Add --ref_geo option
v1.2 20190807 Yu Morishita, Uni of Leeds and GSI
 - Add sin option
v1.1 20190802 Yu Morishita, Uni of Leeds and GSI
 - Make vstd optional
v1.0 20190730 Yu Morishita, Uni of Leeds and GSI
 - Original implementationf
'''

#%% Import
import getopt
import os
import sys
import re
import time
import numpy as np
import datetime as dt
import h5py as h5
import cmcrameri.cm as cmc
import LiCSBAS_io_lib as io_lib
import LiCSBAS_inv_lib as inv_lib
import LiCSBAS_tools_lib as tools_lib
import LiCSBAS_plot_lib as plot_lib
from LiCSBAS_meta import *

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
    #ver="1.3.3"; date=20210910; author="Y. Morishita" # this is from LiCSBAS_meta now
    print("\n{} ver{} {} {}".format(os.path.basename(argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(argv[0]), ' '.join(argv[1:])), flush=True)

    #%% Set default
    imd_s = []
    imd_e = []
    cumfile = 'cum_filt.h5'
    datavar = 'cum'
    outfile = []
    refarea = []
    refarea_geo = []
    maskfile = []
    vstdflag = False
    stcflag = False
    sinflag = False
    pngflag = False
    eqoffsetsflag = False
    offsetsflag = False
    offsetsfile = []
    exportmodelfile = []
    modelflag = False
    minmag = 6.5
    cmap = cmc.romaO.reversed()
    cmap_vstd = 'viridis_r'
    cmap_stc = 'viridis_r'
    cmap_amp = 'viridis_r'
    cmap_dt = cmc.romaO.reversed()
    compress = 'gzip'
    store_to_results = False

    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hs:e:i:o:r:", ["help", "datavar=", "store_to_results", "vstd", "sin", "eqoffsets=", "offsets=","export_model=","png", "ref_geo=", "mask="])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                return 0
            elif o == '-s':
                imd_s = a
            elif o == '-e':
                imd_e = a
            elif o == '-i':
                cumfile = a
            elif o == '-o':
                outfile = a
            elif o == '-r':
                refarea = a
            elif o == '--ref_geo':
                refarea_geo = a
            elif o == '--vstd':
                vstdflag = True
                stcflag = True
                modelflag = True
            elif o == '--sin':
                sinflag = True
            elif o == '--mask':
                maskfile = a
            elif o == '--png':
                pngflag = True
            elif o == '--datavar':
                datavar = a
            elif o == '--eqoffsets':
                minmag = float(a)
                eqoffsetsflag = True
            elif o == '--offsets':
                offsetsfile = a
                offsetsflag = True
            elif o == '--export_model':
                exportmodelfile = a
                modelflag = True
            elif o == '--store_to_results':
                store_to_results = True
        if not os.path.exists(cumfile):
            raise Usage('No {} exists! Use -i option.'.format(cumfile))
        if sinflag and (eqoffsetsflag or offsetsflag):
            raise Usage('--sin does not (yet) work together with offsets estimation - cancelling')
        if offsetsflag:
            if not os.path.exists(offsetsfile):
                raise Usage('Offsets file not provided')
                #raise Usage('Sorry, this functionality is not implemented yet - please raise Issue on github')
        if store_to_results:
            tsdir = os.path.dirname(cumfile)
            resultsdir = os.path.join(tsdir, 'results')
            if not os.path.exists(resultsdir):
                raise Usage('ERROR: The results directory is not provided with the input file')

    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2


    if eqoffsetsflag:
        print('getting earthquakes over the region')
        offsets = tools_lib.get_earthquake_dates(cumfile, minmag=minmag, maxdepth=60)
        print('identified '+str(len(offsets))+' earthquake candidates to solve')
        print('')
        try:
            outxt = os.path.join(os.path.dirname(cumfile), 'info', 'eqoffsets.txt')
            with open(outxt, 'w') as f:
                for i in offsets:
                    print('{}'.format(i), file=f)
            print('stored to file:')
            print(outxt)
        except:
            print('some error storing earthquake offsets to '+outxt+'. Continuing')

    if offsetsflag:
        if not eqoffsetsflag:
            offsets = io_lib.read_epochlist(offsetsfile, outasdt=True)
        print('Loaded '+str(len(offsets))+' offsets:')
        print(offsets)
        print('')


    #%% Read info
    ### Read cumfile
    cumh5 = h5.File(cumfile,'r')
    imdates = cumh5['imdates'][()].astype(str).tolist()
    # cumh5 = xr.open_dataset(cumfile) # future: xr
    # imdates = list(a.time.dt.strftime('%Y%m%d').values)
    cum = cumh5[datavar]
    n_im_all, length, width = cum.shape

    if refarea:
        if not tools_lib.read_range(refarea, width, length):
            print('\nERROR in {}\n'.format(refarea), file=sys.stderr)
            return 2
        else:
            refx1, refx2, refy1, refy2 = tools_lib.read_range(refarea, width, length)
    elif refarea_geo:
        lat1 = float(cumh5['corner_lat'][()])
        lon1 = float(cumh5['corner_lon'][()])
        dlat = float(cumh5['post_lat'][()])
        dlon = float(cumh5['post_lon'][()])
        if not tools_lib.read_range_geo(refarea_geo, width, length, lat1, dlat, lon1, dlon):
            print('\nERROR in {}\n'.format(refarea_geo), file=sys.stderr)
            return 2
        else:
            refx1, refx2, refy1, refy2 = tools_lib.read_range_geo(refarea_geo, width, length, lat1, dlat, lon1, dlon)
    else:
        refarea = cumh5['refarea'][()]
        if type(refarea) is bytes:
            refarea = refarea.decode('utf-8')
        refx1, refx2, refy1, refy2 = [int(s) for s in re.split('[:/]', refarea)]


    #%% Setting
    ### Dates
    if not imd_s:
        imd_s = imdates[0]

    if not imd_e:
        imd_e = imdates[-1]

    ### mask
    if maskfile:
        mask = io_lib.read_img(maskfile, length, width)
        mask[mask==0] = np.nan
        suffix_mask = '.mskd'
    else:
        mask = np.ones((length, width), dtype=np.float32)
        suffix_mask = ''

    ### Find date index if not exist in imdates
    if not imd_s in imdates:
        for imd in imdates:
            if int(imd) >= int(imd_s): ## First larger one than imd_s
                imd_s = imd
                break

    if not imd_e in imdates:
        for imd in imdates[::-1]:
            if int(imd) <= int(imd_e): ## Last smaller one than imd_e
                imd_e = imd
                break

    ix_s = imdates.index(imd_s)
    ix_e = imdates.index(imd_e)+1 #+1 for python custom
    n_im = ix_e-ix_s

    ### Calc dt in year
    imdates_dt = ([dt.datetime.strptime(imd, '%Y%m%d').toordinal() for imd in imdates[ix_s:ix_e]])
    dt_cum = np.float32((np.array(imdates_dt)-imdates_dt[0])/365.25)

    ### Outfile
    if not outfile:
        outfile = '{}_{}'.format(imd_s, imd_e)

    if store_to_results:
        velfile = os.path.join(resultsdir, 'vel'+suffix_mask)
        vconstfile = os.path.join(resultsdir, 'vconst'+suffix_mask)
    else:
        velfile = outfile + '.vel' + suffix_mask
        vconstfile = outfile + '.vconst' + suffix_mask

    #%% Display info
    print('')
    print('Start date  : {}'.format(imdates[ix_s]))
    print('End date    : {}'.format(imdates[ix_e-1]))
    print('# of images : {}'.format(n_im))
    print('Ref area    : {}:{}/{}:{}'.format(refx1, refx2, refy1, refy2))
    print('')


    #%% Calc velocity and vstd
    vconst = np.zeros((length, width), dtype=np.float32)*np.nan
    vel = np.zeros((length, width), dtype=np.float32)*np.nan

    ### Read cum data
    cum_tmp = cum[ix_s:ix_e, :, :]*mask
    cum_ref = np.nanmean(cum[ix_s:ix_e, refy1:refy2, refx1:refx2]*mask[refy1:refy2, refx1:refx2], axis=(1, 2))

    if np.all(np.isnan(cum_ref)):
        print('\nERROR: Ref area has only NaN value!\n', file=sys.stderr)
        return 2

    cum_tmp = cum_tmp-cum_ref[:, np.newaxis, np.newaxis]

    ### Extract not nan points
    bool_allnan = np.all(np.isnan(cum_tmp), axis=0)
    cum_tmp_resh = cum_tmp.reshape(n_im, length*width)[:, ~bool_allnan.ravel()].transpose()
    #
    if exportmodelfile:
        # get the output model h5 file ready:
        modh5file = os.path.join(os.path.dirname(cumfile), 'model.h5')
        modh5 = h5.File(modh5file, 'w')

    if eqoffsetsflag or offsetsflag:
        print('Calc vel and earthquake offsets')
        result, datavarnames, G = inv_lib.calc_vel_offsets(cum_tmp_resh, imdates_dt, offsets, return_G = True)
        params_sorted = []
        print('')
        for i in range(len(datavarnames)):
            dvarname = datavarnames[i]
            print('storing '+dvarname)
            dvar = np.zeros((length, width), dtype=np.float32)*np.nan
            dvar[~bool_allnan] = result[i,:]
            if store_to_results:
                outvarfile = os.path.join(resultsdir, dvarname + suffix_mask)
            else:
                outvarfile = outfile+'.'+dvarname+suffix_mask
            dvar.tofile(outvarfile)
            # also use vel (and vconst?) as usual:
            if dvarname == 'vel':
                vel = dvar
            if exportmodelfile:
                # also export to the h5 (why not)
                modh5.create_dataset(dvarname, data=dvar, compression=compress)
            if modelflag:
                # add as inputs for the model
                params_sorted.append(dvar)
            if pngflag:
                pngfile = outvarfile + '.png'
                # title = 'n_im: {}, Ref X/Y {}:{}/{}:{}'.format(n_im, refx1, refx2, refy1, refy2)
                cmin = np.nanpercentile(dvar, 1)
                cmax = np.nanpercentile(dvar, 99)
                plot_lib.make_im_png(dvar, pngfile, cmap, dvarname, cmin, cmax)
        if modelflag:
            model = inv_lib.get_model_cum(G, params_sorted)
            degfree=len(params_sorted)
        #
        del G
    else:
        if not sinflag: ## Linear function
            print('Calc velocity...')
            vconst[~bool_allnan], vel[~bool_allnan], G = inv_lib.calc_vel(cum_tmp_resh, dt_cum, return_G = True)
            if modelflag:
                model = inv_lib.get_model_cum(G, [vconst, vel])
                degfree = 2
            vel.tofile(velfile)
            vconst.tofile(vconstfile)
        else: ## Linear+sin function
            print('Calc velocity and annual components...')
            amp = np.zeros((length, width), dtype=np.float32)*np.nan
            delta_t = np.zeros((length, width), dtype=np.float32)*np.nan
            if store_to_results:
                ampfile = os.path.join(resultsdir, 'amp' + suffix_mask)
                dtfile = os.path.join(resultsdir, 'dt' + suffix_mask)
            else:
                ampfile = outfile+'.amp'+suffix_mask
                dtfile = outfile+'.dt'+suffix_mask
            if modelflag:
                coef_s = np.zeros((length, width), dtype=np.float32)*np.nan
                coef_c = np.zeros((length, width), dtype=np.float32) * np.nan
                vconst[~bool_allnan], vel[~bool_allnan], coef_s[~bool_allnan], coef_c[~bool_allnan], amp[~bool_allnan], delta_t[~bool_allnan], G = inv_lib.calc_velsin(
                    cum_tmp_resh, dt_cum, imdates[0], return_G = True)
                model = inv_lib.get_model_cum(G, [vconst, vel, coef_s, coef_c])
                degfree = 4
            else:
                vel[~bool_allnan], vconst[~bool_allnan], amp[~bool_allnan], delta_t[~bool_allnan] = inv_lib.calc_velsin(cum_tmp_resh, dt_cum, imdates[0])
            vel.tofile(velfile)
            amp.tofile(ampfile)
            delta_t.tofile(dtfile)

    if exportmodelfile:
        print('Exporting model time series to '+modh5file)
        modh5.create_dataset('cum_model', data=model, compression=compress)
        modh5.close()

    if modelflag:
        try:
            # let's also calculate RMSE using the model values:
            resid = cum_tmp - model
            rmse = np.zeros((length, width), dtype=np.float32) * np.nan
            #rmse = np.sqrt(np.nanmean(resid**2, axis=0))  # simple without degs of freedom
            count = np.sum(~np.isnan(resid), axis=0, dtype=np.float32)
            count[count == 0] = np.nan
            rmse = np.sqrt(np.nansum(resid ** 2, axis=0) / (count - degfree))
            if store_to_results:
                rmsefile = os.path.join(resultsdir, 'rmse' + suffix_mask)
            else:
                rmsefile = outfile+'.rmse'+suffix_mask
            rmse.tofile(rmsefile)
            del resid
        except:
            print('Some error creating RMSE')

    ### vstd
    if vstdflag:
        if store_to_results:
            vstdfile = os.path.join(resultsdir, 'vstd' + suffix_mask)
            bootvelfile = os.path.join(resultsdir, 'bootvel' + suffix_mask)
        else:
            vstdfile = outfile+'.vstd'+suffix_mask
            bootvelfile = outfile+'.bootvel'+suffix_mask
        vstd = np.zeros((length, width), dtype=np.float32)*np.nan
        bootvel = np.zeros((length, width), dtype=np.float32) * np.nan

        print('Calc vstd...')
        if offsetsflag or eqoffsetsflag:
            cum_tmp_resh = cum_tmp_resh - model.reshape(n_im, length*width)[:, ~bool_allnan.ravel()].transpose()

        vstd[~bool_allnan], bootvel[~bool_allnan] = inv_lib.calc_velstd_withnan(cum_tmp_resh, dt_cum)
        vstd.tofile(vstdfile)
        bootvel.tofile(bootvelfile)
        #
        #_cum = cum[:, rows[0]-row_ex1:rows[1]+row_ex2, :].reshape(n_im, lengththis+row_ex1+row_ex2, width)

        ### Calc STC
        #stc = inv_lib.calc_stc(_cum, gpu=gpu)[row_ex1:lengththis+row_ex1, :] ## original length
        #
        if stcflag:
            print('Calc stc...')
            # here, stc calc accepts nans and need 3D cube - so getting the original cum_tmp then
            if store_to_results:
                stcfile = os.path.join(resultsdir, 'stc' + suffix_mask)
            else:
                stcfile = outfile + '.stc' + suffix_mask
            # cum_tmp = cum_tmp.reshape(n_im, length, width) # this will not work!
            if offsetsflag or eqoffsetsflag:
                cum_tmp = cum_tmp - model  # or should this be transposed?
            stc = inv_lib.calc_stc(cum_tmp)

            openmode = 'w'
            with open(stcfile, openmode) as f:
                stc.tofile(f)

    #%% Make png if specified
    if pngflag:
        pngfile = velfile+'.png'
        title = 'Velocity (n_im: {}, Ref X/Y {}:{}/{}:{})'.format(n_im, refx1, refx2, refy1, refy2)
        cmin = np.nanpercentile(vel, 1)
        cmax = np.nanpercentile(vel, 99)
        plot_lib.make_im_png(vel, pngfile, cmap, title, cmin, cmax)
        # plot_lib.make_im_png(dvar, pngfile, cmap, dvarname, cmin, cmax)
        if sinflag:
            amp_max = np.nanpercentile(amp, 99)
            plot_lib.make_im_png(amp, ampfile+'.png', cmap_amp, title, vmax=amp_max)
            plot_lib.make_im_png(delta_t, dtfile+'.png', cmap_dt, title)

        if vstdflag:
            title = 'STD of velocity (mm/yr)'
            cmin = np.nanpercentile(vstd, 1)
            cmax = np.nanpercentile(vstd, 99)
            plot_lib.make_im_png(vstd, vstdfile+'.png', cmap_vstd, title, cmin, cmax)
            title = 'Bootstrapped velocity (mm/yr)'
            cmin = np.nanpercentile(bootvel, 1)
            cmax = np.nanpercentile(bootvel, 99)
            plot_lib.make_im_png(bootvel, bootvelfile + '.png', cmap, title, cmin, cmax)

        if stcflag:
            title = 'Spatio-temporal consistency (mm)'
            cmin = np.nanpercentile(stc, 1)
            cmax = np.nanpercentile(stc, 99)
            plot_lib.make_im_png(stc, stcfile + '.png', cmap_stc, title, cmin, cmax)

        if modelflag:
            title = 'RMSE of applied model (mm)'
            cmin = np.nanpercentile(rmse, 1)
            cmax = np.nanpercentile(rmse, 99)
            try:
                plot_lib.make_im_png(rmse, rmsefile + '.png', cmap_stc, title, cmin, cmax)
            except:
                print('error generating rmse preview')

    #%% Finish
    elapsed_time = time.time()-start
    hour = int(elapsed_time/3600)
    minite = int(np.mod((elapsed_time/60),60))
    sec = int(np.mod(elapsed_time,60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour,minite,sec))

    print('\n{} Successfully finished!!\n'.format(os.path.basename(argv[0])))
    print('Output: {}'.format(velfile), flush=True)
    if vstdflag:
        print('        {}'.format(vstdfile), flush=True)
    if stcflag:
        print('        {}'.format(stcfile), flush=True)
    if sinflag:
        print('        {}'.format(ampfile), flush=True)
        print('        {}'.format(dtfile), flush=True)
    print('')


#%% main
if __name__ == "__main__":
    sys.exit(main())
