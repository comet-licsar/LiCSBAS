#!/usr/bin/env python3

import argparse
import os
import shutil
import h5py as h5
import pandas as pd
import numpy as np
from datetime import datetime
import lics_tstools as lts
import xarray as xr
import multiprocessing as multi
import re
import matplotlib.pyplot as plt


"""
v1.0 20250731 Muhammet Nergizci, COMET University of Leeds

========
Overview
========
This script outputs a tif and png file of cumulative displacement from cum*.h5 iterativelly, also calculated the plate_motion and interseismic effect in each epoch.

=====
Usage
=====
LiCSBAS_cum2tif.py -i cum_filt_interpolate.h5 --plate_motion --interseismic_motion

  -t   Path to TS folder. Default: TS_GEOCml10GACOSmask
  -i   HDF5 file (cum.h5, cum_filt.h5, or cum_filt_interpolate.h5)  [REQUIRED]
  -mask  Mask dataset name (under results/). Default: mask
  -dem   DEM parameter file name under TS folder. Default: EQA.dem_par
  -f   Frame number for output naming. Default: CWD basename
  -p   Start date (YYYYMMDD or YYYY-MM-DD). Default: first imdate in H5
  -s   End date   (YYYYMMDD or YYYY-MM-DD). Required if no
  --plate_motion         Remove cumulative plate-motion (EU-fixed default)
  --interseismic_motion  Also remove cumulative interseismic accumulation
  --n_para <num>         Number of parallel processes to use. Default: 4 #TODO not set yet
"""
#%%useful function
def cum_wrapper(frame, cumxr, imdate, plate_motion, refarea, interseismic_motion,
                imd_p_dt64, vlos_eurasia_reshaped, vlos_gnss):
    """
    Computes corrected cumulative displacement for a single epoch.
    Assumes the following names exist in the caller scope (main),
    captured via closure when we re-bind this function inside main:
      - imd_p_dt64
      - vlos_eurasia_reshaped (or None)
      - vlos_gnss            (or None)
    """
    #reference_area
    refx1, refx2, refy1, refy2 = [int(s) for s in re.split('[:/]', refarea)]

    # parse imdate numpy datetime64[D]
    im_d = np.datetime64(datetime.strptime(imdate, "%Y%m%d").date(), 'D')

    # years since primary
    dt_days = (im_d - imd_p_dt64).astype('timedelta64[D]').astype(int)
    years = dt_days / 365.25
    
    # select cumulative at epoch and at primary
    try:
        C_t = cumxr['cum'].sel(time=imdate)
    except Exception:
        C_t = cumxr['cum'].sel(time=im_d, method='nearest')

    p_str = str(imd_p_dt64).replace('-', '')
    try:
        C_0 = cumxr['cum'].sel(time=p_str)
    except Exception:
        C_0 = cumxr['cum'].sel(time=imd_p_dt64, method='nearest')

    C_t.values = C_t.values - np.nanmean(C_t.values[refy1:refy2, refx1:refx2])
    C_0.values = C_0.values - np.nanmean(C_0.values[refy1:refy2, refx1:refx2])
    cum_base  = (C_t - C_0).copy()  # mm
    
    # plate-motion cumulative removal: v_los * years
    cum_corr_plate = None
    if plate_motion and (vlos_eurasia_reshaped is not None) and years != 0:
        pm_cum = (vlos_eurasia_reshaped * years).interp_like(cum_base, method='nearest')
        pm_cum.values = pm_cum.values - np.nanmean(pm_cum.values[refy1:refy2, refx1:refx2])
        tmp = (cum_base - pm_cum)
        tmp.values = tmp.values - np.nanmean(tmp.values[refy1:refy2, refx1:refx2])
        cum_corr_plate = tmp  # xr.DataArray

    # interseismic cumulative removal: v_los * years
    cum_corr_plate_inter = None
    if interseismic_motion and (vlos_gnss is not None) and years != 0:
        # start from plate-corrected if available, else from base
        start_da = cum_corr_plate if cum_corr_plate is not None else cum_base
        is_cum = (vlos_gnss * years).interp_like(start_da, method='nearest')
        is_cum.values = is_cum.values - np.nanmean(is_cum.values[refy1:refy2, refx1:refx2])
        tmp2 = (start_da - is_cum)
        tmp2.values = tmp2.values - np.nanmean(tmp2.values[refy1:refy2, refx1:refx2])
        cum_corr_plate_inter = tmp2  # xr.DataArray
    
    # saving
    if cum_corr_plate_inter is not None:
        print("Saving plate+interseismic corrected tif...")
        cum_corr_plate_inter.values = cum_corr_plate_inter.values - np.nanmean(cum_corr_plate_inter.values[refy1:refy2, refx1:refx2])
        lts.export_xr2tif(cum_corr_plate_inter, f'cums/{frame}.{imdate}.corrected.tif', dogdal=False)
        
    elif cum_corr_plate is not None:
        print("Saving plate-corrected tif...")
        cum_corr_plate.values = cum_corr_plate.values - np.nanmean(cum_corr_plate.values[refy1:refy2, refx1:refx2])
        #exporting tif:
        lts.export_xr2tif(cum_corr_plate, f'cums/{frame}.{imdate}.corrected.tif', dogdal = False)

    print(f"Processed epoch {imdate} (Δt={years:.4f} yr)")
    
    # 
    if interseismic_motion and (vlos_gnss is not None) and years != 0 and im_d == np.datetime64('2024-12-21'):
      (cum_corr_plate_inter-cum_corr_plate).plot(cmap='RdBu')
      plt.savefig(f'{p_str}_{im_d}_vlos_inter.png')
      plt.close()
    
      (cum_base-cum_corr_plate).plot(cmap='RdBu')
      plt.savefig(f'{p_str}_{im_d}_vlos_plate.png')
      plt.close()
      
      ##lastone
      fig, axes = plt.subplots(1, 3, figsize=(18, 6))  # 1 row, 3 columns
      vmin=-100
      vmax=100
      # 1. Original cumulative
      im1 = cum_base.plot(cmap='RdBu', ax=axes[0], add_colorbar=False, vmin=vmin, vmax=vmax)
      axes[0].set_title("cum")  
      # 2. Plate-corrected
      im2 = cum_corr_plate.plot(cmap='RdBu', ax=axes[1], add_colorbar=False, vmin=vmin, vmax=vmax)
      axes[1].set_title("cum_corr_plate")  
      # 3. Plate+interseismic corrected
      im3 = cum_corr_plate_inter.plot(cmap='RdBu', ax=axes[2], add_colorbar=False, vmin=vmin, vmax=vmax)
      axes[2].set_title("cum_corr_plate_inter")  
      # Add one shared colorbar for all three
      cbar = fig.colorbar(im1, ax=axes, orientation="horizontal", fraction=0.05, pad=0.2)
      cbar.set_label("Displacement (mm)")  # or unit you want  
      #plt.tight_layout()
      plt.savefig(f"{p_str}_{im_d}_cum_plate_inter_subplot.png")
      plt.close()
      
    if years != 0 and im_d == np.datetime64('2024-12-21'):
        (cum_base-cum_corr_plate).plot(cmap='RdBu')
        plt.savefig(f'{p_str}_{im_d}_vlos_plate.png')
        plt.close()
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))  # 1 row, 2 columns
        vmin=-100
        vmax=100
        # 1. Original cumulative
        im1 = cum_base.plot(cmap='RdBu', ax=axes[0], add_colorbar=False, vmin=vmin, vmax=vmax)
        axes[0].set_title("cum")  
        # 2. Plate-corrected
        im2 = cum_corr_plate.plot(cmap='RdBu', ax=axes[1], add_colorbar=False, vmin=vmin, vmax=vmax)
        axes[1].set_title("cum_corr_plate")  
        # Add one shared colorbar for all three
        cbar = fig.colorbar(im1, ax=axes, orientation="horizontal", fraction=0.05, pad=0.2)
        cbar.set_label("Displacement (mm)")  # or unit you want  
        #plt.tight_layout()
        plt.savefig(f"{p_str}_{im_d}_cum_plate_subplot.png")
        plt.close()

    if years == 0:
        zero_da = xr.zeros_like(cum_base)
        arr_plate = zero_da.values.astype(np.float32)
        arr_inter = zero_da.values.astype(np.float32)
    else:
        arr_plate = (cum_corr_plate.values.astype(np.float32)
                    if cum_corr_plate is not None else None)
        arr_inter = (cum_corr_plate_inter.values.astype(np.float32)
                    if cum_corr_plate_inter is not None else None)

    return imdate, arr_plate, arr_inter

