#!/usr/bin/env python3
"""
v1.1 20241011 Milan Lazecky, Leeds Uni

========
Overview
========
This script outputs a standard NetCDF4 file using LiCSBAS results


=====
Usage
=====
LiCSBAS_out2nc.py [-i infile] [-o outfile] [-m yyyymmdd]
     [--ref_geo lon1/lon2/lat1/lat2] [--clip_geo lon1/lon2/lat1/lat2] [--alignsar] [--zarr] [--addtif test.tif]

 -i  Path to input cum file (Default: cum_filt.h5)
 -o  Output netCDF4 file (Default: output.nc)
 -m  Master (reference) date (Default: first date) - TODO: bperps are fixed-referred to the 1st date
 --alignsar, -A  Export complete cube as developed within AlignSAR (all amplitudes, coherences, calc D_A, mean amp, TODO: atmo_error based on step 16)
 --ref_geo  Reference area in geographical coordinates as: lon1/lon2/lat1/lat2
 --clip_geo  Area to clip in geographical coordinates as: lon1/lon2/lat1/lat2
 --compress, -C  use zlib compression (very small files but time series may take long to load in GIS)
 --postfilter will interpolate VEL only through empty areas and filter in space
 --apply_mask  Will apply mask to all relevant variables
 --extracol Will add extra layer from files in folder TS*/results - e.g. --extracol loop_ph_avg_abs
 --zarr  The output will be stored in the zarr format
 --addtif   Optionally you can directly include your external tif file as new data layer (it will get resampled using nearest neigbour interpolation)
"""
#%% Change log
'''
v1.2 2025+ ML
 - some fixes towards AlignSAR cube
v1.1 20241012+ ML
 - allowing extras for AlignSAR cube
v1.05 20240420 ML
 - fixed masking (apply_mask), improved metadata (to be improved further)
v1.0 20200901 Milan Lazecky, Uni of Leeds
 - Original implementation
'''

#%% Import
import getopt
import os
import re
import sys
import time
import numpy as np
import datetime as dt
import xarray as xr
import rioxarray
import subprocess as subp
from scipy.ndimage import gaussian_filter
from scipy import interpolate
import glob
import pandas as pd

class Usage(Exception):
    """Usage context manager"""
    def __init__(self, msg):
        self.msg = msg


def mm2rad(inmm, radar_freq=5.405e9, rad2mm=False):
    """Converts from mm to radians [or vice versa]
    """
    #speed_of_light = 299792458 #m/s
    speed_of_light = 299702547  #m/s ... in case of all-in-air 299792458 #m/s
    #radar_freq = 5.405e9  #for S1
    wavelength = speed_of_light/radar_freq #meter
    coef_r2m = wavelength/4/np.pi*1000 #rad -> mm,
    if rad2mm:
        # apologies for the inmm/outrad naming
        outrad = inmm*coef_r2m
    else:
        outrad = inmm/coef_r2m
    return outrad


def rad2mm(inrad, radar_freq=5.405e9):
    return mm2rad(inrad, radar_freq=radar_freq, rad2mm=True)


def grep1line(arg,filename):
    file = open(filename, "r")
    res=''
    for line in file:
        if re.search(arg, line):
            res=line
            break
    file.close()
    if res:
        res = res.split('\n')[0]
    return res


def datediff_pair(pair):
    """Input: list of pair string (e.g. '20230129_20230210'). will get number of days of Btemp
    """
    epoch1=pair.split('_')[0]
    epoch2=pair.split('_')[1]
    return datediff(epoch1, epoch2)


def datediff(epoch1, epoch2):
    date1 = dt.datetime.strptime(epoch1,'%Y%m%d').date()
    date2 = dt.datetime.strptime(epoch2,'%Y%m%d').date()
    return (date2-date1).days


#just an eye candy layer
def interp_and_smooth(da, sigma=0.8):
    dar = da.copy()
    array = np.ma.masked_invalid(dar.values)
    x = np.arange(0, array.shape[1])
    y = np.arange(0, array.shape[0])
    xx, yy = np.meshgrid(x, y)
    x1 = xx[~array.mask]
    y1 = yy[~array.mask]
    newarr = array[~array.mask]
    GD1 = interpolate.griddata((x1, y1), newarr.ravel(),(xx, yy),method='linear')
    #, fill_value=0)
    GD1 = np.array(GD1)
    GD1 = gaussian_filter(GD1, sigma=sigma)
    dar.values = GD1
    return dar


