#!/usr/bin/env python3
"""
========
Overview
========
Python3 library of time series inversion functions for LiCSBAS.

=========
Changelog
=========
20250114 ML
 - rearrange singular* to allow WLS
20241207 ML
 - added Gaussian kernel-based gapfilling. partly blindly, need checks
20241020 ML
 - added calc with offset dates
20240930 ML
 - (finally) found the bug causing nans in inversion of some datasets. Fixed by removing the scipy.sparse functionality. Perhaps just csr_array would do or other tweaking?
20240423 ML
 - parallelised singular (with correct vel/vconst estimates)
20231101 Yasser Maghsoudi (and ML), Uni Leeds
 - changed least squares function from np to scipy.sparse for faster NSBAS inversion
v1.5.2 20211122 Milan Lazecky, Uni Leeds
 - use bit more economic computations (for tutorial purposes)
v1.5.1 20210309 Yu Morishita, GSI
 - Add GPU option into calc_velstd_withnan and calc_stc
v1.5 20210305 Yu Morishita, GSI
 - Add GPU option into invert_nsbas
v1.4.2 20201118 Yu Morishita, GSI
 - Again Bug fix of multiprocessing
v1.4.1 20201116 Yu Morishita, GSI
 - Bug fix of multiprocessing in Mac python>=3.8
v1.4 20200703 Yu Morishita, GSI
 - Replace problematic terms
v1.3 20200103 Yu Morishita, Uni of Leeds and GSI
 - Bag fix in calc_stc (return nonzero even if two adjacent pixels have identical ts)
v1.2 20190823 Yu Morishita, Uni of Leeds and GSI
 - Bag fix in calc_velstd_withnan
 - Remove calc_velstd
v1.1 20190807 Yu Morishita, Uni of Leeds and GSI
 - Add calc_velsin
v1.0 20190730 Yu Morishita, Uni of Leeds and GSI
 - Original implementation
"""

import warnings
import numpy as np
import datetime as dt
import multiprocessing as multi
from astropy.stats import bootstrap
from astropy.utils import NumpyRNGContext
#from scipy.sparse.linalg import lsqr as sparselsq
#from scipy.sparse.linalg import lsmr as sparselsq
#from scipy.sparse import csr_array, csc_array  # csr_matrix, csc_matrix # but maybe coo_matrix would be better for G? to be checked
import LiCSBAS_tools_lib as tools_lib
try:
    from sklearn.linear_model import RANSACRegressor
except:
    print('not loading RANSAC (optional experimental function)')


#debugmode = True
#print('inversion runs in debug mode - please inform Milan if this works now')

#%%
def make_sb_matrix(ifgdates):
    """
    Make small baseline incidence-like matrix.
    Composed of 1 between primary and secondary. (n_ifg, n_im-1)
    Unknown is incremental displacement.
    """
    imdates = tools_lib.ifgdates2imdates(ifgdates)
    n_im = len(imdates)
    n_ifg = len(ifgdates)

    G = np.zeros((n_ifg, n_im-1), dtype=np.int16)
    for ifgix, ifgd in enumerate(ifgdates):
        primarydate = ifgd[:8]
        primaryix = imdates.index(primarydate)
        secondarydate = ifgd[-8:]
        secondaryix = imdates.index(secondarydate)
        G[ifgix, primaryix:secondaryix] = 1

    return G


#%%
def make_sb_matrix2(ifgdates):
    """
    Make small baseline incidence-like matrix.
    Composed of -1 at primary and 1 at secondary. (n_ifg, n_im)
    Unknown is cumulative displacement.
    """
    imdates = tools_lib.ifgdates2imdates(ifgdates)
    n_im = len(imdates)
    n_ifg = len(ifgdates)

    A = np.zeros((n_ifg, n_im), dtype=np.int16)
    for ifgix, ifgd in enumerate(ifgdates):
        primarydate = ifgd[:8]
        primaryix = imdates.index(primarydate)
        secondarydate = ifgd[-8:]
        secondaryix = imdates.index(secondarydate)
        A[ifgix, primaryix] = -1
        A[ifgix, secondaryix] = 1
    return A


def invert_unws(unw, G, dt_cum, gamma, n_core, gpu, dt_offsets = None,
                wvars = None, method = 'nsbas', inv_alg = 'LS'):
    ''' Passing to the requested inversion method.

    Inputs:
      unw : Unwrapped data block for each point (n_pt, n_ifg)
            Still include nan to keep dimension
      G    : Design matrix (1 between primary and secondary) (n_ifg, n_im-1)
      dt_cum : Cumulative years(or days) for each image (n_im)
      gamma  : Gamma value for NSBAS inversion, should be small enough (e.g., 0.0001)
      n_core : Number of cores for parallel processing
      gpu  : GPU flag
      dt_offsets (None or np.array): Boolean structure. True for im where an offset should be estimated/accounted for
      wvars (None or np.array): variances used to form weights for the (optional) WLS
      method (str): one of following methods: 'nsbas', 'singular', 'singular_gauss', 'only_sb'
      inv_alg (str): either 'LS' or 'WLS'

    Returns:
      inc     : Incremental displacement (n_im-1, n_pt)
      vel     : Velocity (n_pt)
      vconst  : Constant part of linear velocity (c of vt+c) (n_pt)
    '''
    if (gpu and (method[:5] != 'nsbas')):
        print('WARNING, non-NSBAS methods were not tested on GPUs')

    if method == 'nsbas':
        if inv_alg == 'LS':
            return invert_nsbas(unw, G, dt_cum, gamma, n_core, gpu)
        elif inv_alg == 'WLS':
            return invert_nsbas_wls(unw, wvars, G, dt_cum, gamma, n_core)
    elif method == 'only_sb':
        return invert_singular(unw, G, dt_cum, n_core, wvars = wvars, only_sb=True)
    elif method == 'singular_gauss':
        return invert_singular(unw, G, dt_cum, n_core, dt_offsets = dt_offsets, wvars=wvars, singular_gauss = True)
    elif method == 'singular':
        return invert_singular(unw, G, dt_cum, n_core, wvars=wvars, singular_gauss = False)
    else:
        print('ERROR, no implemented method is selected - cancelling (consider this as a BUG)')
        return


