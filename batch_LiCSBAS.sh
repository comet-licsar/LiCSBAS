#!/bin/bash -eu

# LiCSBAS steps:
#  01: LiCSBAS01_get_geotiff.py
#  02to05: LiCSBAS02to05_unwrap.py   or   02: LiCSBAS02_ml_prep.py
#                                         03: LiCSBAS03op_GACOS.py (optional)
#                                         04: LiCSBAS04op_mask_unw.py (optional)
#                                         05: LiCSBAS05op_clip_unw.py (optional)
#  11: LiCSBAS11_check_unw.py
#  (optional) 120: LiCSBAS120_choose_reference.py   - RECOMMENDED, especially if nullification is used, thus added to cometdev
#  12: LiCSBAS12_loop_closure.py
#  13: LiCSBAS13_sb_inv.py
#  14: LiCSBAS14_vel_std.py
#  15: LiCSBAS15_mask_ts.py
#  16: LiCSBAS16_filt_ts.py

#
# Status of COMET dev version - the experimental functions are turned on with 
#
#################
### Settings ####
#################
start_step="01"	# 01-05, 11-16
end_step="16"	# 01-05, 11-16

cometdev='0' # shortcut to use COMET's experimental/dev functions. At this moment, '1' will turn on the nullification. Recommended: 0
# sbovl='n' # if 'y', LiCSBAS will apply on sbovls  ## TODO
eqoffs="n"  # if 'y', it will do: get_eq_offsets, then invert. if singular_gauss, then set use of model (not recommended now, experimental/need some work).
nlook="1"	# multilook factor, used in step02
GEOCmldir="GEOCml${nlook}"	# If start from 11 or later after doing 03-05, use e.g., GEOCml${nlook}GACOSmaskclip
n_para="" # Number of parallel processing in step 02-05,12,13,16. default: number of usable CPU
gpu="n"	# y/n
check_only="n" # y/n. If y, not run scripts and just show commands to be done

logdir="log"
log="$logdir/$(date +%Y%m%d%H%M)$(basename $0 .sh)_${start_step}_${end_step}.log"

freq="" # default: 5.405e9 Hz

### Running the updated pipelines:
run_reunwrapping='n' # y/n. default: 'n'. Reunwrapping would use 02to05 script instead of the original 02[,03,04,05]

### Optional steps (03-05) ###
order_op03_05="03 04 05"	# can change order e.g., 05 03 04
do03op_GACOS="n"	# y/n
do04op_mask="n"	# y/n
do05op_clip="n"	# y/n
p04_mask_coh_thre_avg=""	# e.g. 0.2
p04_mask_coh_thre_ifg=""	# e.g. 0.2
p04_mask_range=""	# e.g. 10:100/20:200 (ix start from 0)
p04_mask_range_file=""	# Name of file containing range list
p05_clip_range=""	# e.g. 10:100/20:200 (ix start from 0)
p05_clip_range_geo=""	# e.g. 130.11/131.12/34.34/34.6 (in deg)

# Optional reunwrapping:
p02to05_freq=$freq # default: 5.405e9 Hz
p02to05_gacos="" # y/n. default: 'y'. Use gacos data if available (for majority of epochs, data without GACOS corr would be dropped)
p02to05_hgtcorr="" # y/n. default: 'n'. Recommended for regions with high and varying topography
p02to05_cascade="" # y/n. default: 'n'. Cascade from higher multilook factor would propagate to higher resolution (lower ML factor) data. Useful but not universal
p02to05_filter="" # gold, gauss or adf. Default: 'gold'
p02to05_thres="" # default: 0.35. Spatial consistence of the interferogram. Recommended to keep this value. If too much is masked, may try getting close to 0 (although, this would introduce some unw errors)
p02to05_cliparea_geo=$p05_clip_range_geo # setting the clip range, e.g. 130.11/131.12/34.34/34.6 (in deg)
p02to05_n_para=$n_para
p02to05_op_GEOCdir="" # by default, if none, it will use GEOC directory