#%% main function running
def main(TS_folder, cum_h5, mask, dem_par, frame, imd_p, imd_s, ve_gnss=None, vn_gnss=None, plate_motion=False, interseismic_motion=False, n_para=4, sbovl=False):

    cum_name= cum_h5.split('.')[0]
    cum_h5 = os.path.join(TS_folder, cum_h5) 
    GEOC_folder = TS_folder.split('_')[-1]
    dem_par = os.path.join(GEOC_folder, dem_par)
    mask = os.path.join(TS_folder,'results', mask)
    if sbovl:
        E_unit=lts.load_tif2xr(f'{frame}.E.azi.geo.tif')
        N_unit=lts.load_tif2xr(f'{frame}.N.azi.geo.tif')
        U_unit=lts.load_tif2xr(f'{frame}.U.azi.geo.tif')
    else:
        E_unit=lts.load_tif2xr(f'{frame}.E.geo.tif')
        N_unit=lts.load_tif2xr(f'{frame}.N.geo.tif')
        U_unit=lts.load_tif2xr(f'{frame}.U.geo.tif')
      
    compress = 'gzip'
    q = multi.get_context('fork')
    
    ##reference
    infodir = os.path.join(TS_folder, 'info')
    reffile = os.path.join(infodir, '16ref.txt')
    if not os.path.exists(reffile):
        print(f"Error: Reference file {reffile} does not exist.")
        exit(1)
    else:
        with open(reffile, "r") as f:
            refarea = f.read().split()[0]  # str, x1/x2/y1/y2
        #   refx1, refx2, refy1, refy2 = [int(s) for s in re.split('[:/]', refarea)]
  
    ##cums file creates
    os.makedirs(os.path.join(TS_folder,'results','cums'), exist_ok=True)
    os.makedirs('cums', exist_ok=True)

    #read cum for the default start
    cumh55 = h5.File(cum_h5,'r+')
    imdates = cumh55['imdates'][()].astype(str).tolist()
    if not imd_p:
        imd_p = imdates[0]


    cumxr = lts.loadall2cube(cum_h5)#, extracols = 'cum')
    
    if plate_motion:
        vlos_eurasia = lts.generate_pmm_velocity(frame, 'Eurasia', 'GEOC', azi=sbovl)
        #reshape
        vlos_eurasia_reshaped=vlos_eurasia.interp_like(cumxr.vel)
    if interseismic_motion:
        
        if ve_gnss is None or vn_gnss is None:
            ve_gnss_nc='/gws/ssde/j25a/nceo_geohazards/vol1/projects/COMET/mnergizci/1.second_paper/interseismic/decomp3d.nc'
            vn_gnss_nc='/gws/ssde/j25a/nceo_geohazards/vol1/projects/COMET/mnergizci/1.second_paper/interseismic/velmap_insars29_sbovls0_scalar.nc'
            if not os.path.exists(ve_gnss_nc):
                print(f"Error: GNSS velocity file {ve_gnss_nc} does not exist.")
                exit(1)
            if not os.path.exists(vn_gnss_nc):
                print(f"Error: GNSS velocity file {vn_gnss_nc} does not exist.")
                exit(1)

            ve_gnss= xr.load_dataset(ve_gnss_nc).Ve
            vn_gnss= xr.load_dataset(vn_gnss_nc).Vn
            vu_gnss= xr.load_dataset(ve_gnss_nc).Vu
            ve_gnss_velmap= xr.load_dataset(vn_gnss_nc).Ve

            ##reshape
            ve_gnss_reshaped=ve_gnss.interp_like(E_unit)
            vn_gnss_reshaped=vn_gnss.interp_like(E_unit)
            vu_gnss_reshaped=vu_gnss.interp_like(E_unit)

            ve_gnss_velmap_reshaped=ve_gnss_velmap.interp_like(E_unit)
            ve_gnss_filled = ve_gnss_reshaped.fillna(ve_gnss_velmap_reshaped)
            vu_gnss_reshaped = vu_gnss_reshaped.where(np.abs(vu_gnss_reshaped) <= 5)
            
            if sbovl:
                vlos_gnss = ve_gnss_filled * E_unit + vn_gnss_reshaped * N_unit
            else:
                vlos_gnss = ve_gnss_filled * E_unit + vn_gnss_reshaped * N_unit + vu_gnss_reshaped * U_unit
            #vlos_gnss
    else:
        print("No interseismic motion calculation requested.")
    
    # if user gave an end date, restrict to [imd_p, imd_s]; else do all epochs
    if isinstance(imd_p, str):
        imd_p_dt64 = (np.datetime64(datetime.strptime(imd_p, "%Y%m%d").date(), 'D')
                        if len(imd_p) == 8 else
                        np.datetime64(datetime.strptime(imd_p, "%Y-%m-%d").date(), 'D'))
    else:
        imd_p_dt64 = np.datetime64(datetime.strptime(str(imdates[0]), "%Y%m%d").date(), 'D')

    if imd_s is not None:
        imd_p_i = int(str(imd_p).replace('-', '')) if isinstance(imd_p, str) else int(imdates[0])
        imd_s_i = int(str(imd_s).replace('-', '')) if isinstance(imd_s, str) else int(imd_s)
        epochs_to_do = [d for d in imdates if imd_p_i <= int(d) <= imd_s_i]
    else:
        epochs_to_do = imdates[:]  # all epochs

    # bind velocity fields (or None) for the wrapper closure
    vlos_eurasia_reshaped = locals().get('vlos_eurasia_reshaped', None) if plate_motion else None
    vlos_gnss = locals().get('vlos_gnss', None) if interseismic_motion else None

    # -------- build args_list and run pool --------
    # args_list = [(cumxr, d, plate_motion, interseismic_motion) for d in epochs_to_do]
    # build args_list including the constants we computed
    args_list = [
        (frame, cumxr, d, plate_motion, refarea, interseismic_motion, imd_p_dt64,
        vlos_eurasia_reshaped if plate_motion else None,
        vlos_gnss if interseismic_motion else None)
        for d in epochs_to_do
    ]

    print(f"Testing sequential run on {len(args_list)} epochs...", flush=True)
    corr_plate_values = []
    corr_plate_inter_values = []

    for args in args_list:
        imd, corr_plate, corr_plate_inter = cum_wrapper(*args)   # set  inside cum_wrapper
        # print("Result:", imd)
        corr_plate_values.append(corr_plate)
        corr_plate_inter_values.append(corr_plate_inter)


    #%%now build stacks with the same shape as cumxr.cum
    T_out = len(epochs_to_do)
    Y, X = cumxr['cum'].isel(time=0).shape
    imdates_out = np.asarray([int(d) for d in epochs_to_do], dtype=np.int32)

    # Prepare stacks (only if those corrections are relevant)
    stack_plate = None
    stack_inter = None
    if plate_motion:
        stack_plate = np.full((T_out, Y, X), np.nan, dtype=np.float32)
    if interseismic_motion:
        stack_inter = np.full((T_out, Y, X), np.nan, dtype=np.float32)

    # Fill stacks
    for i, (arr_p, arr_i) in enumerate(zip(corr_plate_values, corr_plate_inter_values)):
        if stack_plate is not None and arr_p is not None:
            stack_plate[i, :, :] = arr_p  # already float32
        if stack_inter is not None and arr_i is not None:
            stack_inter[i, :, :] = arr_i  # already float32
    # 
    # --- write to the same HDF5 file (single writer) ---
    # cumh55 is already opened as h5.File(cum_h5, 'r+')
    # keep original /imdates and /cum intact; add companions
    # if 'imdates_corr' in cumh55:
    #     del cumh55['imdates_corr']
    # cumh55.create_dataset('imdates_corr', data=imdates_out, dtype=np.int32)

    if stack_plate is not None:
        if 'cum_plate' in cumh55:
            del cumh55['cum_plate']
        cumh55.create_dataset('cum_plate',
                            data=stack_plate, dtype=np.float32,
                            compression='gzip', chunks=True)

    if stack_inter is not None:
        if 'cum_plate_inter' in cumh55:
            del cumh55['cum_plate_inter']
        cumh55.create_dataset('cum_plate_inter',
                            data=stack_inter, dtype=np.float32,
                            compression='gzip', chunks=True)

    cumh55.flush()
    cumh55.close()
    print("Done writing corrected datasets to HDF5.")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read the cum.h5 file and output the binary, tif and png file of cumulative dispalcement of each epoch.")
    parser.add_argument("-t", dest="TS_folder", default="TS_GEOCml10GACOSmask", help="Path to the folder. Default: TS_GEOCml10GACOSmask.")
    parser.add_argument("-i", dest="cum_h5", help="Path to the h5 file. No default must be an input; (cum.h5, cum_filt.h5, cum_filt_interpolate.h5)")
    parser.add_argument("-mask", dest="mask", default="mask", help="Path to the mask file.")
    parser.add_argument("-dem", dest="dem_par", default="EQA.dem_par", help="Path to the DEM parameter file. Default=EQA.dem_par")
    parser.add_argument("-f", dest="frame", default=os.path.basename(os.getcwd()), help="frame number of naming files")
    parser.add_argument("-p", dest="imd_p", default=None, help="Start date of cumulative displacement. Default is first date of the cum_filt.h5")
    parser.add_argument("-s", dest="imd_s", default=None, help="End date of cumulative displacement.")
    parser.add_argument("-ve_gnss", default=None, help="Path to the GNSS velocity file.")
    parser.add_argument("-vn_gnss", default=None, help="Path to the GNSS velocity file.")
    parser.add_argument("--plate_motion", action="store_true", help="If set, it will calculate the plate motion effect")
    parser.add_argument("--interseismic_motion", action="store_true", help="If set, it will calculate the interseismic accumulation")
    parser.add_argument("--n_para", default=4, type=int, help="Number of parallel processes to use")
    parser.add_argument("--sbovl", action="store_true", help="If set, it will use the sbovl dataset")
    args = parser.parse_args()
    args.interseismic_motion = True
    if args.sbovl == True:
        args.TS_folder = 'TS_GEOCml10mask'
    main(args.TS_folder ,args.cum_h5, args.mask, args.dem_par, args.frame, args.imd_p, args.imd_s, args.ve_gnss, args.vn_gnss, args.plate_motion, args.interseismic_motion, args.n_para, args.sbovl)