def invert_singular(unw, G, dt_cum, n_core, wvars = None, dt_offsets = None,
                    singular_gauss = False, only_sb = False):
    ''' Calculate increment displacement difference by two-stage inversion of SBAS and nan-filling.

    Inputs:
      unw : Unwrapped data block for each point (n_pt, n_ifg)
            Still include nan to keep dimension
      G    : Design matrix (1 between primary and secondary) (n_ifg, n_im-1)
      dt_cum : Cumulative years(or days) for each image (n_im)
      wvars (None or np.array): variances used to form weights for the (optional) WLS (n_pt, n_ifg)
      n_core : Number of cores for parallel processing
      dt_offsets (None or np.array): Boolean structure. True for im where an offset should be estimated/accounted for
      singular_gauss (bool): if True, will use Gauss kernel to estimate missing increments
      only_sb (bool): if True, no nan-filling is performed, only pixels with full networks are inverted
    '''
    #if n_core != 1:
    #    global Gall, unw_tmp, mask ## for para_wrapper
    #global Gall, unw_tmp, var_tmp, mask

    ### Settings
    n_pt, n_ifg = unw.shape
    n_im = G.shape[1]+1

    if type(wvars) != type(None):
        print('\n WARNING: WLS with singular was not really well tested now, 2025-01-14. Inform earmla if bugs happen \n')
        wls=True
    else:
        wls=False

    #if type(dt_offsets) != type(None):
    #    #print('\n WARNING: WLS with singular was not really well tested now, 2025-01-14. Inform earmla if bugs happen \n')
    #    wls=True
    #else:
    #    wls=False
    result = np.zeros((G.shape[1], n_pt), dtype=np.float32) * np.nan

    ### Solve points with full unw data at a time. Very fast.
    bool_pt_full = np.all(~np.isnan(unw), axis=1)
    n_pt_full = bool_pt_full.sum()
    if n_pt_full!=0:
        print('  Solving {0:6}/{1:6}th points with full unw at a time...'.format(n_pt_full, n_pt), flush=True)
        if wls:
            result[:, bool_pt_full] = invert_nsbas_wls(unw[bool_pt_full, :], wvars[bool_pt_full, :], G, dt_cum, 0.0001, n_core)[0]
        else:
            result[:, bool_pt_full] = np.linalg.lstsq(G, unw[bool_pt_full, :].transpose(), rcond=None)[0]

    if only_sb:
        print('skipping nan points, only SB inversion is performed')
    else:
        print('  Next, solve {0} points including nan point-by-point...'.format(n_pt - n_pt_full), flush=True)
        # print('using the singular approach (faster and more suitable for non-linear gap filling)')
        d = unw[~bool_pt_full, :].transpose()
        m = result[:, ~bool_pt_full]
        if wls:
            w = wvars[~bool_pt_full,:].transpose()
        else:
            w = None
        
        if n_core == 1:
            result[:, ~bool_pt_full] = singular_nsbas(d,G,m,dt_cum, w, singular_gauss)
        else:
            print('  {} parallel processing'.format(n_core), flush=True)
            #
            args = [i for i in range(n_pt-n_pt_full)]
            q = multi.get_context('fork')
            p = q.Pool(n_core)
            from functools import partial
            func = partial(singular_nsbas_onepoint, d, G, m, dt_cum, w, singular_gauss)
            _result = p.map(func, args)
            result[:, ~bool_pt_full] = np.array(_result).T
            p.close()

        if singular_gauss:
            print('\n Performing experimental nan-gapfilling using Gaussian kernel in temporal domain \n')
            dtcum_offsets_mask = None
            if type(dt_offsets) != type(None):
                dtcum_offsets_mask = ~dt_offsets
            result[:, ~bool_pt_full] = gauss_fill_gaps_cube_full(result[:, ~bool_pt_full], dt_cum, dtcum_offsets_mask)

    print('\n  Inversion finished - estimating linear trend (velocity) \n', flush=True)

    inc = result
    try:
        ### Cumulative displacememt
        cum = np.zeros((n_im, n_pt), dtype=np.float32)*np.nan
        cum[1:, :] = np.cumsum(inc, axis=0)
        #
        ## Fill 1st image with 0 at unnan points from 2nd images
        bool_unnan_pt = ~np.isnan(cum[1, :])
        cum[0, bool_unnan_pt] = 0
        vel, vconst = calc_vel(cum.T, dt_cum)
    except:
        print('WARNING, some error getting cum/vel/vconst after non-NSBAS inversion')
        print('rolling back to simplified vel estimate (note vconst=0)')
        vel = result.sum(axis=0)/dt_cum[-1]
        vconst = np.zeros_like(vel)

    # now need to return ref area that should be zero, back to zero
    try:
        vel[np.all(cum==0, axis=0)] = 0
        vconst[np.all(cum==0, axis=0)] = 0
    except:
        print('a bug in not-tested return of ref point to zero. should be easy fix (and it actually does not bother)')

    return inc, vel, vconst

