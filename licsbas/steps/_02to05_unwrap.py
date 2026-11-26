#!/usr/bin/env python3
"""

This script unwraps GeoTIFF files of wrapped interferograms, for further time series analysis.
It replaces the original LiCSBAS steps 02-05 (except for 04), as these are done in one go.

NOTE: If your input data are coming from the LiCSAR system, please make sure you did run LiCSBAS01 with parameter --get_pha

====================
Input & output files
====================
Inputs:
 - GEOC/    
   - yyyymmdd_yyyymmdd/
     - yyyymmdd_yyyymmdd.geo.diff_unfiltered_pha.tif
    [- yyyymmdd_yyyymmdd.geo.diff_pha.tif]
     - yyyymmdd_yyyymmdd.geo.cc.tif
  [- *.geo.mli.tif]
  [- *.geo.hgt.tif]
  [- *.geo.[E|N|U].tif]
  [- baselines]
  [- metadata.txt]
[- GEOC.MLI/]
  [- yyyymmdd/yyyymmdd.geo.mli.tif]
[- GACOS/]
  [- yyyymmdd/yyyymmdd.geo.sltd.tif]


Outputs in GEOCmlX[GACOS][clip]:
 - yyyymmdd_yyyymmdd/
   - yyyymmdd_yyyymmdd.unw[.png] (float32)
   - yyyymmdd_yyyymmdd.cc (uint8)
   - yyyymmdd_yyyymmdd.conncomp (uint8)
   - [yyyymmdd_yyyymmdd.gacos.png] (if --gacos: before/after GACOS correction QC plot, 03op_GACOS style)
 - baselines (may be dummy)
 - EQA.dem_par
 - slc.mli.par
 - slc.mli[.png] (if input exists)
 - hgt[.png] (if input exists)
 - [E|N|U].geo (if input exists)
 - [GACOS_info2.png / GACOS_info2.txt] (if --gacos: per-pair STD before/after GACOS correction)

=====
Usage
=====
LiCSBAS02to05_unwrap.py -i WORKdir [-M nlook] [-g lon1/lon2/lat1/lat2] [--filter gold|gauss|adf] [--gacos] [--hgtcorr] [--cascade/--cascade_full] [--thres float] [--freq float] [--n_para int] [--nolandmask]

 -i  <str> Path to the work directory (i.e. folder that contains the input GEOC dir with the stack of geotiff data, and optionally other dirs: GEOC.MLI, GACOS)
 -M  <int> Number of multilooking factor (Default: 10, 10x10 multilooking)
 -g  <str> Range to be clipped in geographical coordinates (deg), as lon1/lon2/lat1/lat2
 --filter <str>  Spatial filter to support primary unwrapping and to estimate consistence (Default: Goldstein)
   gold:   Adapted implementation of the Goldstein filter, consistence estimated as FFT spectral magnitude
   gauss:  A 2-D Gaussian kernel filter, consistence estimated based on filter residuals. Fast solution, not recommended for high phase gradients
   adf:    Use of ADF2 for the adaptive filter implemented by GAMMA software (if available), ADF-coherence applied as consistence
 --gacos   Use GACOS data (recommended, expects GACOS folder - see LiCSBAS_01_get_geotiff.py). Note this will limit dataset to epochs with GACOS correction.
 --hgtcorr Apply height-correlation correction (default: not apply). Note this will be turned off if GACOS is to be used.
 --cascade  Apply cascade unwrapping approach: 1 cascade with 10xML layer (recommended)
 --cascade_full Apply full cascade unwrapping approach: 3 cascade steps through 10-5-3xML layers (experimental)
 --thres <float> Threshold value for masking noise based on consistence (Default: 0.3)
 --freq <float>   Radar frequency in Hz (Default: 5.405e9 for Sentinel-1)
           (e.g., 1.27e9 for ALOS, 1.2575e9 for ALOS-2/U, 1.2365e9 for ALOS-2/{F,W})
 --n_para <int> Number of parallel processing (Default: # of usable CPU)
 --nolandmask Do not apply landmask (ON by default)
 --nopngs  This would skip generating unw previews
 
The command will run reunwrapping on interferograms inside WORKdir/GEOC.
Outputs are stored inside WORKdir/GEOCmlX[GACOS][clip] where X is the multilooking factor (-M).
For more information about the procedure, see e.g. https://ieeexplore.ieee.org/document/9884337
"""
#%% Change log
'''
vXX 20240205 ML
 - 'almost' full lics_unwrap functionality (incl. ADF)
v1.14.2 20230628 Milan Lazecky, UniLeeds
 - initial version using previously developed lics_unwrap functions
'''