### Frequently used options. If blank, use default. ###
p01_start_date=""	# default: 20141001
p01_end_date=""	# default: today
p01_get_gacos="n" # y/n
p01_get_pha="n" # y/n
p01_get_mli="n" # y/n
p01_sbovl="n"
p02_sbovl="n"
p11_unw_thre=""	# default: 0.3
p11_coh_thre=""	# default: 0.05
p11_s_param="n" # y/n
p11_sbovl="n"
p120_use="n"  # y/n
p120_sbovl="n"
p12_loop_thre=""	# default: 1.5 rad. With --nullify, recommended higher value (as this is an average over the whole scene)
p12_multi_prime="y"	# y/n. y recommended
p12_nullify="" # y/n. y recommended
p12_rm_ifg_list=""	# List file containing ifgs to be manually removed
p12_skippngs="" # y/n. n by default
p13_nullify_noloops="" # y/n. n by default
p13_singular="" # y/n. n by default
p13_singular_gauss="" # y/n. n by default
p13_skippngs="" # y/n. n by default
p13_sbovl="n"
p15_coh_thre=""	# default: 0.05
p15_n_unw_r_thre=""	# default: 1.5
p15_vstd_thre=""	# default: 100 mm/yr
p15_maxTlen_thre=""	# default: 1 yr
p15_n_gap_thre=""	# default: 10
p15_stc_thre=""	# default: 10 mm
p15_n_ifg_noloop_thre=""	# default: 500 - setting this much higher than orig since we nullify them (p13_nullify_noloops)
p15_n_loop_err_thre=""	# default: 5
p15_n_loop_err_ratio_thre=""	# default: 0.7 - in future we will switch to this ratio term, instead of n_loop_err
p15_resid_rms_thre=""	# default: 15 mm
p15_avg_phasebias="" # default: not used. Setting 1 or 1.2 rad is good option
p15_n_gap_use_merged="y" # default: 'y'
p15_sbovl="n"
p16_filtwidth_km=""	# default: 2 km
p16_filtwidth_yr=""	# default: avg_interval*3 yr
p16_deg_deramp=""	# 1, bl, or 2. default: no deramp
p16_demerr="n"	# y/n. default: n
p16_hgt_linear="n"	# y/n. default: n
p16_hgt_min=""	# default: 200 (m)
p16_hgt_max=""  # default: 10000 (m)
p16_range=""	# e.g. 10:100/20:200 (ix start from 0)
p16_range_geo=""	# e.g. 130.11/131.12/34.34/34.6 (in deg)
p16_ex_range=""	# e.g. 10:100/20:200 (ix start from 0)
p16_ex_range_geo=""	# e.g. 130.11/131.12/34.34/34.6 (in deg)
p16_interpolate_nans="y"  # will interpolate nans in unmasked pixels
p16_skippngs="" # y/n. n by default
p16_sbovl="n"

### Less frequently used options. If blank, use default. ###
p01_frame=""	# e.g. 021D_04972_131213 
p01_n_para=$n_para	# default: 4
p01_rngoff="n"
p02_rngoff="n"
p02_GEOCdir=""	# default: GEOC
p02_GEOCmldir=""	# default: GEOCml$nlook
p02_freq=$freq	# default: 5.405e9 Hz
p02_n_para=$n_para   # default: # of usable CPU
p03_inGEOCmldir=""	# default: $GEOCmldir
p03_outGEOCmldir_suffix="" # default: GACOS
p03_fillhole="y"	# y/n. default: n
p03_gacosdir=""	# default: GACOS
p03_n_para=$n_para   # default: # of usable CPU
p04_inGEOCmldir=""	# default: $GEOCmldir
p04_outGEOCmldir_suffix="" # default: mask
p04_n_para=$n_para   # default: # of usable CPU
p05_inGEOCmldir=""      # default: $GEOCmldir
p05_outGEOCmldir_suffix="" # default: clip
p05_n_para=$n_para   # default: # of usable CPU
p11_GEOCmldir=""	# default: $GEOCmldir
p11_TSdir=""	# default: TS_$GEOCmldir
p11_minbtemp=""  # default: 0 (not use)
p11_maxbtemp=""  # default: 0 (not use)
p120_ignoreconncomp="n" # y/n
p12_GEOCmldir=""        # default: $GEOCmldir
p12_TSdir=""    # default: TS_$GEOCmldir
p12_n_para=$n_para	# default: # of usable CPU
p13_GEOCmldir=""        # default: $GEOCmldir
p13_TSdir=""    # default: TS_$GEOCmldir
p13_inv_alg=""	# LS (default) or WLS
p13_mem_size=""	# default: 8000 (MB)
p13_gamma=""	# default: 0.0001
p13_inputunit="" # rad by default
p13_n_para=$n_para	# default: # of usable CPU
p13_n_unw_r_thre=""	# default: 1 for shorter-than-L-band-wavelength (if cometdev, will set to 0.1)
p13_keep_incfile="n"	# y/n. default: n
p14_TSdir=""    # default: TS_$GEOCmldir
p14_mem_size="" # default: 4000 (MB)
p15_TSdir=""    # default: TS_$GEOCmldir
p15_vmin=""	# default: auto (mm/yr)
p15_vmax=""	# default: auto (mm/yr)
p15_keep_isolated="n"	# y/n. default: n
p15_noautoadjust="n" # y/n. default: n
p16_TSdir=""    # default: TS_$GEOCmldir
p16_nomask="n"	# y/n. default: n
p16_n_para=$n_para   # default: # of usable CPU


