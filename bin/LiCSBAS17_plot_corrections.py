#!/usr/bin/env python3

"""
2025-01-22 Muhammet Nergizci, University of Leeds

========
Overview
========
This script generates a multi-panel PyGMT figure summarizing all correction terms
(tide, ionospheric, tropospheric [GACOS], plate motion) applied in COMET-LiCSBAS
processing workflows. It overlays the results on a DEM basemap.

===== 
Usage 
=====
3.plot_correction_LiCSBAS.py -t <TS_GEOC_dir> [-f <frame_ID>] [-o <output_file>]

Arguments:
 -t    Path to TS_GEOC directory with saved tide, iono, and gacos corrections
 -i    cum(_filt).h5 file (default cum.h5)
 -o    Output PNG file name (default: <frame>.corrections.png)
 -r   Reference area in lon/lat format (e.g., 30:40/50:60) to subtract mean value
--sbovl Run in sbovl mode to preserve absolute velocity (azimuth instead of LOS)
"""

#%% Imports
import os
import re
import sys
import time
import getopt
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cmcrameri.cm as cmc
import pygmt

import LiCSBAS_plot_lib as plot_lib
import LiCSBAS_io_lib as io_lib
import lics_tstools as lts
from lics_unwrap import *

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def create_geogrid(data_array, corner_lon, corner_lat, post_lon, post_lat):
    """Create georeferenced xarray DataArray for PyGMT plotting."""
    ny, nx = data_array.shape
    lons = corner_lon + np.arange(nx) * post_lon
    lats = corner_lat + np.arange(ny) * post_lat
    if post_lat < 0:
        lats = lats[::-1]
        data_array = data_array[::-1, :]
    return xr.DataArray(data_array, coords={"lat": lats, "lon": lons}, dims=["lat", "lon"], name="z")