#%%
def invert_nsbas(unw, G, dt_cum, gamma, n_core, gpu):
    """
    Calculate increment displacement difference by NSBAS inversion. Points with all unw data are solved by simple SB inversion firstly at a time.

    Inputs:
      unw : Unwrapped data block for each point (n_pt, n_ifg)
            Still include nan to keep dimention
      G    : Design matrix (1 between primary and secondary) (n_ifg, n_im-1)
      dt_cum : Cumulative years(or days) for each image (n_im)
      gamma  : Gamma value for NSBAS inversion, should be small enough (e.g., 0.0001)
      n_core : Number of cores for parallel processing
      gpu  : GPU flag

    Returns:
      inc     : Incremental displacement (n_im-1, n_pt)
      vel     : Velocity (n_pt)
      vconst  : Constant part of linear velocity (c of vt+c) (n_pt)
    """
    if n_core != 1:
        global Gall, unw_tmp, mask ## for para_wrapper

    ### Settings
    n_pt, n_ifg = unw.shape
    n_im = G.shape[1]+1

    # do the original NSBAS inversion
    result = np.zeros((n_im+1, n_pt), dtype=np.float32)*np.nan #[inc, vel, const]

    ### Set matrix of NSBAS part (bottom)
    Gbl = np.tril(np.ones((n_im, n_im-1), dtype=np.float32), k=-1) #lower tri matrix without diag
    Gbr = -np.ones((n_im, 2), dtype=np.float32)
    Gbr[:, 0] = -dt_cum
    Gb = np.concatenate((Gbl, Gbr), axis=1)*gamma
    Gt = np.concatenate((G, np.zeros((n_ifg, 2), dtype=np.float32)), axis=1)
    Gall = np.float32(np.concatenate((Gt, Gb)))

    ### Solve points with full unw data at a time. Very fast.
    bool_pt_full = np.all(~np.isnan(unw), axis=1)
    n_pt_full = bool_pt_full.sum()

    if n_pt_full!=0:
        print('  Solving {0:6}/{1:6}th points with full unw at a time...'.format(n_pt_full, n_pt), flush=True)
        ## Solve
        unw_tmp = np.concatenate((unw[bool_pt_full, :], np.zeros((n_pt_full, n_im), dtype=np.float32)), axis=1).transpose()
        if gpu:
            print('  Using GPU')
            import cupy as cp
            unw_tmp_cp = cp.asarray(unw_tmp)
            Gall_cp = cp.asarray(Gall)
            _sol = cp.linalg.lstsq(Gall_cp, unw_tmp_cp, rcond=None)[0]
            result[:, bool_pt_full] = cp.asnumpy(_sol)
            del unw_tmp_cp, Gall_cp, _sol
        else:
            result[:, bool_pt_full] = np.linalg.lstsq(Gall, unw_tmp, rcond=None)[0]

    print('  Next, solve {0} points including nan point-by-point...'.format(n_pt-n_pt_full), flush=True)
    ### Solve other points with nan point by point.
    ## Not use GPU because lstsq with small matrix is slower than CPU
    unw_tmp = np.concatenate((unw[~bool_pt_full, :], np.zeros((n_pt-n_pt_full, n_im), dtype=np.float32)), axis=1).transpose()
    mask = (~np.isnan(unw_tmp))
    unw_tmp[np.isnan(unw_tmp)] = 0
    if n_core == 1:
        result[:, ~bool_pt_full] = censored_lstsq_slow(Gall, unw_tmp, mask) #(n_im+1, n_pt)
    else:
        print('  {} parallel processing'.format(n_core), flush=True)
        #
        args = [i for i in range(n_pt-n_pt_full)]
        q = multi.get_context('fork')
        p = q.Pool(n_core)
        #if debugmode:
        #A = Gall
        #else:
        #    A = csc_array(Gall)  # or csr?
        _result = p.map(censored_lstsq_slow_para_wrapper, args) #list[n_pt][length]
        result[:, ~bool_pt_full] = np.array(_result).T
        p.close()

    #
    # NSBAS result matrix: last 2 rows are vel and vconst
    inc = result[:n_im-1, :]
    vel = result[n_im-1, :]
    vconst = result[n_im, :]
    return inc, vel, vconst


# orig solution by ML, just instead of full large matrix of increment rows, use only sum and minmax - much faster,
# making the computation linear, out of matrix solution. This may be source of some delays, but gives good opportunity
# to improve e.g. by ... some original thoughts
def singular_nsbas(d,G,m,dt_cum, wvars = None, singular_gauss = False):
    # per each point
    #from scipy.optimize import curve_fit
    #def func_vel(x, a):
    #    return a * x
    #
    for px in range(m.shape[1]):
        #if np.mod(px, 100) == 0:
        #    print('\r  Running {0:6}/{1:6}th point...'.format(px, m.shape[1]), end='', flush=True)
        #
        try:
            m[:,px] = singular_nsbas_onepoint(d,G,m,dt_cum, wvars, singular_gauss, px)
        except:
            print('ERROR inverting point '+str(px)+' - filling by nan values')
            m[:,px] = np.nan
    return m


def gauss_fill_gaps_cube(cusel, dt_cumm, filtwidth_yr, time_diff_sq, isinc = True):
    ''' cusel is 2-D array (cube) of shape (n_im_selected, len_selected). Here we perform the nan filling itself.
    originally for increments only (you can try unset isinc for custom use e.g. on cum)
     it uses similar routine (additional Gaussian kernel-weighted mean) to additionally get LP of previous epoch to get its residual and thus align a bit better.
     Why this? The increment will get cumsummed with previous epoch that contains noise
     Not perfect though. ML, 12/2024'''
    #n_im, length, width = cusel.shape
    dtnanposition = np.where(time_diff_sq==0)[0][0] # dtnanposition is the date index from dt_cum for which we do the estimate
    prevepochdata = cusel[dtnanposition - 1, :]
    len_sel = cusel.shape[1]
    if isinc:
        # in such case we center the time diffs between epochs as that's where the weights should be guided
        dt_cum = dt_cumm - np.append(0, np.diff(dt_cumm) / 2)
        # and we need to recalculate the weights
        time_diff_sq = (dt_cum[dtnanposition] - dt_cum) ** 2
        # getting increment per day - squeezing the matrix..
        diffdt = np.tile(np.diff(dt_cumm)[:, np.newaxis], (1, len_sel))
        cusel = cusel[1:, :] / diffdt
        # as we squeeze cusel, need to update positioning
        dtnanposition -= 1
        # n_im_sel -= 1
        dtstartpos = 1
    else:
        dt_cum = dt_cumm.copy()
        dtstartpos = 0
    # towards LP estimate of the previous epoch (the first is 0 == never nan. TODO: might be better to do the same for post-nan increment if it is not a nan. skipping now
    time_diff_sq_prev = (dt_cum[dtnanposition - 1] - dt_cum) ** 2
    # the below line uses Gaussian kernel that is not normalized (as in graphics to keep grey level average)
    weight_factor = np.tile(np.exp(-time_diff_sq / 2 / filtwidth_yr ** 2)[dtstartpos:, np.newaxis],
                            (1, len_sel))
    # below weights for getting the previous epoch LP estimate. The biggest weight is at that epoch but that should be fine
    weight_factor_prev = np.tile(np.exp(-time_diff_sq_prev / 2 / filtwidth_yr ** 2)[dtstartpos:, np.newaxis],
                            (1, len_sel))
    weight_factor = weight_factor * (~np.isnan(cusel))
    weight_factor_prev = weight_factor_prev * (~np.isnan(cusel))
    weight_factor = weight_factor / np.sum(weight_factor, axis=0) # this will ensure their sum is 1. is this normalisation after removing nans?? (without use of pi?)
    #                                                              ok, see below -- that's actually weighted average formula. beautiful!
    lpcube = np.nansum(cusel * weight_factor, axis=0) # that's estimated values for the given epoch
    # same for the previous epoch data (no nans there..)
    weight_factor_prev = weight_factor_prev / np.sum(weight_factor_prev, axis=0)
    lpcube_prev = np.nansum(cusel * weight_factor_prev, axis=0)
    if isinc:
        lpcube = lpcube * diffdt[dtnanposition] # now return the incperday to just inc using time diff for given increment.
        lpcube_prev = lpcube_prev * diffdt[dtnanposition-1]
    # remove residual from the LP estimate
    lpcube = lpcube - (prevepochdata - lpcube_prev)
    return lpcube



