#!/usr/bin/env python3
"""
========
Overview
========
This script:
 - calculates the block sum of unw pixels
 - calculates the block sum of coherence
 - calculates the block sum of connected component size
 - calculates the block std of height
 - combine and normalise a proxy [0-1] of suitability of reference window
 - choose amongst the selected windows (above threshold) the nearest to desired reference location
 - discard ifgs with all nan values in the chosen reference window

===============
Input & output files
===============

Inputs in GEOCml*/:
 - slc.mli.par
 - hgt
 - yyyymmdd_yyyymmdd/
   - yyyymmdd_yyyymmdd.cc
   - yyyymmdd_yyyymmdd.conncomp
   - yyyymmdd_yyyymmdd.unw
   
   - yyyymmdd_yyyymmdd.sbovldiff.adf.mm[.png] (if --sbovl is used)

Outputs in TS_GEOCml*/ :
 - info/
  - 120ref.txt        : refx1:refx2/refy1:refy2
  - 120bad_ifg.txt    : list of ifgs with all nan values within the chosen reference window
  - 120_reference.png : proxy plots

 - networks/
  - network120*png

=====
Usage
=====
LiCSBAS120_choose_reference.py [-h] [-f FRAME_DIR] [-g UNW_DIR] [-t TS_DIR] [-w WIN] [-r [0-1]] [--w_unw [0-1]] [--w_coh [0-1]] [--w_con [0-1]] [--w_hgt [0-1]] [--refx [0-1]] [--refy [0-1]]
"""

#%% Change log
'''
20241221 Muhammet Nergizci
- check baseline file empty or not 
20241030 Muhammet Nergizci
- add sbovl flag
20240928 ML
 - check for existence of conn. components, avoiding if not 
'''

from LiCSBAS_meta import *
import numpy as np
import matplotlib.pyplot as plt
import os
import argparse
import time
import sys
import LiCSBAS_io_lib as io_lib
import LiCSBAS_tools_lib as tools_lib
import LiCSBAS_plot_lib as plot_lib
from matplotlib import cm
import cmcrameri.cm as cmc


def block_sum(array, k):
    result = np.add.reduceat(np.add.reduceat(array, np.arange(0, array.shape[0], k), axis=0),
                             np.arange(0, array.shape[1], k), axis=1)
    return result


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    '''
    Use a multiple inheritance approach to use features of both classes.
    The ArgumentDefaultsHelpFormatter class adds argument default values to the usage help message
    The RawDescriptionHelpFormatter class keeps the indentation and line breaks in the ___doc___
    '''
    pass


def init_args():
    global args
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=CustomFormatter)
    parser.add_argument('-f', dest="frame_dir", default="./", help="directory of LiCSBAS output of a particular frame")
    parser.add_argument('-c', dest='cc_dir', default="GEOCml10GACOS", help="folder containing cc input")
    parser.add_argument('-d', dest='unw_dir', default="GEOCml10GACOS", help="folder containing unw input")
    parser.add_argument('-t', dest='ts_dir', default="TS_GEOCml10GACOS", help="folder containing time series")
    parser.add_argument('-w', dest='win', default="5", type=float, help="Window size in km")
    parser.add_argument('-p', dest='percentile', default=90, type=float, choices=range(0, 100), metavar="[0-100]", help="proxy percentile above which the window nearest to desired center will be chosen as the reference window")
    parser.add_argument('-l', dest='ifg_list', default=None, type=str, help="text file containing a list of ifgs")
    parser.add_argument("--w_unw", default=1, choices=np.arange(0,1.1,0.1), metavar="[0-1]", type=float, help="weight for block_sum_unw_pixel")
    parser.add_argument('--w_coh', default=1, choices=np.arange(0,1.1,0.1), metavar="[0-1]", type=float, help="weight for block_sum_coherence")
    parser.add_argument('--w_con', default=1, choices=np.arange(0,1.1,0.1), metavar="[0-1]", type=float, help="weight for block_sum_component_size")
    parser.add_argument('--w_hgt', default=1, choices=np.arange(0,1.1,0.1), metavar="[0-1]", type=float, help="weight for block_std_hgt")
    parser.add_argument('--refx', default=0.5, choices=np.arange(0,1.1,0.1), metavar="[0-1]", type=float, help="x axis fraction of desired ref center from left (default 0.5)")
    parser.add_argument('--refy', default=0.5, choices=np.arange(0,1.1,0.1), metavar="[0-1]", type=float, help="y axis fraction of desired ref center from top (default 0.5)")
    parser.add_argument('--keep_edge_cuts', default=False, action='store_true', help="do not remove edge cuts from largest network component")
    parser.add_argument('--keep_node_cuts', default=False, action='store_true', help="do not remove node cuts from largest network component")
    parser.add_argument('--skip_node_cuts', default=False, action='store_true', help="skip node cut searching, used when the program gets stuck")
    parser.add_argument('--ignore_comp', default=False, action='store_true', help="do not use connected components for choosing reference")
    parser.add_argument('--sbovl', default=False, action='store_true', help="run the code for only sbovl referencing point")
    args = parser.parse_args()