def loadall2cube(cumfile, extracols=['loop_ph_avg_abs']):
    cumdir = os.path.dirname(cumfile)
    cohfile = os.path.join(cumdir,'results/coh_avg')
    rmsfile = os.path.join(cumdir,'results/resid_rms')
    vstdfile = os.path.join(cumdir,'results/vstd')
    stcfile = os.path.join(cumdir,'results/stc')
    maskfile = os.path.join(cumdir,'results/mask')
    metafile = os.path.join(cumdir,'../../metadata.txt')
    #h5datafile = 'cum.h5'
    cum = xr.load_dataset(cumfile)
    
    sizex = len(cum.vel[0])
    sizey = len(cum.vel)
    
    lon = cum.corner_lon.values+cum.post_lon.values*np.arange(sizex)-0.5*float(cum.post_lon)
    lat = cum.corner_lat.values+cum.post_lat.values*np.arange(sizey)+0.5*float(cum.post_lat)  # maybe needed? yes! for gridline/AREA that is default in rasterio...
    
    time = np.array(([dt.datetime.strptime(str(imd), '%Y%m%d') for imd in cum.imdates.values]))
    
    velxr = xr.DataArray(cum.vel.values.reshape(sizey,sizex), coords=[lat, lon], dims=["lat", "lon"])
    #LiCSBAS uses 0 instead of nans...
    velxr = velxr.where(velxr!=0)
    velxr.attrs['unit'] = 'mm/year'
    #vinterceptxr = xr.DataArray(cum.vintercept.values.reshape(sizey,sizex), coords=[lat, lon], dims=["lat", "lon"])
    
    cumxr = xr.DataArray(cum.cum.values, coords=[time, lat, lon], dims=["time","lat", "lon"])
    cumxr.attrs['unit'] = 'mm'
    #bperpxr = xr.DataArray(cum.bperp.values, coords=[time], dims=["time"])
    
    cube = xr.Dataset()
    cube['cum'] = cumxr
    cube['vel'] = velxr
    #cube['vintercept'] = vinterceptxr
    try:
        cube['bperp'] = xr.DataArray(cum.bperp.values, coords=[time], dims=["time"])
        cube['bperp'] = cube.bperp.where(cube.bperp!=0)
        # re-ref it to the first date
        if np.isnan(cube['bperp'][0]):
            firstbperp = 0
        else:
            firstbperp = cube['bperp'][0]
        cube['bperp'] = cube['bperp'] - firstbperp
        cube['bperp'] = cube.bperp.astype(np.float32)
        cube.bperp.attrs['unit'] = 'm'
    except:
        print('some error loading bperp info')
    
    #if 'mask' in cum:
    #    # means this is filtered version, i.e. cum_filt.h5
    cube.attrs['filtered_version'] = 'mask' in cum
    
    #add coh_avg resid_rms vstd
    if os.path.exists(cohfile):
        infile = np.fromfile(cohfile, 'float32')
        cohxr = xr.DataArray(infile.reshape(sizey,sizex), coords=[lat, lon], dims=["lat", "lon"])
        cube['coh'] = cohxr
        cube.coh.attrs['unit']='unitless'
    else: print('No coh_avg file detected, skipping')
    if os.path.exists(rmsfile):
        infile = np.fromfile(rmsfile, 'float32')
        rmsxr = xr.DataArray(infile.reshape(sizey,sizex), coords=[lat, lon], dims=["lat", "lon"])
        rmsxr.attrs['unit'] = 'mm'
        cube['rms'] = rmsxr
    else: print('No RMS file detected, skipping')
    try:
        for e in extracols:
            efile=os.path.join(cumdir,'results',e)
            if os.path.exists(efile):
                infile = np.fromfile(efile, 'float32')   # should be always float. but we can check with os.stat('loop_ph_avg_abs').st_size
                exr = xr.DataArray(infile.reshape(sizey, sizex), coords=[lat, lon], dims=["lat", "lon"])
                #rmsxr.attrs['unit'] = 'mm'
                cube[e] = exr
            else:
                print('No '+e+' file detected, skipping')
    except:
        print('debug - extra layers not included')
    if os.path.exists(vstdfile):
        infile = np.fromfile(vstdfile, 'float32')
        vstdxr = xr.DataArray(infile.reshape(sizey,sizex), coords=[lat, lon], dims=["lat", "lon"])
        vstdxr.attrs['unit'] = 'mm/year'
        cube['vstd'] = vstdxr
    else: print('No vstd file detected, skipping')
    if os.path.exists(stcfile):
        infile = np.fromfile(stcfile, 'float32')
        stcxr = xr.DataArray(infile.reshape(sizey,sizex), coords=[lat, lon], dims=["lat", "lon"])
        stcxr.attrs['unit'] = 'mm'
        cube['stc'] = stcxr
    else: print('No stc file detected, skipping')
    if os.path.exists(maskfile):
        infile = np.fromfile(maskfile, 'float32')
        #infile = np.nan_to_num(infile,0).astype(int)  # change nans to 0
        infile = np.nan_to_num(infile,0).astype(np.int8)  # change nans to 0
        maskxr = xr.DataArray(infile.reshape(sizey,sizex), coords=[lat, lon], dims=["lat", "lon"])
        maskxr.attrs['unit'] = 'unitless'
        cube['mask'] = maskxr
    else: print('No mask file detected, skipping')
    # add inc_angle
    if os.path.exists(metafile):
        #a = subp.run(['grep','inc_angle', metafile], stdout=subp.PIPE)
        #inc_angle = float(a.stdout.decode('utf-8').split('=')[1])
        inc_angle = float(grep1line('inc_angle',metafile).split('=')[1])
        cube.attrs['inc_angle'] = inc_angle
    else: print('')#'warning, metadata file not found. using general inc angle value')
        #inc_angle = 39
    
    #cube['bperp'] = bperpxr
    #cube[]
    cube.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True)
    cube.rio.write_crs("EPSG:4326", inplace=True)
    #cube = cube.sortby(['time','lon','lat']) # 2025/03: not really right as lat should be opposite-signed..
    return cube