# eqoffs
eqoffs_minmag="0"  # min magnitude of earthquakes to auto-find. 0 means skipping the estimation.
eqoffs_txtfile="eqoffsets.txt"  # path to txt file containing custom-set earthquake dates (if eqoffs_minmag is disabled/0) or that will use results of auto-find
eqoffs_buffer="0.1"  # buffer (in degrees, assuming work with WGS-84 geocoded data) to search for earthquakes (if eqoffs_minmag is set)


#############################
### Run (No need to edit) ###
#############################
echo ""
echo "Start step: $start_step"
echo "End step:   $end_step"
echo "Log file:   $log"
echo ""
mkdir -p $logdir

if [ $run_reunwrapping == "y" ]; then
  # do some additional settings for the reunwrapping:
  p01_get_pha="y"
  p01_get_mli="y" # not really needed but useful for weighting in multilooking
  order_op03_05='' #skipping the optional 03-05 steps, contained here
  skipstep02=1
else
  skipstep02=0
fi

if [ $start_step -le 01 -a $end_step -ge 01 ];then
  p01_op=""
  if [ ! -z $p01_frame ];then p01_op="$p01_op -f $p01_frame"; fi
  if [ ! -z $p01_start_date ];then p01_op="$p01_op -s $p01_start_date"; fi
  if [ ! -z $p01_end_date ];then p01_op="$p01_op -e $p01_end_date"; fi
  if [ ! -z $p01_n_para ];then p01_op="$p01_op --n_para $p01_n_para"; fi
  # Add --sbovl option if p01_sbovl is "y"
  if [ "$p01_sbovl" == "y" ]; then p01_op="$p01_op --sbovl"; fi
  if [ "$p01_rngoff" == "y" ]; then p01_op="$p01_op --rngoff"; fi
    if [ "$p01_get_gacos" == "y" ]; then p01_op="$p01_op --get_gacos"; fi
    if [ "$p01_get_pha" == "y" ]; then p01_op="$p01_op --get_pha"; fi
    if [ "$p01_get_mli" == "y" ]; then p01_op="$p01_op --get_mli"; fi

  if [ $check_only == "y" ];then
    echo "LiCSBAS01_get_geotiff.py $p01_op"
  else
    LiCSBAS01_get_geotiff.py $p01_op 2>&1 | tee -a $log
    if [ ${PIPESTATUS[0]} -ne 0 ];then exit 1; fi
  fi
fi

if [ "$skipstep02" -eq 1 ]; then
  p02to05_op=""

  # Setting the GEOC directory
  if [ ! -z "$p02to05_op_GEOCdir" ]; then
    p02to05_op="$p02to05_op -i $p02to05_op_GEOCdir"
  else
    p02to05_op="$p02to05_op -i GEOC"
  fi

  # Additional parameters
  if [ ! -z "$nlook" ]; then p02to05_op="$p02to05_op -M $nlook"; fi
  if [ ! -z "$p02to05_freq" ]; then p02to05_op="$p02to05_op --freq $p02to05_freq"; fi
  if [ ! -z "$p02to05_n_para" ]; then p02to05_op="$p02to05_op --n_para $p02to05_n_para"; fi
  if [ ! -z "$p02to05_thres" ]; then p02to05_op="$p02to05_op --thres $p02to05_thres"; fi
  if [ ! -z "$p02to05_filter" ]; then p02to05_op="$p02to05_op --filter $p02to05_filter"; fi
  if [ ! -z "$p02to05_cliparea_geo" ]; then p02to05_op="$p02to05_op -g $p02to05_cliparea_geo"; fi
  if [ "$p02to05_cascade" == "y" ]; then p02to05_op="$p02to05_op --cascade"; fi
  if [ "$p02to05_hgtcorr" == "y" ]; then p02to05_op="$p02to05_op --hgtcorr"; fi
  if [ "$p02to05_gacos" == "y" ]; then p02to05_op="$p02to05_op --gacos"; fi

  # Execute or check-only mode
  if [ "$check_only" == "y" ]; then
    echo "LiCSBAS02to05_unwrap.py $p02to05_op"
  else
    LiCSBAS02to05_unwrap.py $p02to05_op 2>&1 | tee -a "$log"
    if [ "${PIPESTATUS[0]}" -ne 0 ]; then exit 1; fi
  fi