def gauss_fill_gaps_cube_full(inc,dt_cum, dtcum_offsets_mask = None):
    ''' inc is 2-D array of (n_im, n_pt)
    dtcum_offsets_mask is True for epochs that should be used (that are not offsets)
     where the gauss avg will be used to fill the gaps (nans). ML, 12/2024 '''
    filtwidth_yr = np.diff(dt_cum).mean() * 3  ## avg interval*3
    if inc.shape[0] == len(dt_cum)-1:
        inc = np.append(np.zeros((1, inc.shape[1])), inc, axis=0)
        addedzerow = True
    else:
        addedzerow = False
    #
    # get only inc that has any nan in time dimension
    #if len(inc.shape)==3:
    #    dts_nans = np.isnan(inc).sum(axis=(1, 2))
    #else:
    dts_nans = np.isnan(inc).sum(axis=1)
    dts_nan_inxs = np.where(dts_nans != 0)[0]  # indexes of dt with nans
    n_im_nans = len(dts_nan_inxs)
    #
    # estimate increments in gaps epoch by epoch...
    #n_im, length, width = inc.shape
    print('Filling gaps using Gaussian window in time:')
    j = 0
    for i in dts_nan_inxs:
        j+=1
        if np.mod(j, 10) == 0:
            print("  {0:3}/{1:3}th epoch with nans...".format(j, n_im_nans), flush=True)
        time_diff_sq = (dt_cum[i] - dt_cum) ** 2
        ## Limit reading data within filtwidth_yr**8
        ixs = time_diff_sq < filtwidth_yr * 8
        ## Further limit - data that contain (eq) offset (to be ignored by the algorithm), unless it is index of i
        if type(dtcum_offsets_mask) != type(None):
            ixs = ixs * dtcum_offsets_mask # will use only indices that are not offsets
            ixs[i] = True
        time_diff_sq = time_diff_sq[ixs]
        ## and limit to only data blocks that has some nan in the given epoch
        #incsel = inc[i,:,:] #.flatten() # 3D
        incsel = inc[i, :]  # .flatten()
        #naninxs = np.where(np.isnan(incsel))[0]
        #nanxs, nanys = np.where(np.isnan(incsel)) # 3D
        nancols = np.where(np.isnan(incsel))[0]  # 2D
        # now process only data with that nan
        #incsel = inc[ixs, nanxs, nanys]  # reduced cube
        #incsel = inc[ixs, :, :][:, nanxs, nanys] # 3D
        incsel = inc[ixs, :][:, nancols]
        #incsel = incsel.reshape((len(ixs), len(nanxs))) # just in case of only one nan # 3D
        incsel = incsel.reshape(ixs.sum(), len(nancols))  # just in case of only one nan
        #inc[i, nanxs, nanys] = gauss_fill_gaps_cube(incsel, dt_cum[ixs], filtwidth_yr, time_diff_sq) # 3D
        inc[i, nancols] = gauss_fill_gaps_cube(incsel, dt_cum[ixs], filtwidth_yr, time_diff_sq)
        #incdt = inc[i, :, :]
        #incdt[np.isnan(incdt)] = inc_lpt[np.isnan(incdt)] * diffdt[np.isnan(incdt)]  # get back the increments
        #inc[i, :, :] = incdt  # store back into inc. maybe not needed?
    #
    if addedzerow:
        inc = inc[1:,:]
    return inc


def singular_nsbas_onepoint(d,G,m,dt_cum, wvars, skip_gapestimate, i):
    ''' Inverts with simplified estimation of gaps - this is improved with singular_gauss (for which skip_gapestimate should be done)
    Inputs:
      d : Unwrapped data block for each point (n_ifg, n_pt)
      wvars : (optional, can be None) Variance estimated from coherence (n_ifg, n_pt)
      G    : Design matrix (1 between primary and secondary) (n_ifg, n_im-1)
      m   :  Empty incremental displacement matrix (n_im-1, n_pt)
      dt_cum : Cumulative years(or days) for each image (n_im)
      skip_gapestimate : (bool) if True, it will not perform nan filling (gaps)
      i : pixel to run the inversion for (up to n_pt)

    Returns:
      mpx     : Filled incremental displacement matrix (n_im-1, n_pt)

    '''
    px = i
    if np.mod(px, 100) == 0:
        print('\r  Running {0:6}/{1:6}th point...'.format(px, m.shape[1]), end='', flush=True)
    dpx = d[:,px]
    mpx = m[:,px]
    # first, work only with values without nans. check if it doesn't remove increments, if so, estimate the inc
    okpx = ~np.isnan(dpx)
    Gpx_ok = G[okpx,:]
    dpx_ok = dpx[okpx]
    # for WLS:
    if type(wvars) != type(None):
        wpx_ok = wvars[okpx,px]
        Gpx_ok = Gpx_ok.copy() / np.sqrt(np.float64(wpx_ok[:, np.newaxis]))
        dpx_ok = dpx_ok.copy() / np.sqrt(np.float64(wpx_ok))

    badincs = np.sum(Gpx_ok,axis=0)==0
    
    if not max(badincs):
        # if actually all are fine, just run LS:
        mpx = np.linalg.lstsq(Gpx_ok, dpx_ok, rcond=None)[0]
    else:
        # if there is at least one im with no related ifg (means, it would cause gap):
        mpx[~badincs] = np.linalg.lstsq(Gpx_ok[:,~badincs], dpx_ok, rcond=None)[0]
        if skip_gapestimate:
            mpx[badincs] = np.nan
        else:
            badinc_index = np.where(badincs)[0]
            #s = mpx[~badincs].sum()
            #t = dt_cum[~badincs].sum()
            bi_prev = 0
            s = []
            t = []
            #
            # ensure the algorithm goes towards the end of the mpx line
            for bi in np.append(badinc_index,len(mpx)):
                group_mpx = mpx[bi_prev:bi]
                #use at least 2 increments for the vel estimate
                if group_mpx.size > 0:
                    group_time = dt_cum[bi_prev:bi+1]
                    s.append(group_mpx.sum())
                    t.append(group_time[-1] - group_time[0])
                bi_prev = bi+1
            s = np.array(s)
            t = np.array(t)
            # is only one value ok? maybe increase the threshold here:
            if len(s)>0:
                velpx = s.sum()/t.sum()    # mm/[dt_cum unit]
            else:
                velpx = np.nan # not sure what will happen. putting 0 may be safer
            #if len(s) == 1:
            #    velpx = s[0]/t[0]
            #else:
            #    velpx = curve_fit(func_vel, t, s)[0][0]
            #mpx[badincs] = (dt_cum[badinc_index+1]-dt_cum[badinc_index]) * velpx
            mpx[badincs] = (dt_cum[badinc_index] - dt_cum[badinc_index-1]) * velpx
    
    return mpx