def main(argv=None):
    if argv is None:
        argv = sys.argv
    
    start_time = time.time()

    # Default values
    tsdir = ''
    frame = None
    output_file = None
    sbovl = False
    keep_absolute = False
    refarea = []
    cumfile = 'cum.h5'

    # Argument parsing
    try:
        opts, _ = getopt.getopt(argv[1:], "ht:i:o:r:", ["help", "sbovl"])
        for opt, arg in opts:
            if opt in ('-h', '--help'):
                print(__doc__)
                return 0
            elif opt == '-t':
                tsdir = arg
            elif opt == '-i':
                cumfile = arg
            elif opt == '-o':
                output_file = arg
            elif opt == '-r':
                refarea = arg
            elif opt == '--sbovl':
                sbovl = True
                # keep_absolute = True

        if not tsdir:
            raise Usage("No TS_GEOC directory provided. Use -t option.")
        if not os.path.exists(tsdir):
            raise Usage(f"Directory {tsdir} does not exist.")
        if not os.path.exists(os.path.join(tsdir, cumfile)):
            raise Usage(f"File {cumfile} does not exist in {tsdir}.")

    except Usage as err:
        print(f"\nERROR: {err.msg}\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2

    # File paths
    workdir = os.getcwd()
    if frame is None:
        frame = os.path.basename(workdir)
    tide_file = os.path.join(workdir, 'tide.vel')
    iono_file = os.path.join(workdir, 'iono.vel')
    gacos_file = os.path.join(workdir, 'sltd.vel')
    vel_file = os.path.join(workdir, f'{frame}.vel_filt.mskd.eurasia.geo.tif')
    cum_file = os.path.join(tsdir, cumfile)

    if sbovl:
        corrections = {
            "tide": {
                "fname": tide_file,
                "field": "GEOC.EPOCHS",
                "input_tif": "tide.geo.azi.tif",
                "scale": 1000,
            },
            "iono": {
                "fname": iono_file,
                "field": "GEOC.EPOCHS",
                "input_tif": "geo.iono.code.sTECA.tif",
                "scale": 14000,
            },
        }
    else:
         corrections = {
            "tide": {
                "fname": tide_file,
                "field": "GEOC.EPOCHS",
                "input_tif": "tide.geo.tif",
                "scale": 1000,
            },
            "iono": {
                "fname": iono_file,
                "field": "GEOC.EPOCHS",
                "input_tif": "geo.iono.code.tif",
                "scale": 55.465 / (4 * np.pi),
            },
            "sltd": {
                "fname": gacos_file,
                "field": "GACOS",
                "input_tif": "sltd.geo.tif",
                "scale": -55.465 / (4 * np.pi),
            },
        }
    # breakpoint()        
    # Load cum.h5 once to get shape if needed
    cum = xr.load_dataset(cum_file)
    shape = cum.vel.shape

    # Try correction and velocity generation
    for datavar, params in corrections.items():
        fname = params["fname"]

        if not os.path.exists(fname):
            print(f"[INFO] Attempting LiCSBAS_cum2vel for {datavar}...")
            result = os.system(f'LiCSBAS_cum2vel.py --datavar {datavar} -i "{cum_file}" -o {datavar}')
            
            # Check if the output .vel file was actually created
            if not os.path.exists(fname):
                print(f"[WARN] {fname} not created, applying correction via lts for {datavar}...")

                # Apply correction
                lts.correct_cum_from_tifs(
                    cum_file,
                    params["field"],
                    params["input_tif"],
                    params["scale"],
                    directcorrect=False,
                    sbovl=False
                )

                # Retry LiCSBAS_cum2vel after correction
                print(f"[INFO] Retrying LiCSBAS_cum2vel for {datavar}...")
                os.system(f'LiCSBAS_cum2vel.py --datavar {datavar} -i "{cum_file}" -o {datavar}')

            else:
                print(f"[OK] {fname} successfully created on first attempt.")
        else:
            print(f"[SKIP] {fname} already exists.")
    # breakpoint()
    # Load data
    tide = np.fromfile(tide_file, dtype='float32').reshape(shape)
    iono = np.fromfile(iono_file, dtype='float32').reshape(shape)
    if not sbovl:
        gacos = np.fromfile(gacos_file, dtype='float32').reshape(shape)
    vlos = lts.load_tif2xr(vel_file)
    vlos_eurasia = lts.generate_pmm_velocity(frame, 'Eurasia', 'GEOC', azi=sbovl).interp_like(vlos)

    # Reference area subtraction if needed
    if not keep_absolute:
        refx1, refx2, refy1, refy2 = map(int, re.split('[:/]', cum.refarea.item()))
        if refarea:
            refx1, refx2, refy1, refy2 = map(int, re.split('[:/]', refarea))
        print(f'ref_area: {refx1}:{refx2}/{refy1}:{refy2}')
        mean_val = np.nanmean(vlos_eurasia.values[refy1:refy2, refx1:refx2])
        mean_val = np.nan_to_num(mean_val, nan=0.0) #in case of all NaNs, would be already referenced that point #MN
        vlos_eurasia.values -= mean_val
        mean_val = np.nanmean(vlos.values[refy1:refy2, refx1:refx2])
        mean_val = np.nan_to_num(mean_val, nan=0.0)
        vlos.values -= mean_val
        mean_val = np.nanmean(tide[refy1:refy2, refx1:refx2])
        mean_val = np.nan_to_num(mean_val, nan=0.0)
        tide -= mean_val
        mean_val = np.nanmean(iono[refy1:refy2, refx1:refx2])
        mean_val = np.nan_to_num(mean_val, nan=0.0)
        iono -= mean_val
        if not sbovl:
            mean_val = np.nanmean(gacos[refy1:refy2, refx1:refx2])
            mean_val = np.nan_to_num(mean_val, nan=0.0)
            gacos -= mean_val

    # Uncorrected velocity
    if sbovl:
        gacos = np.zeros_like(vlos.data)
    vlos_uncorrected = vlos.data - tide - iono - vlos_eurasia.data + gacos

    # Extract metadata
    corner_lon, corner_lat = cum.corner_lon.item(), cum.corner_lat.item()
    post_lon, post_lat = cum.post_lon.item(), cum.post_lat.item()

    # Create grids
    if sbovl:
        grids = {
            "vlos_uncorrected": create_geogrid(vlos_uncorrected, corner_lon, corner_lat, post_lon, post_lat),
            "tide": create_geogrid(tide, corner_lon, corner_lat, post_lon, post_lat),
            "iono": create_geogrid(iono, corner_lon, corner_lat, post_lon, post_lat),
            "eurasia": create_geogrid(vlos_eurasia.data, corner_lon, corner_lat, post_lon, post_lat),
            "vlos": create_geogrid(vlos.data, corner_lon, corner_lat, post_lon, post_lat)
        }    
        
    else:
        grids = {
            "vlos_uncorrected": create_geogrid(vlos_uncorrected, corner_lon, corner_lat, post_lon, post_lat),
            "gacos": create_geogrid(gacos, corner_lon, corner_lat, post_lon, post_lat),
            "tide": create_geogrid(tide, corner_lon, corner_lat, post_lon, post_lat),
            "iono": create_geogrid(iono, corner_lon, corner_lat, post_lon, post_lat),
            "eurasia": create_geogrid(vlos_eurasia.data, corner_lon, corner_lat, post_lon, post_lat),
            "vlos": create_geogrid(vlos.data, corner_lon, corner_lat, post_lon, post_lat)
        }
    

    # Region
    region = [corner_lon, corner_lon + shape[1] * post_lon,
              corner_lat + shape[0] * post_lat, corner_lat]

    #prepareing dem for figure
    ###demfile
    dem_file='earth_relief_fullAHB_30s.nc'
    # Upload data
    batchdir = os.environ.get("BATCH_CACHE_DIR")
    dem = os.path.join(batchdir, dem_file)
    dem_resolution='30s'
    merged_dir = '/home/users/mnergiz/1.gmt_workout/2.turkey_paper/merged_track_polys'
    tr1_dir='/home/users/mnergiz/1.gmt_workout/1.turkey_paper'
    fault_file=f'{tr1_dir}/data/GEM_NAEF.shp'
    #####
    # DEM downloading
    if not os.path.exists(dem):
        print('DEM is downloading please wait! After downloading, the process will be faster!')
        try:
            # Download the earth relief data and save it to a file
            grid = pygmt.datasets.load_earth_relief(resolution=dem_resolution, region=[25,50,25,50])
            # Saving the grid to a NetCDF file
            grid.to_netcdf(dem)
            print(f"Data successfully downloaded and saved to {dem}")
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        print(f'DEM already exists!')
    
    if not sbovl:
        # Figure creation
        fig = pygmt.Figure()
        pygmt.config(MAP_FRAME_PEN='0.7p,black',FONT_LABEL='12p,Helvetica', FONT_ANNOT='10p,Helvetica',MAP_FRAME_TYPE="inside",FORMAT_GEO_MAP="DD")
        
        # Plot rectangle (refarea in lon/lat)
        ref_lon = corner_lon + np.array([refx1, refx2]) * post_lon
        ref_lat = corner_lat + np.array([refy1, refy2]) * post_lat
        rectangle = [ref_lon[0], ref_lat[0], ref_lon[1], ref_lat[1]]
        
        # Plotting loop (6 panels)
        for i, (label, grid) in enumerate(grids.items()):
            if i == 1:
                fig.shift_origin(xshift='5.3c', yshift='1.5c')
            elif i == 2 or i == 3 or i == 4:
                fig.shift_origin(xshift='3.1c')
            if i == 5:
                fig.shift_origin(xshift='3.3c', yshift='-1.5c')


            
            v = np.nanpercentile(grid.data, [2, 98])
            symmetry_needed = (v[0] < 0 and v[1] > 0 and abs(v[0] + v[1]) < 0.25 * max(abs(v[0]), abs(v[1])))
            symmetry_needed = True
            lim = max(abs(v[0]), abs(v[1]))
            if symmetry_needed:
                lim = max(abs(v[0]), abs(v[1]))
                cmap_range = [-round(lim, 1), round(lim, 1)]
            else:
                cmap_range = [round(v[0], 1), round(v[1], 1)]
            
            if i == 0 or i == 5:
                cmap_range = [-100, 100]
            
            pygmt.makecpt(cmap="vik", series=cmap_range)
            if i == 0 or i == 5:
                fig.basemap(projection="M5c", region=region, frame=True)
            else:
                fig.basemap(projection="M3c", region=region, frame=True)
            
            pygmt.makecpt(cmap="gray", series=[-200, 10000, 3000], continuous=True, reverse=True)
            fig.grdimage(grid=dem,cmap=True,region=region,shading=True,frame=False)
            pygmt.makecpt(cmap="vik", series=cmap_range)
            fig.grdimage(grid=grid, cmap=True, nan_transparent=True)
            fig.coast(shorelines="black", water="skyblue")
            pygmt.config(MAP_FRAME_TYPE="plain")
            fig.colorbar(position="JBC+o-0c/0.2c+w1.75c/0.25c+ml+h+e", truncate=cmap_range,
                        frame=f'a{cmap_range[1]}f{cmap_range[1]/2}', cmap=True)
            

            fig.plot(x=[rectangle[0], rectangle[2], rectangle[2], rectangle[0], rectangle[0]],
                y=[rectangle[1], rectangle[1], rectangle[3], rectangle[3], rectangle[1]],
                pen="2p,black")
            
            
            pygmt.config(MAP_FRAME_TYPE="inside")
            if i == 0 or i == 5:
                fig.basemap(projection="M5c", region=region, frame=["x2f1","y2f1",'WSne'])
                fig.plot(data=f'{tr1_dir}/data/GEM_TR.shp', pen="0.5p,black",transparency=70)
                fig.plot(data=fault_file, pen="1p,black",transparency=50)   
            else:
                fig.basemap(projection="M3c", region=region, frame=["x2f1","y2f1",'wsne'])
                
        # Save output
        if not output_file:
            output_file = f"{frame}.corrections_LoS.png"
            
    else:
        # Figure creation
        fig = pygmt.Figure()
        pygmt.config(MAP_FRAME_PEN='0.7p,black',FONT_LABEL='12p,Helvetica', FONT_ANNOT='10p,Helvetica',MAP_FRAME_TYPE="inside",FORMAT_GEO_MAP="DD")
        
        # Plot rectangle (refarea in lon/lat)
        ref_lon = corner_lon + np.array([refx1, refx2]) * post_lon
        ref_lat = corner_lat + np.array([refy1, refy2]) * post_lat
        rectangle = [ref_lon[0], ref_lat[0], ref_lon[1], ref_lat[1]]
        
        # Plotting loop (5 panels)
        for i, (label, grid) in enumerate(grids.items()):
            if i == 1:
                fig.shift_origin(xshift='5.3c', yshift='1.5c')
            elif i == 2 or i == 3:
                fig.shift_origin(xshift='3.1c')
            if i == 4:
                fig.shift_origin(xshift='3.3c', yshift='-1.5c')

            v = np.nanpercentile(grid.data, [2, 98])
            symmetry_needed = (v[0] < 0 and v[1] > 0 and abs(v[0] + v[1]) < 0.25 * max(abs(v[0]), abs(v[1])))
            symmetry_needed = True
            # print(v)
            lim = max(abs(v[0]), abs(v[1]))
            if symmetry_needed:
                lim = max(abs(v[0]), abs(v[1]))
                cmap_range = [-round(lim, 1), round(lim, 1)]
            else:
                cmap_range = [round(v[0], 1), round(v[1], 1)]
            
            if i == 0 or i == 4:
                cmap_range = [-100, 100]

            pygmt.makecpt(cmap="vik", series=cmap_range)
            if i == 0 or i == 4:
                fig.basemap(projection="M5c", region=region, frame=True)
            else:
                fig.basemap(projection="M3c", region=region, frame=True)
            
            # pygmt.makecpt(cmap="gray", series=[-200, 10000, 3000], continuous=True, reverse=True)
            pygmt.makecpt(cmap="gray", series=[-200, 10000, 3000], continuous=True, reverse=True)
            fig.grdimage(grid=dem,cmap=True,region=region,shading=True,frame=False)
            pygmt.makecpt(cmap="vik", series=cmap_range)
            decomp3d_Vn_xyz='sbovl.xyz'
            plot_lib.da_to_xyz(grid, decomp3d_Vn_xyz,varname="Vn")
            # PlOT dsc_file
            fig.plot(data=decomp3d_Vn_xyz, style="c0.05c", fill="+z", cmap=True)
            os.system(f'rm {decomp3d_Vn_xyz}')
            # fig.grdimage(grid=grid, cmap=True, nan_transparent=True)
            fig.coast(shorelines="black", water="skyblue")
            pygmt.config(MAP_FRAME_TYPE="plain")
            fig.colorbar(position="JBC+o-0c/0.2c+w1.75c/0.25c+ml+h+e", truncate=cmap_range,
                        frame=f'a{cmap_range[1]}f{cmap_range[1]/2}', cmap=True)
            

            fig.plot(x=[rectangle[0], rectangle[2], rectangle[2], rectangle[0], rectangle[0]],
                y=[rectangle[1], rectangle[1], rectangle[3], rectangle[3], rectangle[1]],
                pen="2p,black")
            
            pygmt.config(MAP_FRAME_TYPE="inside")
            if i == 0 or i == 4:
                fig.basemap(projection="M5c", region=region, frame=["x2f1","y2f1",'WSne'])
                fig.plot(data=f'{tr1_dir}/data/GEM_TR.shp', pen="0.5p,black",transparency=70)
                fig.plot(data=fault_file, pen="1p,black",transparency=50)   
            else:
                fig.basemap(projection="M3c", region=region, frame=["x2f1","y2f1",'wsne'])
        # Save output
        if not output_file:
            output_file = f"{frame}.corrections_sbovl.png"
        
        
        
    fig.savefig(output_file, dpi=900)
    print(f"Plot saved to {output_file} in {round(time.time() - start_time, 2)} seconds.")

if __name__ == "__main__":
    sys.exit(main())