else
  # Run step 02 if not skipped
  if [ "$start_step" -le 02 -a "$end_step" -ge 02 -a "$skipstep02" -eq 0 ]; then
    p02_op=""

    # Set the GEOC directories
    if [ ! -z "$p02_GEOCdir" ]; then
      p02_op="$p02_op -i $p02_GEOCdir"
    else
      p02_op="$p02_op -i GEOC"
    fi
    if [ ! -z "$p02_GEOCmldir" ]; then p02_op="$p02_op -o $p02_GEOCmldir"; fi
    if [ ! -z "$nlook" ]; then p02_op="$p02_op -n $nlook"; fi
    if [ ! -z "$p02_freq" ]; then p02_op="$p02_op --freq $p02_freq"; fi

    # Parallel processing
    if [ ! -z "$p02_n_para" ]; then
      p02_op="$p02_op --n_para $p02_n_para"
    elif [ ! -z "$n_para" ]; then
      p02_op="$p02_op --n_para $n_para"
    fi

    if [ "$p02_sbovl" == "y" ]; then p02_op="$p02_op --sbovl"; fi
    if [ "$p02_rngoff" == "y" ]; then p02_op="$p02_op --rngoff"; fi

  if [ $check_only == "y" ];then
      echo "LiCSBAS02_ml_prep.py $p02_op"
    else
    LiCSBAS02_ml_prep.py $p02_op 2>&1 | tee -a $log
    if [ ${PIPESTATUS[0]} -ne 0 ];then exit 1; fi
    fi
  fi
fi

## Optional steps
for step in $order_op03_05; do ##1

if [ $step -eq 03 -a $start_step -le 03 -a $end_step -ge 03 ];then
  if [ $do03op_GACOS == "y" ]; then
    p03_op=""
    if [ ! -z $p03_inGEOCmldir ];then inGEOCmldir="$p03_inGEOCmldir";
      else inGEOCmldir="$GEOCmldir"; fi
    p03_op="$p03_op -i $inGEOCmldir"
    if [ ! -z $p03_outGEOCmldir_suffix ];then outGEOCmldir="$inGEOCmldir$p03_outGEOCmldir_suffix";
      else outGEOCmldir="${inGEOCmldir}GACOS"; fi
    p03_op="$p03_op -o $outGEOCmldir"
    if [ ! -z $p03_gacosdir ];then p03_op="$p03_op -g $p03_gacosdir"; fi
    if [ $p03_fillhole == "y" ];then p03_op="$p03_op --fillhole"; fi
    if [ ! -z $p03_n_para ];then p03_op="$p03_op --n_para $p03_n_para";
    elif [ ! -z $n_para ];then p03_op="$p03_op --n_para $n_para";fi

    if [ $check_only == "y" ];then
      echo "LiCSBAS03op_GACOS.py $p03_op"
    else
      LiCSBAS03op_GACOS.py $p03_op 2>&1 | tee -a $log
      if [ ${PIPESTATUS[0]} -ne 0 ];then exit 1; fi
    fi
    ### Update GEOCmldir to be used for following steps
    GEOCmldir="$outGEOCmldir"
  fi
fi