def censored_lstsq_slow_para_wrapper(i):
    ### Use global value
    #A = csc_array(Gall) # or csr?
    if np.mod(i, 100) == 0:
        print('  Running {0:6}/{1:6}th point...'.format(i, unw_tmp.shape[1]), flush=True)
    m = mask[:,i] # drop rows where mask is zero
    X = np.linalg.lstsq(Gall[m], unw_tmp[m, i], rcond=None)[0]
    return X

'''
2024-09-30 - a BUG! the sparselsq ended up on values with e-5 where lstsq return correct values(!)
reverting back to numpy solution

    try:
        #X = np.linalg.lstsq(Gall[m], unw_tmp[m,i], rcond=None)[0]
        X = sparselsq(A[m], unw_tmp[m, i], atol=1e-05, btol=1e-05)[0]
    except:
        X = np.zeros((Gall.shape[1]), dtype=np.float32)*np.nan
        print('Warning: error during sparselsq - setting to nan')
        print('')
    return X
'''

#%%
def invert_nsbas_wls(unw, var, G, dt_cum, gamma, n_core):
    """
    Calculate increment displacement difference by NSBAS inversion with WLS.

    Inputs:
      unw : Unwrapped data block for each point (n_pt, n_ifg)
            Still include nan to keep dimention
      var : Variance estimated from coherence (n_pt, n_ifg)
      G    : Design matrix (1 between primary and secondary) (n_ifg, n_im-1)
      dt_cum : Cumulative years(or days) for each image (n_im)
      gamma  : Gamma value for NSBAS inversion, should be small enough (e.g., 0.0001)
      n_core : Number of cores for parallel processing

    Returns:
      inc     : Incremental displacement (n_im-1, n_pt)
      vel     : Velocity (n_pt)
      vconst  : Constant part of linear velocity (c of vt+c) (n_pt)
    """
    global Gall, unw_tmp, var_tmp, mask ## for para_wrapper

    ### Settings
    n_pt, n_ifg = unw.shape
    n_im = G.shape[1]+1

    result = np.zeros((n_im+1, n_pt), dtype=np.float32)*np.nan #[inc, vel, const]

    ### Set matrix of NSBAS part (bottom)
    Gbl = np.tril(np.ones((n_im, n_im-1), dtype=np.float32), k=-1) #lower tri matrix without diag
    Gbr = -np.ones((n_im, 2), dtype=np.float32)
    Gbr[:, 0] = -dt_cum
    Gb = np.concatenate((Gbl, Gbr), axis=1)*gamma
    Gt = np.concatenate((G, np.zeros((n_ifg, 2), dtype=np.float32)), axis=1)
    Gall = np.float32(np.concatenate((Gt, Gb)))


    ### Make unw_tmp, var_tmp, and mask
    unw_tmp = np.concatenate((unw, np.zeros((n_pt, n_im), dtype=np.float32)), axis=1).transpose()
    mask = (~np.isnan(unw_tmp))
    unw_tmp[np.isnan(unw_tmp)] = 0
    var_tmp = np.concatenate((var, 50*np.ones((n_pt, n_im), dtype=np.float32)), axis=1).transpose() #50 is var for coh=0.1, to scale bottom part of Gall

    if n_core == 1:
        for i in range(n_pt):
            result[:, i] = wls_nsbas(i) #(n_im+1, n_pt)
    else:
        print('  {} parallel processing'.format(n_core), flush=True)

        args = [i for i in range(n_pt)]
        q = multi.get_context('fork')
        p = q.Pool(n_core)
        _result = p.map(wls_nsbas, args) #list[n_pt][length]
        result = np.array(_result).T

    inc = result[:n_im-1, :]
    vel = result[n_im-1, :]
    vconst = result[n_im, :]

    return inc, vel, vconst


def wls_nsbas(i):
    ### Use global value of Gall, unw_tmp, var_tmp, mask
    if np.mod(i, 1000) == 0:
        print('  Running {0:6}/{1:6}th point...'.format(i, unw_tmp.shape[1]), flush=True)

    ## Weight unw and G

    Gall_w = Gall/np.sqrt(np.float64(var_tmp[:,i][:,np.newaxis]))
    unw_tmp_w = unw_tmp[:, i]/np.sqrt(np.float64(var_tmp[:,i]))
    m = mask[:,i] # drop rows where mask is zero

    try:
        X = np.linalg.lstsq(Gall_w[m], unw_tmp_w[m], rcond=None)[0]
    except:
        X = np.zeros((Gall.shape[1]), dtype=np.float32)*np.nan
    return X


