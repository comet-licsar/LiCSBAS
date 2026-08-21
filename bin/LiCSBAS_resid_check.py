#!/usr/bin/env python3
"""
========
Overview
========
This script checks the LiCSBAS13 residual statistics for sbovl data and
updates the list of bad interferograms to be discarded before rerunning
LiCSBAS13.

The script reads the residual RMS values from:

    TS_GEOCml*/info/13resid.txt

Interferograms are flagged as bad using two criteria:

1. Zero-residual interferograms
   - Any interferogram with RMS = 0 is treated as problematic.
   - These usually indicate failed, empty, or invalid residual estimates.

2. High-residual outliers
   - RMS values equal to zero are first excluded from the statistical
     calculation.
   - The mean and standard deviation are then computed from the remaining
     non-zero RMS values.
   - An interferogram is flagged as noisy if:

         RMS > mean(RMS) + 2 * std(RMS)

   - This identifies interferograms whose residuals are significantly larger
     than the typical residual level of the network.

The newly detected bad interferograms are merged with any existing entries in:

    TS_GEOCml*/info/11bad_ifg.txt

The final output is a sorted, unique list of bad interferograms. This file can
then be used by LiCSBAS to discard these noisy interferograms in the following
processing steps.

===============
Input & output files
===============
Inputs in TS_GEOCml*/:
 - info/
   - 13resid.txt      : Residual RMS values from LiCSBAS13

Outputs in TS_GEOCml*/:
 - info/
   - 11bad_ifg.txt    : Updated list of bad interferograms to be discarded
   - 11bad_ifg.txt.backup : Backup of previous bad interferogram list, or just rerun LiCSBAS11 to get original bad interferogram?
 - TS_*/13resid_bad
    - epoch.res.png : selected bad interferograms with their RMS values for visual inspection

=====
Usage
=====
LiCSBAS11_check_unw.py -t TS_GEOCml*
"""
#%% Change log
'''
Muhammet Nergizci-COMET, Leeds, 2026-05-18
- turn the 95 percentile thresholding as default as the histogram is skewed.
Muhammet Nergizci-COMET, Leeds, 2026-05-05
- Updates the Overview, create the backup and screen the selected bad interferograms.
Muhammet Nergizci-COMET, Leeds, 2025-08-07
- First application
'''

#%% Import
from LiCSBAS_meta import *
import getopt
import os
import sys
import time
import shutil
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

class Usage(Exception):
    """Usage context manager"""
    def __init__(self, msg):
        self.msg = msg

#%% Helper
def days_between(pair):
    try:
        d1_str, d2_str = pair.split('_')
        d1 = datetime.strptime(d1_str, '%Y%m%d')
        d2 = datetime.strptime(d2_str, '%Y%m%d')
        return abs((d2 - d1).days)
    except:
        return -1