if [ $step -eq 04 -a $start_step -le 04 -a $end_step -ge 04 ];then
  if [ $do04op_mask == "y" ]; then
    p04_op=""
    if [ ! -z $p04_inGEOCmldir ];then inGEOCmldir="$p04_inGEOCmldir";
      else inGEOCmldir="$GEOCmldir"; fi
    p04_op="$p04_op -i $inGEOCmldir"
    if [ ! -z $p04_outGEOCmldir_suffix ];then outGEOCmldir="$inGEOCmldir$p04_outGEOCmldir_suffix";
      else outGEOCmldir="${inGEOCmldir}mask"; fi
    p04_op="$p04_op -o $outGEOCmldir"
    if [ ! -z $p04_mask_coh_thre_avg ];then p04_op="$p04_op -c $p04_mask_coh_thre_avg"; fi
    if [ ! -z $p04_mask_coh_thre_ifg ];then p04_op="$p04_op -s $p04_mask_coh_thre_ifg"; fi
    if [ ! -z $p04_mask_range ];then p04_op="$p04_op -r $p04_mask_range"; fi
    if [ ! -z $p04_mask_range_file ];then p04_op="$p04_op -f $p04_mask_range_file"; fi
    if [ ! -z $p04_n_para ];then p04_op="$p04_op --n_para $p04_n_para";
    elif [ ! -z $n_para ];then p04_op="$p04_op --n_para $n_para";fi

    if [ $check_only == "y" ];then
      echo "LiCSBAS04op_mask_unw.py $p04_op"
    else
      LiCSBAS04op_mask_unw.py $p04_op 2>&1 | tee -a $log
      if [ ${PIPESTATUS[0]} -ne 0 ];then exit 1; fi
    fi
    ### Update GEOCmldir to be used for following steps
    GEOCmldir="$outGEOCmldir"
  fi
fi

if [ $step -eq 05 -a $start_step -le 05 -a $end_step -ge 05 ];then
  if [ $do05op_clip == "y" ]; then
    p05_op=""
    if [ ! -z $p05_inGEOCmldir ];then inGEOCmldir="$p05_inGEOCmldir";
      else inGEOCmldir="$GEOCmldir"; fi
    p05_op="$p05_op -i $inGEOCmldir"
    if [ ! -z $p05_outGEOCmldir_suffix ];then outGEOCmldir="$inGEOCmldir$p05_outGEOCmldir_suffix";
      else outGEOCmldir="${GEOCmldir}clip"; fi
    p05_op="$p05_op -o $outGEOCmldir"
    if [ ! -z $p05_clip_range ];then p05_op="$p05_op -r $p05_clip_range"; fi
    if [ ! -z $p05_clip_range_geo ];then p05_op="$p05_op -g $p05_clip_range_geo"; fi
    if [ ! -z $p05_n_para ];then p05_op="$p05_op --n_para $p05_n_para";
    elif [ ! -z $n_para ];then p05_op="$p05_op --n_para $n_para";fi

    if [ $check_only == "y" ];then
      echo "LiCSBAS05op_clip_unw.py $p05_op"
    else
      LiCSBAS05op_clip_unw.py $p05_op 2>&1 | tee -a $log
      if [ ${PIPESTATUS[0]} -ne 0 ];then exit 1; fi
    fi
    ### Update GEOCmldir to be used for following steps
    GEOCmldir="$outGEOCmldir"
  fi
fi

done ##1

### Determine name of TSdir
TSdir="TS_$GEOCmldir"


if [ $start_step -le 11 -a $end_step -ge 11 ];then
  p11_op=""
  if [ ! -z $p11_GEOCmldir ];then p11_op="$p11_op -d $p11_GEOCmldir"; 
    else p11_op="$p11_op -d $GEOCmldir"; fi
  if [ ! -z $p11_TSdir ];then p11_op="$p11_op -t $p11_TSdir"; fi
  if [ ! -z $p11_unw_thre ];then p11_op="$p11_op -u $p11_unw_thre"; fi
  if [ ! -z $p11_coh_thre ];then p11_op="$p11_op -c $p11_coh_thre"; fi
  if [ ! -z $p11_minbtemp ];then p11_op="$p11_op --minbtemp $p11_minbtemp"; fi
  if [ ! -z $p11_maxbtemp ];then p11_op="$p11_op --minbtemp $p11_maxbtemp"; fi
  if [ $p11_sbovl == "y" ];then p11_op="$p11_op --sbovl"; fi
  if [ $p11_s_param == "y" ];then p11_op="$p11_op -s"; fi
  if [ $check_only == "y" ];then
    echo "LiCSBAS11_check_unw.py $p11_op"
  else
    LiCSBAS11_check_unw.py $p11_op 2>&1 | tee -a $log
    if [ ${PIPESTATUS[0]} -ne 0 ];then exit 1; fi
  fi
fi