#%% Import
from licsbas.meta import *
import getopt
import os, shutil, glob
import sys
import time
import numpy as np
import multiprocessing as multi
import cmcrameri.cm as cmc #SCM
from licsbas import io_lib
from licsbas import plot_lib

# but should cancel if there is no snaphu installed (checked at runtime in main())
def _require_snaphu():
    if os.system('which snaphu >/dev/null 2>/dev/null') != 0:
        print('snaphu not detected. please install it yourself, e.g. from:')
        print('https://web.stanford.edu/group/radar/softwareandlinks/sw/snaphu')
        sys.exit(1)


try:
    import lics_unwrap as unw
except ImportError:
    try:
        from licsar_extra import lics_unwrap as unw
    except ImportError:
        unw = None  # licsar_extra not installed (optional: pip install .[unwrap])


def _require_licsar_extra():
    if unw is None:
        print('ERROR: lics_unwrap library not found.')
        print('please install from https://github.com/comet-licsar/licsar_extra')
        print('e.g.:')
        print("pip install 'licsbas[unwrap]'")
        print('or (clearer):')
        print('pip install --upgrade git+https://github.com/comet-licsar/licsar_extra.git')
        sys.exit(1)


class Usage(Exception):
    """Usage context manager"""
    def __init__(self, msg):
        self.msg = msg