#not in use now
def maskit(clipped, cohthres = 0.62, rmsthres = 5, vstdthres = 0.3):
    da = clipped.copy()
    out = da.where(clipped.coh>=cohthres) \
    .where(np.abs(clipped.rms)<=rmsthres) \
    .where(np.abs(clipped.vstd)<=vstdthres)
    return out


def toalignsar(tsdir, cube, filestoadd = []):  # ncfile, outncfile, filestoadd = []):
    '''Will add some extras to the ncfile - need to have workdir with GEOC.MLI loaded - and for now, the multilook should be only ML = 1!
    filestoadd should be a list of tif files (with full path) that should be imported'''
    docoh = True
    coh_in_4d = False
    doatmo = True
    gacosremove = False
    # first fix vel as we load it from cum_filt!
    try:
        velfile = os.path.join(tsdir, 'results', 'vel')
        vel = np.fromfile(velfile, np.float32)
        vel = vel.reshape(cube.vel.shape)
        #vel = np.flipud(vel)
        cube.vel.values = vel
    except:
        print('some error loading vel')
    #cube=xr.open_dataset(ncfile) # only opening, not loading to memory
    workdir=os.path.dirname(tsdir)
    mldircode=tsdir.split('/')[-1].split('_')[-1]
    geocmldir=os.path.join(workdir, mldircode)
    gacosdir = os.path.join(workdir, 'GACOS')
    try:
        ml = int(mldircode[6:].split('G')[0].split('m')[0].split('c')[0])
        if ml>1:
            print('WARNING, only ML1 will work ok for amplitudes (for now) - you used multilook '+str(ml)+'. Skipping amplitudes.')
            doamp = False
        else:
            doamp = True
    except:
        print('WARNING, could not identify ml factor from the folder name. Assuming not equal 1 == skipping amplitudes')
        doamp = False
    if not os.path.exists(geocmldir):
        docoh = False
    mlidir = os.path.join(workdir, 'GEOC.MLI')
    if not os.path.exists(mlidir):
        doamp = False
    #
    #
    #
    if doamp:
        #cube = xr.open_dataset(ncfile)
        var = cube['cum'] # will do 3D set
        new_var = xr.DataArray(data=np.zeros((var.shape)).astype(np.float32), dims=var.dims)
        cube = cube.assign({'amplitude': new_var.copy(deep=True)})
        new_var = None
        print('Importing amplitudes')
        cube = import_tifs2cube_simple(mlidir, cube, searchstring='/*geo.mli.tif', varname='amplitude', thirddim='time',
                                apply_func=np.sqrt)
        cube['amplitude']=cube['amplitude'].where(cube['amplitude']!=0)
        print('calculating mean amp and amp stab index')
        cube['amp_mean']=cube.amplitude.mean(dim='time')
        cube['amp_std']=cube.amplitude.std(dim='time')
        #cube['amp_dispersion_index']=(cube.amp_std**2)/cube['amp_mean']
        #cube['amp_dispersion_index'] = cube['amp_std'] / cube['amp_mean']
        #cube['amp_stability_index'] = 1 - cube['amp_mean'] / (cube.amp_std ** 2)  # from 0-1, close to 0 = very stable
        cube['amp_stability_index'] = 1 - (cube['amp_std'] / cube['amp_mean'])  # from 0-1, close to 0 = very stable
        cube['amp_stability_index'].values[cube['amp_stability_index'] <= 0] = 0.00001
    if docoh:
        # will set only 12 and 24 day cohs for now
        btemps = [12, 24]
        var = cube['cum'] # will do 3D set
        if coh_in_4d:
            new_var = var.expand_dims({'btemp':btemps}).astype(np.float32) * np.nan
            cube = cube.assign({'spatial_coherence': new_var.copy(deep=True)})
            new_var = None
        else:
            new_var = xr.DataArray(data=np.zeros((var.shape)).astype(np.float32), dims=var.dims)
            for btemp in btemps:
                cube = cube.assign({'spatial_coherence_'+str(btemp): new_var.copy(deep=True)})
                cube['spatial_coherence_'+str(btemp)].attrs['description']='Spatial coherence of Btemp = '+str(btemp)+' days estimated per epoch.'
            new_var = None
        #
        t=cube.indexes['time']
        searchstring='/*/*.cc'
        ccs = glob.glob(geocmldir+searchstring)
        print('Importing spatial coherences for following Btemp [days]:')
        print(btemps)
        print('')
        for cc in ccs:
            pair = os.path.basename(cc).split('.')[0]
            btemp = datediff_pair(pair)
            if not btemp in btemps:
                continue
            eintime = False
            for epochstr in pair.split('_'):
                epochdt = pd.Timestamp(epochstr)
                if epochdt in t:
                    eintime = True
            if not eintime:
                continue
            # at least one epoch is within the cc here, loading
            coh = np.fromfile(cc, np.uint8)
            coh = coh.reshape(cube.vel.shape)
            #coh = (np.flipud(coh) / 255).astype(np.float32)
            coh = (coh / 255).astype(np.float32)
            coh[coh == 0] = np.nan
            for epochstr in pair.split('_'):
                #epochdt = pd.Timestamp(pair.split('_')[1])
                epochdt = pd.Timestamp(epochstr)
                if not epochdt in t:
                    continue
                i = t.get_loc(epochdt)
                cohcount = coh*0+1
                if coh_in_4d:
                    j = cube.indexes['btemp'].get_loc(btemp)
                    prevcoh = cube['spatial_coherence'].isel(time=i, btemp=j).values
                    prevcohcount = prevcoh*0+1
                    totalcount = cohcount+prevcohcount
                    cube['spatial_coherence'].isel(time=i, btemp=j)[:] = (coh+prevcoh)/totalcount
                else:
                    prevcoh = cube['spatial_coherence_'+str(btemp)].isel(time=i).values
                    prevcohcount = prevcoh * 0 + 1
                    prevcohcount[np.isnan(prevcohcount)]=0
                    totalcount = cohcount + prevcohcount
                    #cube['spatial_coherence_'+str(btemp)].isel(time=i)[:] = coh
                    cube['spatial_coherence_' + str(btemp)].isel(time=i)[:] = (coh+prevcoh)/totalcount
    #cube.to_netcdf(outnc, mode='w', unlimited_dims=['time'])
    #del cube # clean memory
    if doatmo:
        if not os.path.exists(gacosdir):
            print('WARNING, no GACOS directory found - will store only results of filtering as atmo var')
        else:
            var = cube['cum'] # will do 3D set
            new_var = xr.DataArray(data=np.zeros((var.shape)).astype(np.float32), dims=var.dims)
            varname = 'atmosphere_external'
            cube = cube.assign({varname: new_var.copy(deep=True)})
            new_var =None
            print('Importing GACOS as atmosphere based on external model')
            cube = import_tifs2cube_simple(gacosdir, cube, searchstring='/*.sltd.geo.tif', varname=varname, thirddim='time',
                                    apply_func=rad2mm)
            cube[varname]=cube[varname].where(cube[varname]!=0)
            # w.r.t. ref point 
            cube[varname]=cube[varname]-cube[varname].sel(lon=cube.ref_lon, lat=cube.ref_lat, method='nearest')
            cube[varname] = cube[varname] - cube[varname][0]  # must be referred to the reference epoch (first epoch)
            # change sign as sltd was radians of delay where POSITIVE means BIGGER DELAY (opposite to SLC phase)
            # and after inversion, the increments [mm] are NEGATIVE for BIGGER DELAY (e.g. subsidence)
            cube[varname] = cube[varname]*(-1)
        print('Getting residuals from filtering assuming atmo-correction')
        cumfile = os.path.join(tsdir, 'cum.h5')
        cumnf = xr.open_dataset(cumfile)
        varname = 'atmosphere_resid_filter'
        var = cube['cum'] # will do 3D set
        new_var = xr.DataArray(data=np.zeros((var.shape)).astype(np.float32), dims=var.dims)
        cube = cube.assign({varname: new_var.copy(deep=True)})
        new_var = None
        cube[varname].values = cumnf['cum'].values - cube['cum'].values
        #for i in range(len(cube.time)):
        #    cube[varname].isel(time=i)[:] = cube['cum'][i].values - cumnf.cum[i].values #np.flipud(cumnf.cum[i].values) # filt minus not filt
        # to same ref point (might have changed)
        cube[varname]=cube[varname]-cube[varname].sel(lon=cube.ref_lon, lat=cube.ref_lat, method='nearest')
        # 2024-10-14: after AlignSAR meeting: we should actually keep cum being unfiltered... thus changing here (lazy):
        cube['cum'] = cube['cum'] + cube[varname]
        # 2025-03: let's remove also GACOS corrections (?) -- but then we should store velocity etc. of such non-corrected data!
        if gacosremove:
            if 'atmosphere_external' in cube:
                cube['cum'] = cube['cum'] - cube['atmosphere_external']
        #    cube['atmosphere']=cube['atmosphere_external']+cube['filter_APS']
        #    cube=cube.drop_vars('atmosphere_external')
        #else:
        #    cube=cube.rename({'filter_APS':'atmosphere'})
        # also adding height
        cube['DEM'] = cube.vel.copy()
        cube['DEM'].values = cumnf.hgt.values #np.flipud(cumnf.hgt.values)
        cube['DEM'].attrs['unit']='m'
        cube['DEM']=cube['DEM'].where(cube['DEM'] != 0)
    #
    if filestoadd:
        for tif in filestoadd:
            try:
                data = rioxarray.open_rasterio(tif)
                data = data.squeeze('band')
                data = data.drop('band')
                data = data.rename({'x':'lon', 'y':'lat'})
                dtype = str(data.dtype)
                try:
                    fillvalue = data.attrs['_FillValue']
                except:
                    if 'int' in dtype:
                        fillvalue = 0
                    else:
                        fillvalue = np.nan
            except:
                print('ERROR loading tif '+tif)
                continue
            #if data.shape != cube.vel.shape:
            data = data.interp_like(cube.vel, method='nearest', kwargs={'fill_value':fillvalue})
            data=data.astype(dtype)
            varname = os.path.basename(tif).split('.')[0]
            cube[varname] = cube.vel.copy()
            cube[varname].values = data.values
            cube[varname].attrs = {'grid_mapping': 'spatial_ref'}
    #
    print('Converting to the AlignSAR standard datacube')
    cube = alignsar_rename(cube)
    cube = alignsar_global_metadata(cube)
    #cube.to_netcdf(outncfile)  # uncompressed
    return cube