#%%
def calc_vel(cum, dt_cum, return_G = False):
    """
    Calculate velocity.

    Inputs:
      cum    : cumulative phase block for each point (n_pt, n_im)
      dt_cum : Cumulative days for each image (n_im)
      return_G: optionally return G matrix

    Returns:
      vel    : Velocity (n_pt)
      vconst : Constant part of linear velocity (c of vt+c) (n_pt)
    """
    n_pt, n_im = cum.shape
    result = np.zeros((2, n_pt), dtype=np.float32)*np.nan #[vconst, vel]

    G = np.stack((np.ones_like(dt_cum), dt_cum), axis=1)
    vconst = np.zeros((n_pt), dtype=np.float32)*np.nan
    vel = np.zeros((n_pt), dtype=np.float32)*np.nan

    bool_pt_full = np.all(~np.isnan(cum), axis=1)
    n_pt_full = bool_pt_full.sum()

    if n_pt_full!=0:
        print('  Solving {0:6}/{1:6}th points with full cum at a time...'.format(n_pt_full, n_pt), flush=True)

        ## Sovle
        result[:, bool_pt_full] = np.linalg.lstsq(G, cum[bool_pt_full, :].transpose(), rcond=None)[0]

    ### Solve other points with nan point by point.
    cum_tmp = cum[~bool_pt_full, :].transpose()
    mask = (~np.isnan(cum_tmp))
    cum_tmp[np.isnan(cum_tmp)] = 0
    print('  Next, solve {0} points including nan point-by-point...'.format(n_pt-n_pt_full), flush=True)

    result[:, ~bool_pt_full] = censored_lstsq_slow(G, cum_tmp, mask) #(n_im+1, n_pt)

    vconst = result[0, :]
    vel = result[1, :]
    # reverting the zeroes to nan, although ref area will then be nan now.
    vel[vel==0] = np.nan
    vconst[vconst==0] = np.nan

    print(' Velocity estimation finished')

    if return_G:
        # careful, we switch the output params to conform with G
        return vconst, vel, G
    else:
        return vel, vconst


#%%
def calc_velsin(cum, dt_cum, imd0, return_G = False):
    """
    Calculate velocity and coeffcients of sin (annual) function.

    Inputs:
      cum    : cumulative phase block for each point (n_pt, n_im)
      dt_cum : Cumulative days for each image (n_im)
      imd0   : Date of first acquistion (str, yyyymmdd)
      return_G: optionally return G matrix (careful..)

    Returns:
      vel    : Velocity (n_pt)
      vconst : Constant part of linear velocity (c of vt+c) (n_pt)
      amp    : Amplitude of sin function
      dt     : Time difference of sin function wrt Jan 1 (day)
    """
    doy0 = (dt.datetime.strptime(imd0, '%Y%m%d')-dt.datetime.strptime(imd0[0:4]+'0101', '%Y%m%d')).days

    n_pt, n_im = cum.shape
    result = np.zeros((4, n_pt), dtype=np.float32)*np.nan #[vconst, vel, coef_s, coef_c]


    sin = np.sin(2*np.pi*dt_cum)
    cos = np.cos(2*np.pi*dt_cum)
    G = np.stack((np.ones_like(dt_cum), dt_cum, sin, cos), axis=1)

    vconst = np.zeros((n_pt), dtype=np.float32)*np.nan
    vel = np.zeros((n_pt), dtype=np.float32)*np.nan
    amp = np.zeros((n_pt), dtype=np.float32)*np.nan
    delta_t = np.zeros((n_pt), dtype=np.float32)*np.nan

    bool_pt_full = np.all(~np.isnan(cum), axis=1)
    n_pt_full = bool_pt_full.sum()

    if n_pt_full!=0:
        print('  Solving {0:6}/{1:6}th points with full cum at a time...'.format(n_pt_full, n_pt), flush=True)

        ## Sovle
        result[:, bool_pt_full] = np.linalg.lstsq(G, cum[bool_pt_full, :].transpose(), rcond=None)[0]

    ### Solve other points with nan point by point.
    cum_tmp = cum[~bool_pt_full, :].transpose()
    mask = (~np.isnan(cum_tmp))
    cum_tmp[np.isnan(cum_tmp)] = 0
    print('  Next, solve {0} points including nan point-by-point...'.format(n_pt-n_pt_full), flush=True)

    result[:, ~bool_pt_full] = censored_lstsq_slow(G, cum_tmp, mask) #(n_im+1, n_pt)

    vconst = result[0, :]
    vel = result[1, :]
    coef_s = result[2, :]
    coef_c = result[3, :]

    amp = np.sqrt(coef_s**2+coef_c**2)
    delta_t = np.arctan2(-coef_c, coef_s)/2/np.pi*365.25 ## wrt 1st img
    delta_t = delta_t+doy0 ## wrt Jan 1
    delta_t[delta_t < 0] = delta_t[delta_t < 0]+365.25 #0-365.25
    delta_t[delta_t > 365.25] = delta_t[delta_t > 365.25]-365.25

    if return_G:
        # careful, we switch the output params to conform with G - AND, actually also coef_s/c
        return vconst, vel, coef_s, coef_c, amp, delta_t, G
    else:
        return vel, vconst, amp, delta_t



def get_vel_ransac(dt_cum, cumm, return_intercept=False):
    """
    Recalculate velocity (and intercept) using RANSAC algorithm to identify/skip use of outliers.
    
    Inputs:
       dt_cum   : delta time values for the cumm. time series
       cumm     : the cumm. time series values, array of shape (n_points, n_dates)
    
    Returns:
       vel2     : recalculated velocity for each point
    """
    X=dt_cum.reshape(-1,1)  # single feature (time) of dt_cum.shape[0] samples
    vel2 = np.zeros(cumm.shape[0])
    if return_intercept:
        intercept2 = np.zeros(cumm.shape[0])
    
    for i in range(cumm.shape[0]):
        y=cumm[i]
        mask = ~np.isnan(y)
        if np.mod(i, 100) == 0:
            print('\r  Running {0:6}/{1:6}th point...'.format(i, cumm.shape[0]), end='', flush=True)
        if np.sum(mask) < 2:
            # 'all' nan situation
            vel2[i] = np.nan
            if return_intercept:
                intercept2[i] = np.nan
        else:
            reg = RANSACRegressor().fit(X[mask],y[mask])   # the implementation is fine, parameters should be quite robust
            # yet, one may check parameters max_trials[=100]
            vel2[i] = reg.estimator_.coef_[0]
            if return_intercept:
                intercept2[i] = reg.estimator_.intercept_ # if needed..
    
    print('')
    if return_intercept:
        return vel2 , intercept2
    else:
        return vel2