#%% GACOS correction plots (standard LiCSBAS style, generated post-hoc)
def _find_gacos_tif(gacosdir, date):
    """Locate the sltd geo-tif for ``date`` inside a GACOS dir (a few common layouts)."""
    cands = [
        os.path.join(gacosdir, date + '.sltd.geo.tif'),
        os.path.join(gacosdir, date, date + '.sltd.geo.tif'),
        os.path.join(gacosdir, date, date + '.geo.sltd.tif'),
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def _parallel_map(func, tasks, nproc):
    if nproc > 1 and len(tasks) > 1:
        with multi.Pool(processes=min(nproc, len(tasks))) as pool:
            return pool.map(func, tasks)
    return [func(task) for task in tasks]


def _plot_unw_preview(task):
    unwfile, length, width, cycle = task
    pairstr = os.path.basename(unwfile).split('.')[0]
    unwdata = np.fromfile(unwfile, dtype=np.float32).reshape(length, width)
    unwpngfile = unwfile + '.png'
    plot_lib.make_im_png(np.angle(np.exp(1j * unwdata / cycle) * cycle), unwpngfile,
                         cmc.romaO, pairstr, vmin=-np.pi, vmax=np.pi, cbar=False)


def plot_unw_previews(outdir, nproc = 1):
    mlipar = os.path.join(outdir, 'slc.mli.par')
    if not os.path.exists(mlipar):
        print('ERROR: No slc.mli.par file exists in ' + outdir)
        return 2
    #
    width = int(io_lib.get_param_par(mlipar, 'range_samples'))
    length = int(io_lib.get_param_par(mlipar, 'azimuth_lines'))
    #
    speed_of_light = 299792458  # m/s
    radar_frequency = float(io_lib.get_param_par(mlipar, 'radar_frequency'))  # Hz
    wavelength = speed_of_light / radar_frequency  # meter
    if wavelength > 0.2:  ## L-band
        cycle = 1.5  # 2pi/cycle for png
    else:  ## C-band
        cycle = 3  # 2pi*3/cycle for png
    tasks = [(unwfile, length, width, cycle)
             for unwfile in glob.glob(outdir+'/*/*.unw')]
    _parallel_map(_plot_unw_preview, tasks, nproc)
    return 0


def _plot_gacos_correction(task):
    pair, outdir, t1, t2, ml, cliparea_geo, nx, ny, cycle = task
    try:
        unwf = np.fromfile(os.path.join(outdir, pair, pair + '.unw'),
                           dtype=np.float32).reshape(ny, nx)
        unw_after = np.where(unwf == 0, np.nan, unwf)
        # Use the same lics_unwrap helpers as unwrapping to preserve the output grid.
        dsltd = unw.load_tif2xr(t2, cliparea_geo=cliparea_geo) \
                - unw.load_tif2xr(t1, cliparea_geo=cliparea_geo)
        dsltd = unw.multilook_xrda(dsltd, ml=ml, coords=('lon', 'lat')).where(dsltd != 0)
        dsltd = dsltd.values
        if tuple(dsltd.shape) != (ny, nx):
            print('WARNING: pair {}: dsltd shape {} != unw {} - skipping plot'.format(
                pair, dsltd.shape, (ny, nx)))
            return None
        # 03op convention: unw_after = unw_before - dsltd  ->  before = after + dsltd
        unw_before = unw_after + dsltd
        std_bef = float(np.nanstd(unw_before))
        std_aft = float(np.nanstd(unw_after))
        rate = (std_bef - std_aft) / std_bef * 100.0 if std_bef > 0 else 0.0
        data3 = [np.angle(np.exp(1j * (data / cycle)) * cycle)
                 for data in (unw_before, unw_after, dsltd)]
        title3 = ['unw_org (STD: {:.1f} rad)'.format(std_bef),
                  'unw_cor (STD: {:.1f} rad)'.format(std_aft),
                  'dsltd ({:.1f}% reduced)'.format(rate)]
        pngfile = os.path.join(outdir, pair, pair + '.gacos.png')
        plot_lib.make_3im_png(data3, pngfile, cmc.romaO, title3,
                              vmin=-np.pi, vmax=np.pi, cbar=False)
        return [pair, std_bef, std_aft, rate]
    except Exception as ex:
        print('WARNING: GACOS correction plot for pair {} failed: {}'.format(pair, ex))
        return None


def plot_gacos_corrections(outdir,
                           gacosdir,
                           ml,
                           cliparea_geo=None,
                           nproc = 1):
    """Generate the standard LiCSBAS-style per-ifg GACOS correction plots
    (``pair.gacos.png`` 3-panel before/after/difference, plus a per-ifg STD
    before/after ``GACOS_info2.png`` / ``.txt``).

    The 02to05 chain applies GACOS *during* unwrapping (inside
    ``licsar_extra.lics_unwrap``, which exports only the corrected
    ``pair.unw``), so the correction plots normally produced by
    ``LiCSBAS03op_GACOS.py`` are built here post-hoc - using the exported
    products and the same lics_unwrap helpers for multilook/clip (same grid
    as ``pair.unw``), i.e. without modifying licsar_extra.
    All failures are non-fatal: these are QC plots only.
    """
    import re
    if unw is None:
        print('skip GACOS correction plots: licsar_extra (lics_unwrap) not available?')
        return
    try:
        from licsbas import plot_lib, io_lib
        import cmcrameri.cm as cmc
    except ImportError as e:
        print('skip GACOS correction plots (missing dependency: {})'.format(e))
        return
    parfile = os.path.join(outdir, 'slc.mli.par')
    if not os.path.exists(parfile):
        print('skip GACOS correction plots: '+parfile+' not found')
        return
    try:
        nx = int(io_lib.get_param_par(parfile, 'range_samples'))
        ny = int(io_lib.get_param_par(parfile, 'azimuth_lines'))
    except Exception as e:
        print('skip GACOS correction plots: cannot read slc.mli.par ({})'.format(e))
        return
    #
    speed_of_light = 299792458  # m/s
    radar_frequency = float(io_lib.get_param_par(parfile, 'radar_frequency'))  # Hz
    wavelength = speed_of_light / radar_frequency  # meter
    if wavelength > 0.2:  ## L-band
        cycle = 1.5  # 2pi/cycle for png
    else:  ## C-band
        cycle = 3  # 2pi*3/cycle for png
    pairs = [d for d in sorted(os.listdir(outdir))
             if re.fullmatch(r'\d{8}_\d{8}', d)
             and os.path.exists(os.path.join(outdir, d, d + '.unw'))]
    tasks = []
    for pair in pairs:
        e1, e2 = pair.split('_')
        t1 = _find_gacos_tif(gacosdir, e1)
        t2 = _find_gacos_tif(gacosdir, e2)
        if t1 is None or t2 is None:
            continue
        tasks.append((pair, outdir, t1, t2, ml, cliparea_geo, nx, ny, cycle))
    info_rows = [row for row in _parallel_map(_plot_gacos_correction, tasks, nproc)
                 if row is not None]
    if info_rows:
        infofile = os.path.join(outdir, 'GACOS_info2.txt')
        with open(infofile, 'w') as f:
            f.write('pair\tstd_before_rad\tstd_after_rad\treduction_pct\n')
            for pair, sb, sa, rt in info_rows:
                f.write('{}\t{:.3f}\t{:.3f}\t{:.1f}\n'.format(pair, sb, sa, rt))
        try:
            plot_lib.plot_gacos_info2(infofile, os.path.join(outdir, 'GACOS_info2.png'),
                                      label='GACOS correction (02to05 re-unwrapping)')
        except Exception as ex:
            print('WARNING: GACOS_info2.png plot failed: {}'.format(ex))
    print('GACOS correction plots written for {}/{} pairs'.format(len(info_rows), len(pairs)))


#%% Main
def main(argv=None):
    _require_licsar_extra()
    _require_snaphu()
    
    #%% Check argv
    if argv == None:
        argv = sys.argv
    
    start = time.time()
    ver="1.14.2"; date='2023-06-28'; author="M. Lazecky"
    print("\n{} ver{} {} {}".format(os.path.basename(argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(argv[0]), ' '.join(argv[1:])), flush=True)
    
    #%% Set default
    workdir = []
    ml = 10
    freq = 5405000000
    thres = 0.3
    cliparea_geo = None
    cascade = False
    only10 = True
    hgtcorr = False
    gacoscorr = False
    do_landmask = True
    spfilter = 'gold'
    create_unw_previews = True

    try:
        nproc = len(os.sched_getaffinity(0))
    except:
        nproc = multi.cpu_count()
    
    #%% Read options
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hi:g:M:", ["help", "gacos", "nopngs", "hgtcorr", "cascade", "cascade_full", "filter=","nolandmask", "thres=", "freq=", "n_para="])
        except getopt.error as msg:
            raise Usage(msg)
        for o, a in opts:
            if o == '-h' or o == '--help':
                print(__doc__)
                return 0
            elif o == '-i':
                workdir = os.path.realpath(a)
            elif o == '-M':
                ml = int(a)
            elif o == '-g':
                cliparea_geo = a
            elif o == '--thres':
                thres = float(a)
            elif o == '--gacos':
                gacoscorr = True
            elif o =='--filter':
                spfilter = a
            elif o == '--hgtcorr':
                hgtcorr = True
            elif o == '--nolandmask':
                do_landmask = False
            elif o == '--cascade':
                cascade = True
                only10 = True
            elif o == '--cascade_full':
                if cascade:
                    print('both cascade params set. Prioritising the cascade_full param')
                cascade = True
                only10 = False
            elif o == '--freq':
                freq = float(a)
            elif o == '--n_para':
                nproc = int(a)
            elif o == '--nopngs':
                create_unw_previews = False
        
        if not workdir:
            raise Usage('No WORK directory given, -d is not optional!')
        elif not os.path.isdir(workdir):
            raise Usage('No {} dir exists!'.format(workdir))
        elif not os.path.isdir(os.path.join(workdir, 'GEOC')):
            raise Usage('No GEOC dir exists in {}!'.format(workdir))
        if gacoscorr and not os.path.exists(os.path.join(workdir, 'GACOS')):
            raise Usage('No GACOS dir exists in {} but use of GACOS turned on!'.format(workdir))
        if spfilter not in ['gold', 'gauss', 'adf']:
            raise Usage("Wrong filtering option set - only 'gold', 'gauss', or 'adf' are available")
        if spfilter == 'adf':
            # check for gamma commands
            if os.system('which adf2 >/dev/null 2>/dev/null') != 0:
                raise Usage('ERROR: GAMMA SW not found, cancelling')
    except Usage as err:
        print("\nERROR:", file=sys.stderr, end='')
        print("  "+str(err.msg), file=sys.stderr)
        print("\nFor help, use -h or --help.\n", file=sys.stderr)
        return 2
    
    if gacoscorr and hgtcorr:
        print('WARNING, both GACOS and DEM-correlated signal corrections are ON. Turning hgtcorr OFF.')
        hgtcorr = False
    
    # just run the existing script, but it expects being inside the directory with the GEOC folder!
    os.chdir(workdir)
    outdir = 'GEOCml'+str(ml)
    if gacoscorr:
        outdir=outdir+'GACOS'
    if cliparea_geo:
        outdir=outdir+'clip'
    outdir = os.path.join(workdir, outdir)
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    os.chdir(outdir) # need to run the processing here..
    # about the filters
    if spfilter == 'gauss':
        goldstein = False
        use_gamma = False
        smooth = True
    elif spfilter == 'gold':
        goldstein = True
        use_gamma = False
        smooth = False
    elif spfilter == 'adf':
        goldstein = True
        use_gamma = True
        smooth = False
    print('Running unwrapping using given parameters')
    unw.process_frame(ml = ml, thres = thres, cliparea_geo = cliparea_geo, 
                cascade=cascade, only10 = only10,
                hgtcorr = hgtcorr, gacoscorr = gacoscorr,
                nproc = nproc, freq=freq,
                # if smooth, combine with filtered ifgs
                goldstein = goldstein, smooth = smooth, use_gamma = use_gamma,
                prefer_unfiltered = True, # UNFILTERED SEEM ALWAYS BETTER!!! # TODO ?
                # keeping the 'not-to-be-changed'defaults:
                lowpass = False, defomax = 0.3, dolocal = True, frame = 'dummy', specmag = True,
                pairsetfile = None, subtract_gacos = True, export_to_tif = False,
                keep_coh_debug = True, use_amp_coh = False, use_coh_stab = False,
                use_amp_stab = False, gacosdir = '../GACOS', do_landmask = do_landmask)
    
    #%% Generate the standard LiCSBAS-style GACOS correction plots (post-hoc,
    #%% same style as LiCSBAS03op_GACOS), because lics_unwrap applies the
    #%% correction internally and does not export the plots itself.
    os.chdir(workdir)
    # clean residual tmp folders
    for tmpdir in glob.glob(outdir + '/*/tmp*'):
        shutil.rmtree(tmpdir)

    # create previews
    if create_unw_previews:
        print('Creating preview images for unwrapped data')
        plot_unw_previews(outdir, nproc=nproc)
        if gacoscorr:
            print('Creating GACOS preview images')
            try:
                plot_gacos_corrections(outdir, os.path.join(workdir, 'GACOS'), ml, cliparea_geo, nproc)
            except Exception as ex:
                print('WARNING: GACOS correction plotting failed: {}'.format(ex))

    #%% Finish
    elapsed_time = time.time()-start
    hour = int(elapsed_time/3600)
    minite = int(np.mod((elapsed_time/60),60))
    sec = int(np.mod(elapsed_time,60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour,minite,sec))
    
    print('\n{} Successfully finished!!\n'.format(os.path.basename(argv[0])))
    print('Output directory: {}\n'.format(os.path.relpath(outdir)))


#%% main
if __name__ == "__main__":
    sys.exit(main())