#%% Main
def main(argv=None):

    #%% Check argv
    if argv == None:
        argv = sys.argv

    start = time.time()
    print("\n{} ver{} {} {}".format(os.path.basename(argv[0]), ver, date, author), flush=True)
    print("{} {}".format(os.path.basename(argv[0]), ' '.join(argv[1:])), flush=True)


    #%% Set default
    tsadir = []
    sigma2_threshold = False
 
    #%% Read options
  
    # Parse options
    try:
        opts, args = getopt.getopt(argv[1:], "ht:", ["help"])
    except getopt.GetoptError as err:
        print(str(err))
        print(__doc__)
        return 1

    for o, a in opts:
        if o in ("-h", "--help"):
            print(__doc__)
            return 0
        elif o == "-t":
            tsadir = a

    if not tsadir or not os.path.isdir(tsadir):
        print("ERROR: Please provide a valid TS directory using -t", flush=True)
        return 1
    
    infodir = os.path.join(tsadir, 'info')
    restxtfile = os.path.join(infodir,'13resid.txt')
    badifg_file = os.path.join(infodir, '11bad_ifg.txt')
    resid_folder = os.path.join(tsadir, '13resid')
    resid_checked_dir = os.path.join(tsadir, '13resid_bad')
    

    if not os.path.isfile(restxtfile):
        print("ERROR: Residual file {} does not exist!".format(restxtfile), flush=True)
        return 1
    
    pairs, rms_values = [], []
    with open(restxtfile, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) >= 2:
                pairs.append(parts[0])
                rms_values.append(float(parts[1]))
                
        
    pairs = np.array(pairs)
    rms_values = np.array(rms_values)

    # Zero residuals
    zero_mask = rms_values == 0.0
    zero_pairs = pairs[zero_mask]

    # Remove zeros for stats
    valid_mask = rms_values != 0.0
    pairs = pairs[valid_mask]
    rms_values = rms_values[valid_mask]
    # breakpoint()
    # Thresholding
    if sigma2_threshold:
        mean = np.mean(rms_values)
        std = np.std(rms_values)
        threshold = mean + 2 * std
    
    else:
        # percentile-based thresholding (alternative)
        threshold = np.percentile(rms_values, 95)

    outlier_indices = np.where(rms_values > threshold)[0]
    outlier_pairs = pairs[outlier_indices]

    print("\n===== Bad Interferograms Summary =====")

    print(f"\nZero-residual interferograms ({len(zero_pairs)}):")
    for p in sorted(zero_pairs):
        print(f"  {p}  RMS=0.0000")

    print(f"\nHigh-RMS outliers ({len(outlier_pairs)}):")
    for idx in outlier_indices:
        print(f"  {pairs[idx]}  RMS={rms_values[idx]:.4f}")

    # Combine all unique problematic pairs
    bad_set = set()
    bad_set.update(zero_pairs)
    bad_set.update(outlier_pairs)
    
    #plot histogram of RMS values with threshold
    plt.figure(figsize=(10,6))
    plt.hist(rms_values, bins=30, color='blue', alpha=0.7, label='RMS values')
    plt.axvline(threshold, color='red', linestyle='dashed', linewidth=2, label=f'Threshold = {threshold:.4f}')
    plt.xlabel('RMS Value')
    plt.ylabel('Frequency')
    plt.title('Histogram of Residual RMS Values')
    plt.legend()
    plt.grid()
    plt.tight_layout()
    hist_file = os.path.join(infodir, '13resid_histogram.png')
    plt.savefig(hist_file)
    print(f"\nHistogram of RMS values saved to: {hist_file}")
    
    #linking the selected bad interferograms for visual inspection
    if not os.path.exists(resid_checked_dir):
        os.makedirs(resid_checked_dir)
    for pair in bad_set:
        resid_file = os.path.join(resid_folder, f"{pair}.res.png")
        if os.path.isfile(resid_file):
            link_name = os.path.join(resid_checked_dir, f"{pair}.res.png")
            if not os.path.exists(link_name):
                shutil.copy2(resid_file, link_name)

    # # Sort and write output
    # bad_list = sorted(bad_set)
    # print(f"  Total bad interferograms: {len(bad_list)}")
    # if bad_list:
    #     with open(badifg_file, 'w') as f:
    #         for pair in bad_list:
    #             f.write(pair + '\n')
    #     print(f"  Written to: {badifg_file}")
    # else:
    #     print("  No bad interferograms found.")
    
    # Combine with existing if present
    existing_pairs = set()
    if os.path.exists(badifg_file):
        #create backup
        backup_file = badifg_file + f".backup"
        if os.path.exists(backup_file):
            print(f"Backup already exists: {backup_file}")
        else:
            shutil.copy2(badifg_file, backup_file)
            print(f"Backup created: {backup_file}")
        # Read existing bad interferograms
        with open(badifg_file, 'r') as f:
            for line in f:
                if line.strip():
                    existing_pairs.add(line.strip())

    # Merge and sort all unique bad interferograms
    all_bad_pairs = existing_pairs.union(bad_set)
    bad_list = sorted(all_bad_pairs)

    # Write updated file
    with open(badifg_file, 'w') as f:
        for pair in bad_list:
            f.write(pair + '\n')
    
    #%% Finish
    elapsed_time = time.time()-start
    hour = int(elapsed_time/3600)
    minite = int(np.mod((elapsed_time/60),60))
    sec = int(np.mod(elapsed_time,60))
    print("\nElapsed time: {0:02}h {1:02}m {2:02}s".format(hour,minite,sec))

    print('\n{} Successfully finished!!\n'.format(os.path.basename(argv[0])))
    
    return 0


#%% main
if __name__ == "__main__":
    sys.exit(main())

