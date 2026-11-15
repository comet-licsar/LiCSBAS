#!/usr/bin/env python3

#%% Import
import numpy as np
import argparse
import sys
import LiCSBAS_io_lib as io_lib
import LiCSBAS_tools_lib as tools_lib


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
    parser.add_argument('-p', dest='primary_epoch_list', default=None, type=str, help="input text file containing a list of epochs to serve as primary epochs")
    parser.add_argument('-s', dest='secondary_epoch_list', default=None, type=str, help="input text file containing a list of epochs to serve as secondary epochs")
    parser.add_argument('-e', dest='existing_ifg_list', default=None, type=str, help="input text file containing a list of epochs, used to avoid generating existing ifgs in the output list, or used to provide primary and secondary epochs when -p and -s are not used. ")
    parser.add_argument('-o', dest='output_ifg_list', default="dense_list.txt", type=str, help="output text file containing a list of epochs")
    parser.add_argument('-l', dest='minimum_temporal_baseline', default=13, type=int, help="minimum temporal baseline in days")
    parser.add_argument('-u', dest='maximum_temporal_baseline', default=400, type=int, help="maximum temporal baseline in days")
    parser.add_argument('-m', dest='maximum_number', default=500, type=int, help="evenly sample new list to below this total number")
    args = parser.parse_args()


if __name__ == "__main__":
    init_args()

    # get epochs for generating new ifgs
    if args.primary_epoch_list and args.secondary_epoch_list:
        epoch1 = np.loadtxt(args.primary_epoch_list)
        epoch2 = np.loadtxt(args.secondary_epoch_list)
    elif args.existing_ifg_list:
        ifgdates = io_lib.read_ifg_list(args.existing_ifg_list)
        epoch1 = epoch2 = tools_lib.ifgdates2imdates(ifgdates)
    else:
        sys.exit("no primary or secondary epoch list or no existing ifg list ")

    # load list of any pre-existing ifgs
    if args.existing_ifg_list:
        existing_ifgdates = io_lib.read_ifg_list(args.existing_ifg_list)
    else:
        existing_ifgdates = []

    # generate a new ifg list
    ifgdates = []
    for e1 in epoch1:
        for e2 in epoch2:
            ifgdates.append(e1+"_"+e2)

    # only keep those with allowed range of temporal baselines
    dt = tools_lib.calc_temporal_baseline(ifgdates)
    mask = np.logical_and(np.array(dt) > args.minimum_temporal_baseline, np.array(dt) < args.maximum_temporal_baseline)
    ifgdates_masked = np.array(ifgdates)[mask].tolist()
    new_ifgdates = sorted(list(set(ifgdates_masked)-set(existing_ifgdates)))

    if len(new_ifgdates) > args.maximum_number:
        # separate new_ifgdates into two lists, one with primary epochs before 2017, one after 2017
        new_primary = np.array([int(x[:4]) for x in new_ifgdates])
        before_2017_ifgs = np.array(new_ifgdates)[new_primary < 2017].tolist()
        after_2017_ifgs = np.array(new_ifgdates)[new_primary >= 2017].tolist()

        # downsample list of ifgs after 2017 to make total number of ifgs below -m threshold
        length = len(new_ifgdates)
        ratio = length / args.maximum_number
        downsample_factor_before_2017 = int(np.floor(ratio))
        downsample_factor_after_2017 = int(np.ceil(ratio))
        downsampled_before_2017_ifgs = before_2017_ifgs[::downsample_factor_before_2017]
        downsampled_after_2017_ifgs = after_2017_ifgs[::downsample_factor_after_2017]
        to_process_ifgdates = downsampled_before_2017_ifgs + downsampled_after_2017_ifgs
    else:
        to_process_ifgdates = new_ifgdates

    # export to text file
    with open(args.output_ifg_list, 'w') as f:
        for i in to_process_ifgdates:
            print('{}'.format(i), file=f)