#%%
def calc_velstd_withnan(cum, dt_cum, gpu=False):
    """
    Calculate std of velocity by bootstrap for each point which may include nan.

    Inputs:
      cum    : Cumulative phase block for each point (n_pt, n_im)
               Can include nan.
      dt_cum : Cumulative days for each image (n_im)
      gpu    : GPU flag

    Returns:
      vstd   : Std of Velocity for each point (n_pt)
      vel   : median of bootstrapped velocity (n_pt)
    """
    global bootcount, bootnum
    n_pt, n_im = cum.shape
    bootnum = 100
    bootcount = 0

    vstd = np.zeros((n_pt), dtype=np.float32)
    G = np.stack((np.ones_like(dt_cum), dt_cum), axis=1)

    data = cum.transpose().copy()
    ixs_day = np.arange(n_im)
    mask = (~np.isnan(data))
    data[np.isnan(data)] = 0

    velinv = lambda x : censored_lstsq2(G[x, :], data[x, :], mask[x, :],
                                        gpu=gpu)[1]

    with NumpyRNGContext(1):
        bootresult = bootstrap(ixs_day, bootnum, bootfunc=velinv)

    vstd = np.nanstd(bootresult, axis=0)
    vel = np.nanmedian(bootresult, axis=0) # experimental

    print('')

    return vstd, vel


def censored_lstsq2(A, B, M, gpu=False):
    ## http://alexhwilliams.info/itsneuronalblog/2018/02/26/censored-lstsq/
    global bootcount, bootnum
    if gpu:
        import cupy as xp
        A = xp.asarray(A)
        B = xp.asarray(B)
        M = xp.asarray(M)
    else:
        xp = np

    print('\r  Running {0:3}/{1:3}th bootstrap...'.format(bootcount, bootnum), end='', flush=True)
    Bshape1 = B.shape[1]
    bootcount = bootcount+1

    # if B is a vector, simply drop out corresponding rows in A
    if B.ndim == 1 or Bshape1 == 1:
        sol = xp.linalg.leastsq(A[M], B[M])[0]
        if gpu:
            sol = xp.asnumpy(sol)
            del A, B, M
        return sol

    # else solve via tensor representation
    rhs = xp.dot(A.T, M * B).T[:,:,None] # n x r x 1 tensor
    T = xp.matmul(A.T[None,:,:], M.T[:,:,None] * A[None,:,:]) # n x r x r tensor

    # Not use gpu for solve because it is quite slow
    if gpu:
        T = xp.asnumpy(T)
        rhs = xp.asnumpy(rhs)
        del A, B, M

    try:
        X = np.squeeze(np.linalg.solve(T, rhs)).T # transpose to get r x n
    except: ## In case Singular matrix
        X = np.zeros((Bshape1), dtype=np.float32)*np.nan

    return X


#%%
def calc_stc(cum, gpu=False):
    """
    Calculate STC (spatio-temporal consistensy; Hanssen et al., 2008,
    Terrafirma) of time series of displacement.
    Note that isolated pixels (which have no surrounding pixel) have nan of STC.

    Input:
      cum  : Cumulative displacement (n_im, length, width)
      gpu  : GPU flag

    Return:
      stc  : STC (length, width)
    """
    if gpu:
        import cupy as xp
        cum = xp.asarray(cum)
    else:
        xp = np

    n_im, length, width = cum.shape

    ### Add 1 pixel margin to cum data filled with nan
    cum1 = xp.ones((n_im, length+2, width+2), dtype=xp.float32)*xp.nan
    cum1[:, 1:length+1, 1:width+1] = cum

    ### Calc STC for surrounding 8 pixels
    _stc = xp.ones((length, width, 8), dtype=xp.float32)*xp.nan
    pixels = [[0, 0], [0, 1], [0, 2], [1, 0], [1, 2], [2, 0], [2, 1], [2, 2]]
    ## Left Top = [0, 0], Rigth Bottmon = [2, 2], Center = [1, 1]

    for i, pixel in enumerate(pixels):
        ### Spatial difference (surrounding pixel-center)
        d_cum = cum1[:, pixel[0]:length+pixel[0], pixel[1]:width+pixel[1]] - cum1[:, 1:length+1, 1:width+1]

        ### Temporal difference (double difference)
        dd_cum = d_cum[:-1,:,:]-d_cum[1:,:,:]

        ### STC (i.e., RMS of DD)
        sumsq_dd_cum = xp.nansum(dd_cum**2, axis=0)
        n_dd_cum = (xp.sum(~xp.isnan(dd_cum), axis=0)).astype(xp.float32) #nof non-nan
        n_dd_cum[n_dd_cum==0] = xp.nan #to avoid 0 division
        _stc[:, :, i] = xp.sqrt(sumsq_dd_cum/n_dd_cum)

    ### Strange but some adjacent pixels can have identical time series,
    ### resulting in 0 of stc. To avoid this, replace 0 with nan.
    _stc[_stc==0] = xp.nan

    ### Identify minimum value as final STC
    with warnings.catch_warnings(): ## To silence warning by All-Nan slice
        warnings.simplefilter('ignore', RuntimeWarning)
        stc = xp.nanmin(_stc, axis=2)

    if gpu:
        stc = xp.asnumpy(stc)
        del cum, cum1, _stc, d_cum, dd_cum, sumsq_dd_cum, n_dd_cum

    return stc


#%%
def censored_lstsq(A, B, M):
    ## http://alexhwilliams.info/itsneuronalblog/2018/02/26/censored-lstsq/
    ## This is actually slow because matmul does not use multicore...
    ## Need multiprocessing.
    ## Precison is bad widh bad condition, so this is unfortunately useless for NSABS...
    ## But maybe usable for vstd because its condition is good.
    """Solves least squares problem subject to missing data.

    Note: uses a broadcasted solve for speed.

    Args
    ----
    A (ndarray) : m x r matrix
    B (ndarray) : m x n matrix
    M (ndarray) : m x n binary matrix (zeros indicate missing values)

    Returns
    -------
    X (ndarray) : r x n matrix that minimizes norm(M*(AX - B))
    """

    # Note: we should check A is full rank but we won't bother...

    # if B is a vector, simply drop out corresponding rows in A
    if B.ndim == 1 or B.shape[1] == 1:
        return np.linalg.leastsq(A[M], B[M])[0]

    # else solve via tensor representation
    rhs = np.dot(A.T, M * B).T[:,:,None] # n x r x 1 tensor
    T = np.matmul(A.T[None,:,:], M.T[:,:,None] * A[None,:,:]) # n x r x r tensor
    return np.squeeze(np.linalg.solve(T, rhs)).T # transpose to get r x n