def start():
    global start_time
    # intialise and print info on screen
    start_time = time.time()
    ver="1.0"; date=20221020; author="Dr. Qi Ou"
    print("\n{} ver{} {} {}".format(os.path.basename(sys.argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(sys.argv[0]), ' '.join(sys.argv[1:])), flush=True)


def finish():
    #%% Finish
    elapsed_time = time.time() - start_time
    hour = int(elapsed_time/3600)
    minite = int(np.mod((elapsed_time/60),60))
    sec = int(np.mod(elapsed_time,60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour,minite,sec))
    print("\n{} {}".format(os.path.basename(sys.argv[0]), ' '.join(sys.argv[1:])), flush=True)
    print('Output directory: {}\n'.format(os.path.relpath(tsadir)))


def set_input_output():
    global ccdir, ifgdir, tsadir, infodir, resultsdir, netdir, noref_ifgfile, no_ref_dir, reference_png, weak_ifgfile, strong_ifgfile, edge_cut_ifgfile, node_cut_ifgfile, component_statsfile

    ### Define input directories
    ccdir = os.path.abspath(os.path.join(args.frame_dir, args.cc_dir))
    ifgdir = os.path.abspath(os.path.join(args.frame_dir, args.unw_dir))
    tsadir = os.path.abspath(os.path.join(args.frame_dir, args.ts_dir))
    resultsdir = os.path.join(tsadir, 'results')
    infodir = os.path.join(tsadir, 'info')

    ### Define output dir
    no_ref_dir = os.path.join(tsadir, '120no_ref')
    if not os.path.exists(no_ref_dir): 
        os.mkdir(no_ref_dir)
    netdir = os.path.join(tsadir, 'network')
    noref_ifgfile = os.path.join(infodir, '120bad_ifg.txt')
    reference_png = os.path.join(infodir, "120_reference.png")
    weak_ifgfile = os.path.join(infodir, '120weak_links.txt')
    strong_ifgfile = os.path.join(infodir, '120strong_connected_links.txt')
    edge_cut_ifgfile = os.path.join(infodir, '120edge_cuts.txt')
    node_cut_ifgfile = os.path.join(infodir, '120node_cuts.txt')
    component_statsfile = os.path.join(infodir, '120component_stats.txt')


def read_length_width():
    global length, width

    ### Get size
    mlipar = os.path.join(ccdir, 'slc.mli.par')
    width = int(io_lib.get_param_par(mlipar, 'range_samples'))
    length = int(io_lib.get_param_par(mlipar, 'azimuth_lines'))
    print("\nSize         : {} x {}".format(width, length), flush=True)


def decide_reference_window_size():
    global window_size
    ### Get resolution
    dempar = os.path.join(ccdir, 'EQA.dem_par')
    lattitude_resolution = float(io_lib.get_param_par(dempar, 'post_lat'))
    print(f'lat_res={lattitude_resolution}')
    window_size = int(abs(args.win / 110 / lattitude_resolution) + 0.5)   # 110 km per degree latitude
    print("\nWindow size : ", window_size)


def get_ifgdates():
    global ifgdates
    if args.ifg_list:
        ifgdates = io_lib.read_ifg_list(args.ifg_list)
    else:
        ### Get dates
        ifgdates = tools_lib.get_ifgdates(ifgdir)

        ### Read bad_ifg11 and rm_ifg
        bad_ifg11file = os.path.join(infodir, '11bad_ifg.txt')
        bad_ifg11 = io_lib.read_ifg_list(bad_ifg11file)

        ### Remove bad ifgs and images from list
        ifgdates = list(set(ifgdates)-set(bad_ifg11))
    ifgdates.sort()


def calc_block_sum_of_unw_coh_component_size():
    global block_unw, block_coh, block_con, ifgd
    ### Start counting indices for choosing the reference
    n_unw = np.zeros((length, width), dtype=np.float32)
    n_coh = np.zeros((length, width), dtype=np.float32)
    if not args.ignore_comp:
        n_con = np.zeros((length, width), dtype=np.float32)

    ### Accumulate through network (1)unw pixel counts, (2) coherence and (3) size of connected components
    for ifgd in ifgdates:
        # turn ifg into ones and zeros for non-nan and nan values
        if args.sbovl:
            unwfile = os.path.join(ifgdir, ifgd, ifgd+'.sbovldiff.adf.mm')
        else:    
            unwfile = os.path.join(ifgdir, ifgd, ifgd+'.unw')
        unw = io_lib.read_img(unwfile, length, width)
        unw[unw == 0] = np.nan # Fill 0 with nan
        n_unw += ~np.isnan(unw) # Summing number of unnan unw

        # coherence values from 0 to 1
        ccfile = os.path.join(ccdir, ifgd, ifgd + '.cc')
        coh = io_lib.read_img(ccfile, length, width, np.uint8)
        coh = coh.astype(np.float32) / 255  # keep 0 as 0 which represent nan values
        n_coh += coh

        if not args.ignore_comp:

            # connected components in terms of component area (pixel count)
            confile = os.path.join(ccdir, ifgd, ifgd+'.conncomp')
            con = io_lib.read_img(confile, length, width, np.uint8)
            # replace component index by component size. the first component is the 0th component, which should be of size 0
            uniq_components, pixel_counts = np.unique(con.flatten(), return_counts=True)
            for i, component in enumerate(uniq_components[1:]):
                con[con==component] = pixel_counts[i+1]
            n_con += con

        del unw, coh
        if not args.ignore_comp:
            del con

    ### calculate block sum
    block_unw = block_sum(n_unw, window_size)
    block_coh = block_sum(n_coh, window_size)
    if not args.ignore_comp:
        block_con = block_sum(n_con, window_size)


def calc_height_std():
    global block_rms_hgt
    ### calculate block standard deviation of height
    hgtfile = os.path.join(resultsdir, 'hgt')
    hgt = io_lib.read_img(hgtfile, length, width)
    block_mean_hgt = block_sum(hgt, window_size)/(window_size**2)
    repeat_block_mean_hgt = np.repeat(block_mean_hgt, window_size, axis=1)
    broadcast_mean_hgt = np.repeat(repeat_block_mean_hgt, window_size, axis=0) #size getting lengt, width)
    hgt_demean = hgt - broadcast_mean_hgt[:hgt.shape[0], :hgt.shape[1]] ##here is for to be sure broadcast is same size with original hgt..
    hgt_demean_square = hgt_demean ** 2
    block_rms_hgt = np.sqrt( block_sum(hgt_demean_square, window_size) / (window_size ** 2) ) #size getting again lengt/ws, width/ws)


def clip_normalise_combine_indices():
    global block_proxy, block_unw, block_coh, block_con, block_rms_hgt
    ### turn 0 to nan
    block_unw[block_unw == 0] = np.nan
    block_coh[block_coh == 0] = np.nan
    if not args.ignore_comp:
        block_con[block_con == 0] = np.nan
    block_rms_hgt[block_rms_hgt == 0] = np.nan
    # print(np.nanmin(block_coh), np.nanmin(block_unw),np.nanmin(block_rms_hgt))
    ### clipping values at zigzagy edges which are the lowest for block sums and highest for std
    block_unw[block_unw < np.nanpercentile(block_unw, 5)] = np.nanpercentile(block_unw, 5)
    block_coh[block_coh < np.nanpercentile(block_coh, 5)] = np.nanpercentile(block_coh, 5)
    if not args.ignore_comp:
        block_con[block_con < np.nanpercentile(block_con, 5)] = np.nanpercentile(block_con, 5)
    block_rms_hgt[block_rms_hgt > np.nanpercentile(block_rms_hgt, 90)] = np.nanpercentile(block_rms_hgt, 90)
    # print(np.nanmin(block_coh), np.nanmin(block_unw),np.nanmin(block_rms_hgt))
    
    ### normalise with nan minmax
    block_unw = (block_unw - np.nanmin(block_unw)) / (np.nanmax(block_unw) - np.nanmin(block_unw))
    block_coh = (block_coh - np.nanmin(block_coh)) / (np.nanmax(block_coh) - np.nanmin(block_coh))
    if not args.ignore_comp:
        block_con = (block_con - np.nanmin(block_con)) / (np.nanmax(block_con) - np.nanmin(block_con))
    block_rms_hgt = (block_rms_hgt - np.nanmin(block_rms_hgt)) / (np.nanmax(block_rms_hgt) - np.nanmin(block_rms_hgt))

    ### calculate proxy from 4 indices and normalise
    if not args.ignore_comp:
        block_proxy = args.w_unw * block_unw + args.w_coh * block_coh + args.w_con * block_con - args.w_hgt * block_rms_hgt
    else:
        block_proxy = args.w_unw * block_unw + args.w_coh * block_coh - args.w_hgt * block_rms_hgt
    block_proxy = (block_proxy - np.nanmin(block_proxy)) / (np.nanmax(block_proxy) - np.nanmin(block_proxy))


def closest_to_ref_center():
    ''' Find the point with large enough (>args.thresh) block_proxy that is the closest to
    the desired ref center defined by args.refx and args.refy'''
    global desired_ref_center_x, desired_ref_center_y, refx, refy
    ## choose distance closer to center
    desired_ref_center_y = int(block_proxy.shape[0] * args.refy)
    desired_ref_center_x = int(block_proxy.shape[1] * args.refx)
    refys, refxs = np.where(block_proxy > np.nanpercentile(block_proxy, args.percentile))
    distance_to_center = np.sqrt((refys - desired_ref_center_y) ** 2 + (refxs - desired_ref_center_x) ** 2)
    nearest_to_center = np.min(distance_to_center)
    index_nearest_to_center = np.where(distance_to_center == nearest_to_center)
    refy = refys[index_nearest_to_center][0]
    refx = refxs[index_nearest_to_center][0]
    print("Reference window nearest to center: refy={}, refx={}".format(refy, refx))


def plot_ref_proxies():
    ### load example unw for plotting in block resolution
    if args.sbovl:
        unwfile = os.path.join(ifgdir, ifgdates[0], ifgdates[0] + '.sbovldiff.adf.mm')
    else:
        unwfile = os.path.join(ifgdir, ifgdates[0], ifgdates[0] + '.unw')
    
    unw = io_lib.read_img(unwfile, length, width)
    unw[unw == 0] = np.nan
    unw_example = block_sum(unw, window_size)
    unw_example[unw_example == 0] = np.nan
    
    # plot figure
    fig, ax = plt.subplots(2, 3, sharey='all', sharex='all')
    im_unw = ax[0, 0].imshow(block_unw, vmin=0, vmax=1)
    im_coh = ax[0, 1].imshow(block_coh, vmin=0, vmax=1)
    if not args.ignore_comp:
        im_con = ax[1, 0].imshow(block_con, vmin=0, vmax=1)
    im_hgt = ax[1, 1].imshow(block_rms_hgt, vmin=0, vmax=1)
    im_proxy = ax[0, 2].imshow(block_proxy, vmin=0, vmax=1)
    im_example = ax[1, 2].imshow(unw_example, cmap=cm.RdBu)
    plt.colorbar(im_unw, ax=ax, orientation='horizontal')

    ax[0, 0].set_title("block_sum_unw")
    ax[0, 1].set_title("block_sum_coh")
    ax[1, 0].set_title("block_sum_comp_size")
    ax[1, 1].set_title("block_std_hgt")
    ax[0, 2].set_title("proxy")
    ax[1, 2].set_title("unw example")

    ax[0, 0].scatter(refx, refy, s=3, c='red')
    ax[0, 1].scatter(refx, refy, s=3, c='red')
    ax[0, 2].scatter(refx, refy, s=3, c='red')
    ax[0, 2].scatter(desired_ref_center_x, desired_ref_center_y, s=3, c='black')
    ax[1, 0].scatter(refx, refy, s=3, c='red')
    ax[1, 1].scatter(refx, refy, s=3, c='red')
    ax[1, 2].scatter(refx, refy, s=3, c='red')

    fig.savefig(reference_png, dpi=300, bbox_inches=None) #'tight')
    plt.close()


def save_reference_to_file():
    global refx1, refx2, refy1, refy2

    # calc reference window in full resolution ifg
    refx1, refx2, refy1, refy2 = refx*window_size, (refx+1)*window_size, refy*window_size, (refy+1)*window_size
    print('Selected ref in full resolution: {}:{}/{}:{}'.format(refx1, refx2, refy1, refy2), flush=True)

    ### Save ref
    if not args.sbovl:
        refsfile = os.path.join(infodir, '120ref.txt')
    else:
        refsfile = os.path.join(infodir, '12ref.txt')
    with open(refsfile, 'w') as f:
        print('{}:{}/{}:{}'.format(refx1, refx2, refy1, refy2), file=f)


def discard_ifg_with_all_nans_at_ref():
    global noref_ifg, retained_ifgs
    print("Check if any ifg have all nan values in the selected reference window and export referenced ifgs")
    ### identify IFGs with all nan in the reference window
    ### Check ref exist in unw. If not, list as noref_ifg
    noref_ifg = []
    for ifgd in ifgdates:
        # add about ori:
        if args.sbovl:
            unwfile = os.path.join(ifgdir, ifgd, ifgd+'.sbovldiff.adf.mm.ori')
            if not os.path.exists(unwfile):
                unwfile = os.path.join(ifgdir, ifgd, ifgd+'.sbovldiff.adf.mm')
        else:
            unwfile = os.path.join(ifgdir, ifgd, ifgd+'.unw.ori')
            if not os.path.exists(unwfile):
                unwfile = os.path.join(ifgdir, ifgd, ifgd+'.unw')
        unw_data = io_lib.read_img(unwfile, length, width)
        unw_ref = unw_data[refy1:refy2, refx1:refx2]

        unw_ref[unw_ref == 0] = np.nan # Fill 0 with nan
        if np.all(np.isnan(unw_ref)):
            noref_ifg.append(ifgd)

            # plot no_ref_ifg with reference window to no_ref folder
            pngfile = os.path.join(no_ref_dir, ifgd + '.png')
            plot_lib.make_im_png(unw_data, pngfile, cmc.roma.reversed(), ifgd,
                                 vmin=np.nanpercentile(unw_data, 1), vmax=np.nanpercentile(unw_data, 99),
                                 ref_window=[refx1, refx2, refy1, refy2])

        # else:  # save referenced unw to original folder
        #     unw_referenced = unw_data - np.nanmean(unw_ref)
        #     unw_referenced.flatten().tofile(unwfile)

    # save list of no_ref_ifg to a text file in info directory

    print("{} ifgs are discarded due to all nan values in the reference window...".format(len(noref_ifg)))
    with open(noref_ifgfile, 'a') as f:
        for i in noref_ifg:
            print('{}'.format(i), file=f)
            print('{}'.format(i))
    retained_ifgs = list(set(ifgdates)-set(noref_ifg))

    # export weak links
    with open(os.path.join(infodir, '120retained_links.txt'), 'w') as f:
        for i in retained_ifgs:
            print('{}'.format(i), file=f)

    return retained_ifgs


def component_network_analysis(retained_ifgs):
    global strong_links, weak_links, edge_cuts, node_cuts
    print("Separate strong and weak links in the remaining network")
    strong_links, weak_links, edge_cuts, node_cuts = tools_lib.separate_strong_and_weak_links(retained_ifgs, component_statsfile, remove_edge_cuts=not args.keep_edge_cuts, remove_node_cuts=not args.keep_node_cuts, skip_node_cuts=args.skip_node_cuts)

    # export weak links
    with open(weak_ifgfile, 'w') as f:
        for i in weak_links:
            print('{}'.format(i), file=f)
            # print('{}'.format(i))

    # export strong links
    with open(strong_ifgfile, 'w') as f:
        for i in strong_links:
            print('{}'.format(i), file=f)

    # export edge cuts
    print("{} ifgs are edge cuts".format(len(edge_cuts)))
    with open(edge_cut_ifgfile, 'w') as f:
        for i in edge_cuts:
            print('{}'.format(i), file=f)
            print('{}'.format(i))

    # export edge cuts
    print("{} epochs are node cuts".format(len(node_cuts)))
    with open(node_cut_ifgfile, 'w') as f:
        for i in node_cuts:
            print('{}'.format(i), file=f)
            print('{}'.format(i))


def get_bperp_from_ifgdates(ifgdates):
    ## Read bperp data or dummy
    imdates = tools_lib.ifgdates2imdates(ifgdates)
    bperp_file = os.path.join(ccdir, 'baselines')
    
    # Check if the baselines file exists and contains sufficient data
    if os.path.exists(bperp_file):
        with open(bperp_file, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]  # Remove empty lines
        if len(lines) >= len(imdates):  # Ensure enough entries
            bperp = io_lib.read_bperp_file(bperp_file, imdates)
        else:
            ##baselines file contain fewer entries than the number of ifgs, so dummy values will be used
            bperp = np.random.random(len(imdates)).tolist()
    else:  # Generate dummy baselines if file doesn't exist
        print(f"WARNING: Baselines file not found. Using dummy values.")
        bperp = np.random.random(len(imdates)).tolist()
    
    return bperp


def plot_networks():
    #%% Plot network
    bperp = get_bperp_from_ifgdates(ifgdates)

    pngfile = os.path.join(netdir, 'network120_red_no_ref.png')
    plot_lib.plot_network(ifgdates, bperp, noref_ifg, pngfile, plot_bad=True, label_name='NaN at Ref')

    bperp = get_bperp_from_ifgdates(retained_ifgs)
    pngfile = os.path.join(netdir, 'network120_remain_strong_cuts.png')
    plot_lib.plot_strong_weak_cuts_network(retained_ifgs, bperp, weak_links, edge_cuts, node_cuts, pngfile, plot_weak=True)


def check_components_existence():
    missingcomp = False
    for ifgd in ifgdates:
        confile = os.path.join(ccdir, ifgd, ifgd + '.conncomp')
        if not os.path.exists(confile):
            missingcomp = True
            break
    if missingcomp:
        print('At least one ifg has missing conncomp file - not using conncomps')
        args.ignore_comp=True


def main():
    global retained_ifgs
    start()
    init_args()
    set_input_output()
    read_length_width()
    decide_reference_window_size()
    get_ifgdates()
    if not args.ignore_comp:
        check_components_existence()

    calc_block_sum_of_unw_coh_component_size()
    calc_height_std()
    clip_normalise_combine_indices()

    closest_to_ref_center()
    plot_ref_proxies()
    save_reference_to_file()
    retained_ifgs = discard_ifg_with_all_nans_at_ref()
    component_network_analysis(retained_ifgs)
    plot_networks()
    finish()


if __name__ == "__main__":
    main()