if [ $start_step -le 12 -a $end_step -ge 12 ];then
  if [ "$cometdev" -eq 1 ] || [ "$p120_sbovl" == "y" ]; then
    p120_use='y'
  fi
  if [ $p120_use == "y" ]; then
    dirset="-c $GEOCmldir -d $GEOCmldir -t $TSdir "
    extra=""
    if [ $p120_ignoreconncomp == "y" ]; then
        extra="--ignore_comp"
    fi
    if [ $p120_sbovl == "y" ]; then
      extra="--sbovl"
    fi
    if [ $check_only == "y" ];then
      echo "LiCSBAS120_choose_reference.py $dirset "$extra
    else
      LiCSBAS120_choose_reference.py $dirset $extra 2>&1 | tee -a $log
      if [ ${PIPESTATUS[0]} -ne 0 ];then echo "WARNING, LiCSBAS120 failed. Reverting to original LiCSBAS ref selection"; fi; #exit 1; fi # this often fails, so only warning message
    fi
  fi

  if [ $p120_sbovl != "y" ]; then
      p12_op=""
      if [ $cometdev -eq 1 ]; then
         p12_nullify="y"
      fi
      if [ ! -z $p12_GEOCmldir ];then p12_op="$p12_op -d $p12_GEOCmldir"; 
        else p12_op="$p12_op -d $GEOCmldir"; fi
      if [ ! -z $p12_TSdir ];then p12_op="$p12_op -t $p12_TSdir"; fi
      if [ ! -z $p12_loop_thre ];then p12_op="$p12_op -l $p12_loop_thre"; fi
      if [ $p12_multi_prime == "y" ];then p12_op="$p12_op --multi_prime"; fi
      if [ $p12_nullify == "y" ];then p12_op="$p12_op --nullify"; fi
      if [ $p12_skippngs == "y" ];then p12_op="$p12_op --nopngs"; fi
      if [ ! -z $p12_rm_ifg_list ];then p12_op="$p12_op --rm_ifg_list $p12_rm_ifg_list"; fi
      if [ ! -z $p12_n_para ];then p12_op="$p12_op --n_para $p12_n_para";
      elif [ ! -z $n_para ];then p12_op="$p12_op --n_para $n_para";fi
    
      if [ $check_only == "y" ];then
        echo "LiCSBAS12_loop_closure.py $p12_op "
      else
        LiCSBAS12_loop_closure.py $p12_op 2>&1 | tee -a $log
        if [ ${PIPESTATUS[0]} -ne 0 ];then exit 1; fi
      fi
      # 2024/11/13: updated nullification may cause extra all-nans-in-ref area. Workaround - update reference point.
      # Forcing this to always use p120 ..
      if [ $p12_nullify == "y" ];then
      #if [ $p120_use == "y" ]; then
        dirset="-c $GEOCmldir -d $GEOCmldir -t $TSdir "
        extra=""
        if [ $p120_ignoreconncomp == "y" ]; then
            extra="--ignore_comp"
        fi
        if [ $check_only == "y" ];then
          echo "LiCSBAS120_choose_reference.py $dirset "$extra
        else
          LiCSBAS120_choose_reference.py $dirset $extra 2>&1 | tee -a $log
          if [ ${PIPESTATUS[0]} -ne 0 ];then echo "WARNING, LiCSBAS120 failed. Reverting to original LiCSBAS ref selection"; fi; #
          # if [ ${PIPESTATUS[0]} -ne 0 ];then exit 1; fi
        fi
      #fi
      fi
    fi
fi