def alignsar_global_metadata(cube):
    print('WARNING, global metadata are set in default values, valid for the AlignSAR InSAR TS demo datacube - please change manually')
    print('(especially things such as incidence angle, frame time etc)')
    cube.attrs['filtered_version'] = 0  # this is because of the workaround we did before...
    resolution = float(cube.lon[2] - cube.lon[1])
    frtime = '05:11:50'
    #
    cube.attrs['processing_level'] = 'InSAR'
    cube.attrs['date_created'] = str(dt.datetime.now())
    cube.attrs['creator_name'] = 'Milan Lazecky'
    cube.attrs['creator_email'] = 'M.Lazecky@leeds.ac.uk'
    cube.attrs['creator_url'] = 'https://comet.nerc.ac.uk/COMET-LiCS-portal'
    cube.attrs['institution'] = 'University of Leeds'
    cube.attrs['project'] = 'AlignSAR'
    cube.attrs['publisher_name'] = cube.attrs['creator_name']  # 'N/A'
    cube.attrs['publisher_email'] = cube.attrs['creator_email']  # 'N/A'
    cube.attrs['publisher_url'] = cube.attrs['creator_url']  # 'N/A'
    cube.attrs['geospatial_lat_min'] = float(cube.lat.min())
    cube.attrs['geospatial_lat_max'] = float(cube.lat.max())
    cube.attrs['geospatial_lon_min'] = float(cube.lon.min())
    cube.attrs['geospatial_lon_max'] = float(cube.lon.max())
    cube.attrs['sar_date_time'] = 'N/A'  # not for multitemporal datacube really..
    cube.attrs['sar_reference_date_time'] = str(cube.time[0].values).split('T')[0] + 'T' + frtime
    cube.attrs['sar_instrument_mode'] = 'TOPS'
    cube.attrs['sar_looks_range'] = round(resolution * 111111 / 2.3)  # 7 originally
    cube.attrs['sar_looks_azimuth'] = round(resolution * 111111 / 14)  # 2 originally, but then again..
    cube.attrs['sar_pixel_spacing_azimuth'] = 13.95
    cube.attrs['sar_processing_software'] = 'LiCSAR, LiCSBAS'
    cube.attrs['sar_absolute_orbit'] = '-'
    cube.attrs['sar_relative_orbit'] = '22D'
    cube.attrs['sar_view_azimuth'] = -169.9
    cube.attrs['sar_view_incidence_angle'] = 33.8
    cube.attrs['sar_slc_crop'] = '-'
    return cube