#%%
def censored_lstsq_slow(A, B, M):
    ## http://alexhwilliams.info/itsneuronalblog/2018/02/26/censored-lstsq/
    """Solves least squares problem subject to missing data.

    Note: uses a for loop over the columns of B, leading to a
    slower but more numerically stable algorithm

    Args
    ----
    A (ndarray) : m x r matrix
    B (ndarray) : m x n matrix
    M (ndarray) : m x n binary matrix (zeros indicate missing values)

    Returns
    -------
    X (ndarray) : r x n matrix that minimizes norm(M*(AX - B))
    """

    X = np.empty((A.shape[1], B.shape[1]))
    # 20231101 update - not tested
    #A = csr_matrix(A) # or csc?
    #if not debugmode:
    #    A = csc_array(A) # or csr?
    errs = 0
    for i in range(B.shape[1]):
        if np.mod(i, 100) == 0:
             print('\r  Running {0:6}/{1:6}th point...'.format(i, B.shape[1]), end='', flush=True)

        m = M[:,i] # drop rows where mask is zero
        X[:, i] = np.linalg.lstsq(A[m], B[m, i], rcond=None)[0]
    return X

'''
# 20240930 - removing the sparselsq - it just does NOT do any good job! 
        try:
            #X[:,i] = np.linalg.lstsq(A[m], B[m,i], rcond=None)[0]
            # 20231101 update
            X[:, i] = sparselsq(A[m], B[m, i], atol=1e-05, btol=1e-05)[0]
        except:
            errs = errs+1
            X[:,i] = np.nan
    print('')
    if errs > 0:
        print('Warning: '+str(errs)+' errors occurred during sparselsq (-> nan increments)')
        print('')
    return X
'''

def calc_vel_offsets(cum, imdates_dt, offsetdates, return_G = False, trunc_last_days = 180):
    """
    Calculate vconst, velocity, and offsets for given dates. ML 20241022

    Inputs:
      cum    : cumulative phase block for each point (n_pt, n_im)
      imdates_dt : acquisition dates as ordinal number (n_im)
      offsetdates : earthquake event dates as datetime.date
      return_G : will also return the formed G matrix
      trunc_last_days : if the offset is within the last trunc_last_days, it will set velocity estimate to not use such. TODO: may get to problems in short datasets

    Returns:
      result : vconst, vel, estimated offsets (n_vars, n_pt)
      Gdesc :  description of the 'result' content (n_vars)

    """
    dt_cum = np.float32((np.array(imdates_dt) - imdates_dt[0]) / 365.25)
    n_pt, n_im = cum.shape
    result = np.zeros((2, n_pt), dtype=np.float32)*np.nan #[vconst, vel]

    G = np.stack((np.ones_like(dt_cum), dt_cum), axis=1)
    #vconst = np.zeros((n_pt), dtype=np.float32)*np.nan
    #vel = np.zeros((n_pt), dtype=np.float32)*np.nan

    bool_pt_full = np.all(~np.isnan(cum), axis=1)
    n_pt_full = bool_pt_full.sum()

    offsetcol_prev = np.zeros_like(imdates_dt)
    Gdesc = ['vconst', 'vel']

    for offdate in offsetdates:
        # dt_cum_offset = dt_cum.copy()
        # coseismic offset
        TT = np.array(imdates_dt) >= offdate.toordinal()
        offsetcol = (TT > 0).astype(int)
        if np.array_equal(offsetcol, offsetcol_prev):
            # skipping this offset
            continue
        if np.all(offsetcol == 1):
            continue
        offsetcol_prev = offsetcol
        # all ok, adding to G matrix
        G = np.insert(G, G.shape[-1], offsetcol, axis=1)
        Gdesc.append('offset_' + offdate.strftime('%Y%m%d'))
        # and allocate extended result
        result = np.insert(result, result.shape[0], np.zeros((1, n_pt), dtype=np.float32) * np.nan, axis=0)


    if n_pt_full!=0:
        print('  Solving {0:6}/{1:6}th points with full cum at a time...'.format(n_pt_full, n_pt), flush=True)

        ## Sovle
        result[:, bool_pt_full] = np.linalg.lstsq(G, cum[bool_pt_full, :].transpose(), rcond=None)[0]

    ### Solve other points with nan point by point.
    cum_tmp = cum[~bool_pt_full, :].transpose()
    mask = (~np.isnan(cum_tmp))
    cum_tmp[np.isnan(cum_tmp)] = 0
    print('  Next, solve {0} points including nan point-by-point...'.format(n_pt-n_pt_full), flush=True)

    result[:, ~bool_pt_full] = censored_lstsq_slow(G, cum_tmp, mask) #(n_im+1, n_pt)

    #vconst = result[0, :]
    #vel = result[1, :]
    #
    #return vel, vconst
    if return_G:
        return result, Gdesc, G
    else:
        return result, Gdesc


def get_model_cum(G, params_sorted):
    """ Will get the model cum displacements, using formed G and corresponding parameters.

    Inputs:
        G (np.array) :  shape of (time, modelparams)
        params_sorted (list of arrays):  the model parameter estimates, e.g. [vel, vconst]

    Returns:
        np.array : same shape as the cum layer
    """
    t, x, y = G.shape[0], params_sorted[0].shape[0], params_sorted[0].shape[1]
    out = np.zeros((t, x, y), dtype=np.float32)
    # this way below is little less memory demanding:
    for i in range(len(params_sorted)):
        ivals = G[:,i]
        m = params_sorted[i]
        out = m * np.repeat(ivals[:, np.newaxis], x*y, axis=1).reshape((t,x,y)) + out
    #
    return out