if [ $start_step -le 13 -a $end_step -ge 13 ];then
  # getting eq offsets here:
  if [ "$eqoffs" == "y" -a $eqoffs_minmag -gt 0 ]; then
    extra='-M '$eqoffs_minmag
    extra=$extra' -t '$TSdir
    extra=$extra' -o '$eqoffs_txtfile
    extra=$extra' --buffer '$eqoffs_buffer
    if [ "$check_only" == "y" ];then
      echo "LiCSBAS_get_eqoffsets.py $extra"
    else
      LiCSBAS_get_eqoffsets.py $extra
    fi
  fi
  p13_op=""
  if [ ! -z "$p13_GEOCmldir" ];then p13_op="$p13_op -d $p13_GEOCmldir";
    else p13_op="$p13_op -d $GEOCmldir"; fi
  if [ ! -z "$p13_TSdir" ];then p13_op="$p13_op -t $p13_TSdir"; fi
  if [ ! -z "$p13_inv_alg" ];then p13_op="$p13_op --inv_alg $p13_inv_alg"; fi
  if [ ! -z "$p13_mem_size" ];then p13_op="$p13_op --mem_size $p13_mem_size"; fi
  if [ ! -z "$p13_gamma" ];then p13_op="$p13_op --gamma $p13_gamma"; fi
  if [ ! -z "$p13_inputunit" ];then p13_op="$p13_op --input_units $p13_inputunit"; fi
  if [ ! -z "$p13_n_para" ];then p13_op="$p13_op --n_para $p13_n_para";
    elif [ ! -z "$n_para" ];then p13_op="$p13_op --n_para $n_para"; fi
  if [ ! -z "$p13_n_unw_r_thre" ];then p13_op="$p13_op --n_unw_r_thre $p13_n_unw_r_thre"; fi
  if [ "$p13_keep_incfile" == "y" ];then p13_op="$p13_op --keep_incfile"; fi
  if [ "$p13_nullify_noloops" == "y" ];then p13_op="$p13_op --nullify_noloops"; fi
  if [ "$p13_singular" == "y" ];then p13_op="$p13_op --singular"; fi
  if [ "$p13_sbovl" == "y" ];then p13_op="$p13_op --sbovl"; fi
  if [ "$p13_singular_gauss" == "y" ];then p13_op="$p13_op --singular_gauss"; fi
  if [ "$p13_skippngs" == "y" ];then p13_op="$p13_op --nopngs"; fi
  if [ "$gpu" == "y" ];then p13_op="$p13_op --gpu"; fi

  if [ "$cometdev" -eq 1 ];then
      extra='--nopngs'
      if [ -z "$p13_n_unw_r_thre" ];then extra="$extra --n_unw_r_thre 0.4"; fi
      extra="$extra --singular_gauss"
    else
      extra=''
  fi

  if [ "$eqoffs" == "y" ]; then
    touch $eqoffs_txtfile # just in case it would fail earlier
    extra='--offsets '$eqoffs_txtfile
  fi


  if [ "$check_only" == "y" ];then
    echo "LiCSBAS13_sb_inv.py $extra $p13_op"
  else
    LiCSBAS13_sb_inv.py $extra $p13_op 2>&1 | tee -a $log
    pstat=(${PIPESTATUS[0]})

    if [ "$p12_nullify" == "y" ];then
      if [ $pstat -ne 0 ];then
        echo "Fixing the unresolved-yet issue with NaNs in ref area by just rerunning step 13"
        LiCSBAS13_sb_inv.py $extra $p13_op 2>&1 | tee -a $log
        pstat=(${PIPESTATUS[0]})
      fi
    fi

    if [ $pstat -ne 0 ];then exit 1; fi
  fi
fi

if [ $start_step -le 14 -a $end_step -ge 14 ];then
  p14_op=""
  if [ ! -z $p14_TSdir ];then p14_op="$p14_op -t $p14_TSdir";
    else p14_op="$p14_op -t $TSdir"; fi
  if [ ! -z $p14_mem_size ];then p14_op="$p14_op --mem_size $p14_mem_size"; fi
  if [ $gpu == "y" ];then p14_op="$p14_op --gpu"; fi
  if [ "$eqoffs" == "y" ]; then
    # we then do not want to regenerate vstd
    extra='--skipexisting'
  else
    extra=''
  fi
  if [ $check_only == "y" ];then
    echo "LiCSBAS14_vel_std.py $extra $p14_op"
  else
    LiCSBAS14_vel_std.py $extra $p14_op 2>&1 | tee -a $log
    if [ ${PIPESTATUS[0]} -ne 0 ];then exit 1; fi
  fi
fi