def alignsar_rename(cube):
    def _updatecube(cube, varname, unittext = None, desctext = None, newvarname = None):
        #print(varname)
        if varname in cube:
            if unittext:
                cube[varname].attrs['unit'] = unittext
            if desctext:
                cube[varname].attrs['description'] = desctext
            # AlignSAR other local params:
            cube[varname].attrs['range'] = '('+str(np.nanmin(cube[varname]))+', '+str(np.nanmax(cube[varname]))+')'
            cube[varname].attrs['format'] = str(cube[varname].dtype)
            if newvarname:
                cube = cube.rename_vars({varname:newvarname})
        else:
            print('WARNING, data var '+varname+' does not exist in the cube. Continuing')
        return cube
    #cube = _updatecube(cube, varname, newvarname = None,
    #            unittext = None,
    #            desctext = None)
    cube = _updatecube(cube, 'cum', newvarname = 'cum_displacement',
                unittext = 'mm',
                desctext = 'Inverted cumulative displacements from unwrapped interferograms')
    cube = _updatecube(cube, 'vel', newvarname = 'linear_velocity',
                unittext = 'mm/year',
                desctext = 'Linear displacement trend estimated from the cumulative displacements')
    if 'bperp' in cube:
        cube.bperp.attrs['description']='Perpendicular baseline'
    cube = _updatecube(cube, 'coh', newvarname = 'mean_coherence',
                unittext = 'unitless',
                desctext = 'Mean spatial coherence of the dataset')
    cube = _updatecube(cube, 'rms', newvarname = 'residuals_rms',
                unittext = 'mm',
                desctext = 'RMSE from residuals in the small baseline inversion')
    cube = _updatecube(cube, 'loop_ph_avg_abs', newvarname = 'mean_abs_loop_phase_closure',
                unittext = 'rad',
                desctext = 'Mean absolute value of phase loop closure residual')
    cube = _updatecube(cube, 'vstd', newvarname = 'linear_velocity_std',
                unittext = 'mm/year',
                desctext = 'RMSE of the estimated linear velocity')
    cube = _updatecube(cube, 'stc', newvarname = 'spatiotemporal_consistency',
                unittext = 'mm',
                desctext = 'Spatio-temporal consistency as minimum RMSE of double differences of time series in space and time between the pixel and adjacent pixels')
    #cube = _updatecube(cube, 'amp_dispersion_index',
    #            unittext = 'unitless',
    #            desctext = 'Amplitude dispersion index calculated as variance/mean of the amplitudes')
    cube = _updatecube(cube, 'amp_stability_index',
                unittext = 'unitless',
                desctext = 'Amplitude stability calculated as 1 - mean/stddev of the amplitudes (close to 1 = most stable)')
    # tricky one - spatial coherence if in 4D cube
    cube = _updatecube(cube, 'spatial_coherence',
                unittext = 'unitless',
                desctext = 'Spatial coherence of given Btemp where time represents second epoch of the interferometric pair')
    cube = _updatecube(cube, 'atmosphere_external',
                unittext = 'mm',
                desctext = 'Errors due to atmosphere estimated from GACOS (double-difference to keep consistent datacube)')
    cube = _updatecube(cube, 'atmosphere_resid_filter',
                unittext = 'mm',
                desctext = 'Errors due to residual atmosphere (after applying GACOS corrections) estimated from spatio-temporal filtering')
    cube = _updatecube(cube, 'DEM',
                unittext = 'm',
                desctext = 'Height map extracted from Copernicus DEM')
    return cube


def import_tifs2cube_simple(tifspath, cube, searchstring='/*geo.mli.tif', varname = 'amplitude', thirddim = 'time', apply_func = None):
    '''e.g. for amplitude from mlis, use apply_func = np.sqrt
    Note this function is simplified and loads everything to memory! see licsar_extra/lics_tstools for improved way
    finally, the varname must exist!'''
    t=cube.indexes['time']
    tifs=glob.glob(tifspath+searchstring)
    for tif in tifs:
        fname = os.path.basename(tif)
        epoch=fname.split('.')[0]
        if '_' in epoch:  # in case of ifgs, we set this to the later date
            epoch = epoch.split('_')[-1]
        epochdt = pd.Timestamp(epoch)
        if not epochdt in t:
            continue
        i = t.get_loc(epochdt)
        try:
            data = rioxarray.open_rasterio(tif)
            data = data.squeeze('band')
            data = data.drop_vars('band')
            data = data.rename({'x':'lon', 'y':'lat'})
        except:
            print('ERROR loading tif for epoch '+epoch)
            continue
        if data.shape != cube.vel.shape:
            data = data.interp_like(cube.vel, method='linear') # WARNING: method linear is ok for all but not phase!
            data = data.values
        else:
            data = data.values #np.flipud(data.values) # to np array..
        if apply_func:
            data = apply_func(data)
        cube[varname].isel(time=i)[:] = data
    return cube