if [ $start_step -le 15 -a $end_step -ge 15 ];then
  p15_op=""
  if [ ! -z "$p15_TSdir" ];then p15_op="$p15_op -t $p15_TSdir";
    else p15_op="$p15_op -t $TSdir"; fi
  if [ ! -z "$p15_coh_thre" ];then p15_op="$p15_op -c $p15_coh_thre"; fi
  if [ ! -z "$p15_n_unw_r_thre" ];then p15_op="$p15_op -u $p15_n_unw_r_thre"; fi
  if [ ! -z "$p15_vstd_thre" ];then p15_op="$p15_op -v $p15_vstd_thre"; fi
  if [ ! -z "$p15_maxTlen_thre" ];then p15_op="$p15_op -T $p15_maxTlen_thre"; fi
  if [ ! -z "$p15_n_gap_thre" ];then p15_op="$p15_op -g $p15_n_gap_thre"; fi
  if [ ! -z "$p15_stc_thre" ];then p15_op="$p15_op -s $p15_stc_thre"; fi
  if [ ! -z "$p15_n_ifg_noloop_thre" ];then p15_op="$p15_op -i $p15_n_ifg_noloop_thre"; fi
  if [ ! -z "$p15_n_loop_err_thre" ];then p15_op="$p15_op -l $p15_n_loop_err_thre"; fi
  if [ ! -z "$p15_n_loop_err_ratio_thre" ];then p15_op="$p15_op -L $p15_n_loop_err_ratio_thre"; fi
  if [ ! -z "$p15_avg_phasebias" ] && [ "$p15_sbovl" != "y" ];then p15_op="$p15_op --avg_phase_bias $p15_avg_phasebias"; fi
  if [ ! -z "$p15_resid_rms_thre" ];then p15_op="$p15_op -r $p15_resid_rms_thre"; fi
  if [ ! -z "$p15_vmin" ];then p15_op="$p15_op --vmin $p15_vmin"; fi
  if [ ! -z "$p15_vmax" ];then p15_op="$p15_op --vmax $p15_vmax"; fi
  if [ "$p15_keep_isolated" == "y" ];then p15_op="$p15_op --keep_isolated"; fi
  if [ "$p15_noautoadjust" == "y" ];then p15_op="$p15_op --noautoadjust"; fi
  if [ "$p15_sbovl" == "y" ];then p15_op="$p15_op --sbovl"; fi
  if [ "$p15_n_gap_use_merged" == "y" ];then p15_op="$p15_op --n_gap_use_merged"; fi

  if [ "$check_only" == "y" ];then
    echo "LiCSBAS15_mask_ts.py $p15_op"
  else
    LiCSBAS15_mask_ts.py $p15_op 2>&1 | tee -a $log
    if [ ${PIPESTATUS[0]} -ne 0 ];then exit 1; fi
  fi
fi

if [ $start_step -le 16 -a $end_step -ge 16 ];then
  p16_op=""
  if [ ! -z "$p16_TSdir" ];then p16_op="$p16_op -t $p16_TSdir";
    else p16_op="$p16_op -t $TSdir"; fi
  if [ ! -z "$p16_filtwidth_km" ];then p16_op="$p16_op -s $p16_filtwidth_km"; fi
  if [ ! -z "$p16_filtwidth_yr" ];then p16_op="$p16_op -y $p16_filtwidth_yr"; fi
  if [ ! -z "$p16_deg_deramp" ];then p16_op="$p16_op -r $p16_deg_deramp"; fi
  if [ "$p16_demerr" == "y" ];then p16_op="$p16_op --demerr"; fi
  if [ "$p16_hgt_linear" == "y" ];then p16_op="$p16_op --hgt_linear"; fi
  if [ ! -z "$p16_hgt_min" ];then p16_op="$p16_op --hgt_min $p16_hgt_min"; fi
  if [ ! -z "$p16_hgt_max" ];then p16_op="$p16_op --hgt_max $p16_hgt_max"; fi
  if [ "$p16_nomask" == "y" ];then p16_op="$p16_op --nomask"; fi
  if [ ! -z "$p16_n_para" ];then p16_op="$p16_op --n_para $p16_n_para";
    elif [ ! -z "$n_para" ];then p16_op="$p16_op --n_para $n_para";fi
  if [ ! -z "$p16_range" ];then p16_op="$p16_op --range $p16_range"; fi
  if [ ! -z "$p16_range_geo" ];then p16_op="$p16_op --range_geo $p16_range_geo"; fi
  if [ ! -z "$p16_ex_range" ];then p16_op="$p16_op --ex_range $p16_ex_range"; fi
  if [ ! -z "$p16_ex_range_geo" ];then p16_op="$p16_op --ex_range_geo $p16_ex_range_geo"; fi
  if [ "$p16_interpolate_nans" == "y" ] && [ "$p16_sbovl" != "y" ];then p16_op="$p16_op --interpolate_nans"; fi
  if [ "$p16_sbovl" == "y" ];then p16_op="$p16_op --sbovl"; fi
  if [ "$p16_skippngs" == "y" ];then p16_op="$p16_op --nopngs"; fi

  if [ "$eqoffs" == "y" ]; then
    extra='--from_model '$TSdir/model.h5
  else
    extra=''
  fi

  if [ "$check_only" == "y" ];then
    echo "LiCSBAS16_filt_ts.py $extra $p16_op"
  else
    LiCSBAS16_filt_ts.py $extra $p16_op 2>&1 | tee -a $log
    if [ ${PIPESTATUS[0]} -ne 0 ];then exit 1; fi
  fi
fi

if [ $check_only == "y" ];then
  echo ""
  echo "Above commands will run when you change check_only to \"n\""
  echo ""
fi