#%% Main
def main(argv=None):
   
    #%% Check argv
    if argv == None:
        argv = sys.argv
        
    start = time.time()
    ver=1.1; date=20241011; author="M.Lazecky"
    print("\n{} ver{} {} {}".format(os.path.basename(argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(argv[0]), ' '.join(argv[1:])), flush=True)


    #%% Set default
    cumfile = 'cum.h5'
    outfile = 'output.nc'
    imd_m = []
    #refarea = []
    refarea_geo = []
    #maskfile = []
    apply_mask = False
    cliparea_geo = []
    compress = False
    postfilter = False
    alignsar = False
    centre_refx, centre_refy = np.nan, np.nan
    extracols = ['loop_ph_avg_abs']
    filestoadd = []
    tozarr =False

    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hi:o:m:r:CA", ["help", "alignsar", "zarr", "addtif=", "extracol=", "compress","postfilter","clip_geo=", "ref_geo=", "apply_mask", "mask="])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                return 0
            elif o == '-i':
                cumfile = a
            elif o == '-o':
                outfile = a
            elif o == '--extracol':
                extracols.append(a)
            elif o == '--addtif':
                print('Final datacube will include imported '+a)
                filestoadd.append(a)
            elif o == '-m':
                imd_m = a
            elif (o == '-C') or (o=='--compress'):
                compress = True
                print('will use zlib compression')
            elif (o == 'postfilter'):
                postfilter = True
                print('vel_filt will be created including interpolation over masked area')
            elif o == '-r':
                refarea = a
                print('ref area in radar coords not implemented yet')
            elif o == '--clip_geo':
                cliparea_geo = a
                minclipx, maxclipx, minclipy, maxclipy = cliparea_geo.split('/')
                minclipx, maxclipx, minclipy, maxclipy = float(minclipx), float(maxclipx), float(minclipy), float(maxclipy)
            elif o == '--ref_geo':
                refarea_geo = a
                minrefx, maxrefx, minrefy, maxrefy = refarea_geo.split('/')
                minrefx, maxrefx, minrefy, maxrefy = float(minrefx), float(maxrefx), float(minrefy), float(maxrefy)
                centre_refx, centre_refy = (minrefx+maxrefx)/2, (minrefy+maxrefy)/2
            #elif o == '--mask':
            #    maskfile = a
            elif o == '--apply_mask':
                apply_mask = True
            elif (o == '-A') or (o=='--alignsar'):
                alignsar = True
                print('outputting as the AlignSAR InSAR TS cube')
            elif o == '--zarr':
                tozarr = True

        if not os.path.exists(cumfile):
            raise Usage('No {} exists! Use -i option.'.format(cumfile))

    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2
    
    if alignsar:
        if os.path.basename(cumfile) == 'cum_filt.h5':
            print('WARNING, we will indeed import cum_filt datacube as requested but for AlignSAR, the output cum will be the unfiltered version')
        cumfile = cumfile.replace('cum.h5','cum_filt.h5') # just adjusting to ensure all signatures in the input h5 (but output will be from unfiltered version!)
        if not 'loop_ph_avg_abs' in extracols:
            extracols.append('loop_ph_avg_abs')

    if tozarr:
        import zarr # just to check for its existence before the whole processing

    cube = loadall2cube(cumfile, extracols = extracols)
    
    if apply_mask:
        davars = list(cube.data_vars)
        davars.remove('mask')
        for vbl in davars:
            if 'lat' in cube[vbl].coords:
                cube[vbl] = cube[vbl].where(cube.mask==1)
    
    #reference cum to time (first date will be 0)
    if not imd_m:
        imd_m = cube.time.isel(time=0).values.astype('str').split('T')[0]
    
    cube['cum'] = cube['cum'] - cube['cum'].sel(time=imd_m)
    
    #reference it
    if refarea_geo:
        #ref = cube.rio.clip_box(minrefx, minrefy, maxrefx, maxrefy)
        ref = cube.sel(lon=slice(minrefx, maxrefx), lat=slice(maxrefy,minrefy))
        if len(ref.vel) == 0:
            print('warning, no points in the reference area - will export without referencing')
        else:
            refcoh = ref.where(ref.coh >0.6)
            if refcoh.vel.count() < 2:
                print('warning, the ref area has low coherence! continuing anyway')
                refcoh = ref
            #for v in refcoh.data_vars.variables:
            #for v in ['cum', 'vel', 'vel_filt']:
            for v in ['cum', 'vel']:
                cube[v] = cube[v] - refcoh[v].median(["lat", "lon"])
    else:
        # just load default ref point
        #if np.isnan(centre_refx):
        if cube.attrs['filtered_version']:
            inref = '16ref'
        else:
            inref = '13ref'
        cumdir = os.path.dirname(cumfile)
        refkml = os.path.join(cumdir,'info',inref+'.kml')
        refcoords = grep1line('<coordinates>',refkml)
        refcoords = refcoords.split('>')[1].split('<')[0].split(',')
        centre_refx, centre_refy = float(refcoords[0]), float(refcoords[1])
    
    cube.attrs['ref_lon'] = centre_refx
    cube.attrs['ref_lat'] = centre_refy
    # netcdf does not support boolean, so:
    cube.attrs['filtered_version'] = cube.attrs['filtered_version']*1
    
    # alignsar (RAM-demanding version):
    if alignsar:
        cube = toalignsar(os.path.dirname(cumfile), cube, filestoadd = filestoadd)
    
    #only now will clip - this way the reference area can be outside the clip, if needed
    if cliparea_geo:
        cube = cube.sel(lon=slice(minclipx, maxclipx), lat=slice(maxclipy, minclipy))
    
    if postfilter:
        #do filtered (it is nice)
        cube['vel_filt'] = interp_and_smooth(cube['vel'], 0.5)
    
    
    #masked = maskit(clipped)
    #masked['vel_filt'] = clipped['vel_filt']
    #masked.to_netcdf(outfile)
    #just to make sure it is written..
    #check if it does not invert data!
    
    # strange error regarding the grid mapping. seen only in alignsar way. solving:
    for var in list(cube.data_vars):
        if 'grid_mapping' in cube[var].attrs:
            del cube[var].attrs['grid_mapping']
    
    cube.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True)
    cube.rio.write_crs("EPSG:4326", inplace=True)

    if not tozarr:
        if (compress and not alignsar):
            if postfilter:
                encode = {'cum': {'zlib': True, 'complevel': 9}, 'vel': {'zlib': True, 'complevel': 9},
                'coh': {'zlib': True, 'complevel': 9}, 'rms': {'zlib': True, 'complevel': 9},
                'stc': {'zlib': True, 'complevel': 9}, 'vel_filt': {'zlib': True, 'complevel': 9},
                'time': {'dtype': 'i4'}}
            else:
                encode = {'cum': {'zlib': True, 'complevel': 9}, 'vel': {'zlib': True, 'complevel': 9},
                'coh': {'zlib': True, 'complevel': 9}, 'rms': {'zlib': True, 'complevel': 9},
                'stc': {'zlib': True, 'complevel': 9},
                'time': {'dtype': 'i4'}}
        else:
            # if not compress then at least encode only time to keep standard NetCDF:
            encode = {'time': {'dtype': 'i4'}}

        cube.to_netcdf(outfile, encoding=encode)
        if alignsar:
            print('Trying to compress additionally')
            cmd = 'nccopy -d 5 '+outfile+' '+outfile+'.tmp.nc'
            os.system(cmd)
            if os.path.exists(outfile+'.tmp.nc'):
                os.system('mv '+outfile+'.tmp.nc '+outfile)
    else:
        # exporting to zarr directly, just as is (seems reasonable. pity the 'append_dim' does not work, perhaps due to the mixed data, some having 'time' and some not?
        #try:
        cube.to_zarr(outfile)
        #except:
        #    print('error storing to zarr - ')
        
    #if alignsar:
    #    # will just load it from stored since we will use the non-load approach for amps/cohs to save memory
    #    del cube
    #    cube = toalignsar(os.path.dirname(cumfile), outfile, outfile+'.tmp.nc')
    #    if cliparea_geo:
    #        cube = cube.sel(lon=slice(minclipx, maxclipx), lat=slice(minclipy, maxclipy))
    #
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
