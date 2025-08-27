#!/usr/bin/env python3
"""
========
Overview
========
Python3 library of time series analysis tools for LiCSBAS.

=========
Changelog
=========
2025-08-22 ML: url extractor for the 'future' LiCSAR HTMLs
2024-12-13 Muhammet Nergizci, ULeeds
 - Add weights to multilooking
2024-10-22 Milan Lazecky, ULeeds
 - Add function to get offsets regarding earthquakes (used by optional LiCSBAS_cum2vel)
v1.8 20210309 Yu Morishita, GSI
 - Add GPU option to fit2dh (but not recommended)
v1.7 20210205 Yu Morishita, GSI
 - Add cm_insar, cm_isce, get_cmap
v1.6.2 20201225 Yu Morishita, GSI
 - Avoid error when remote file is empty
v1.6.1 20201207 Yu Morishita, GSI
 - Check size and retry if error in download_data
v1.6 20200911 Yu Morishita, GSI
 - STDOUT time and size in download_data
 - Add convert_size
v1.5 20200828 Yu Morishita, GSI
 - Update for matplotlib >= 3.3
 - Use nearest interpolation for insar cmap to avoid aliasing
v1.4 20200703 Yu Morishita, GSI
 - Replace problematic terms
 - Small bug (shift) fix in read_range_geo
v1.3 20200503 Yu Morishita, GSI
 - Update download_data (thanks to sahitono)
v1.2 20200227 Yu Morishita, Uni of Leeds and GSI
 - Add read_point and fit2dh
v1.1 20190916 Yu Morishita, Uni of Leeds and GSI
 - Add read_range_line and read_range_line_geo
v1.0 20190730 Yu Morishita, Uni of Leeds and GSI
 - Original implementation
"""
import os
import sys
import re
import time
import requests
import dateutil
import datetime as dt
import numpy as np
import warnings
from bs4 import BeautifulSoup
from matplotlib.colors import LinearSegmentedColormap as LSC
from matplotlib import pyplot as plt
import matplotlib.path as path
try:
    from scipy import interpolate
except:
    print('warning, scipy not installed') #. no interpolation tools')

try:
    import networkx as nx
except:
    print('warning, networkx is not installed') #. Some LiCSBAS Plus functions will not work')
import h5py as h5
try:
    import pandas as pd
except:
    print('warning, pandas is not installed')

try:
    from libcomcat.search import search
except:
    print('warning, libcomcat is not installed')

#%%
def bl2xy(lon, lat, width, length, lat1, postlat, lon1, postlon):
    """
    lat1 is north edge and postlat is negative value.
    lat lon values are in grid registration
    x/y index start from 0, end with width-1
    """
    x = int(np.round((lon - lon1)/postlon))
    y = int(np.round((lat - lat1)/postlat))

    return [x, y]


#%%
def comp_size_time(file_remote, file_local):
    """
    Compare size and time of remote and local files.
    Returns:
        0 : Size is identical and local time is new
        1 : Size is not identical
        2 : Size is identical but remote time is new
        3 : Remote not exist
    """

    response = requests.head(file_remote, allow_redirects=True)

    if response.status_code != 200:
        return 3
    elif response.headers.get("Content-Length") is None:
        ## Remote file exist but empty
        return 3

    size_remote = int(response.headers.get("Content-Length"))
    size_local = os.path.getsize(file_local)
    if size_remote != size_local: ### Different size
        return 1

    time_remote = dateutil.parser.parse(response.headers.get("Last-Modified"))
    time_local = dt.datetime.fromtimestamp(os.path.getmtime(file_local), dt.timezone.utc)
    if time_remote > time_local: ### New file
        return 2

    return 0


#%%
def cm_insar():
    rgbs = np.zeros((256,3), dtype=np.uint8)

    for kk in range(85):
        rgbs[kk,0] = kk*3
        rgbs[kk,1] = 255-kk*3
        rgbs[kk,2] = 255

    rgbs[85:170,0] = rgbs[0:85,2]
    rgbs[85:170,1] = rgbs[0:85,0]
    rgbs[85:170,2] = rgbs[0:85,1]

    rgbs[170:255,0] = rgbs[0:85,1]
    rgbs[170:255,1] = rgbs[0:85,2]
    rgbs[170:255,2] = rgbs[0:85,0]

    rgbs[255,0] = 0
    rgbs[255,1] = 255
    rgbs[255,2] = 255

    rgbs = np.roll(rgbs, int(256/2), axis=0)  #shift green to the center
    rgbs = (rgbs/255.0*200+55)/255.0

    return LSC.from_list('cm_insar', rgbs)


#%%
def cm_isce():
    # https://github.com/insarlab/MintPy/blob/main/mintpy/objects/colors.py#L199
    # Almost same as GAMMA except for bottom RGB (0vs0.2), shift and flip
    rgbs = np.zeros((256,3), dtype=np.uint8)

    for kk in range(85):
        rgbs[kk,0] = kk*3
        rgbs[kk,1] = 255-kk*3
        rgbs[kk,2] = 255

    rgbs[85:170,0] = rgbs[0:85,2]
    rgbs[85:170,1] = rgbs[0:85,0]
    rgbs[85:170,2] = rgbs[0:85,1]

    rgbs[170:255,0] = rgbs[0:85,1]
    rgbs[170:255,1] = rgbs[0:85,2]
    rgbs[170:255,2] = rgbs[0:85,0]

    rgbs[255,0] = 0
    rgbs[255,1] = 255
    rgbs[255,2] = 255

    rgbs = np.roll(rgbs, int(256/2-214), axis=0)  #shift green to the center
    rgbs = np.flipud(rgbs)   #flip up-down so that orange is in the later half (positive)
    rgbs = rgbs/255.0

    return LSC.from_list('cm_isce', rgbs)


#%%
def cmap_insar():
    """
    How to use cmap_insar (GAMMA standard rainbow cmap):
        import matplotlib as mpl
        from matplotlib import pyplot as plt
        cdict = cmap_insar()
        plt.register_cmap(cmap=mpl.colors.LinearSegmentedColormap('insar', cdict))
        plt.register_cmap(name='insar', data=cdict)
        plt.imshow(array, cmap='insar', vmin=-np.pi, vmax=np.pi, interpolation='nearest')

    Note:
        - Input array should be wrapped and in radian
        - To wrap unwrapped phase, np.angle(np.exp(1j*unw/cycle)*cycle)
    """

#    These are for 0-2pi, not -pi to pi
    red = [255,255,255,255,240,203,165,127,90,55,92,130,167,205,243,255,255,255]
    green = [118,156,193,231,255,255,255,255,255,255,217,179,142,104,66,80,118,156]
    blue = [191,153,116,78,69,106,144,182,219,255,255,255,255,255,255,229,191,153]
    phase = [k/32 for k in range(1,33,2)]
    phase = [0] + phase + [1]

    red_norm = [ k/255 for k in red ] + [ red[0]/255 ]
    green_norm = [ k/255 for k in green ] + [ green[0]/255 ]
    blue_norm = [ k/255 for k in blue ] + [ blue[0]/255 ]

    redtuple=[]
    greentuple=[]
    bluetuple=[]
    for j in range(18):
        redtuple.append((phase[j],red_norm[j],red_norm[j+1]))
        greentuple.append((phase[j],green_norm[j],green_norm[j+1]))
        bluetuple.append((phase[j],blue_norm[j],blue_norm[j+1]))

    redtuple=tuple(redtuple)
    greentuple=tuple(greentuple)
    bluetuple=tuple(bluetuple)

    cdict = { 'red': redtuple, 'green': greentuple, 'blue': bluetuple }

    return cdict


#%%
def convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(np.floor(np.log(size_bytes)/np.log(1024)))
   p = np.power(1024, i)
   s = round(size_bytes / p, 2)
   return "%s%s" % (s, size_name[i])


def extract_url_licsar(url):
    ''' new since Aug 2025+: URL gets different from direct to HTML file with a link..
    '''
    # first try if the direct url actually works (old version):
    response = requests.head(url, allow_redirects=True)
    if response.status_code == 200:
        return url
    else:
        url = os.path.dirname(url)
        fname = os.path.basename(url)
        response = requests.get(url)
        if response.status_code != 200:
            return None # this does not exist
        response.encoding = response.apparent_encoding  # avoid garble
        html_doc = response.text
        soup = BeautifulSoup(html_doc, "html.parser")
        tag = soup.find(href=re.compile(fname))
        if tag:
            return tag.get('href')
        else:
            return None


#%%
def download_data(url, file, n_retry=3):
    for i in range(n_retry):
        try:
            start = time.time()
            with requests.get(url) as res:
                res.raise_for_status()
                size_remote = int(res.headers.get("Content-Length"))
                with open(file, "wb") as output:
                     output.write(res.content)
                size_local = os.path.getsize(file)
                if size_remote != size_local: ### Different size
                    raise IOError('Downloaded file not complete')

            elapsed = int(time.time()-start)
            if elapsed==0: elapsed=elapsed+1
            fsize = convert_size(os.path.getsize(file))
            speed = convert_size(int(os.path.getsize(file)/elapsed))
            print('    {}, {}, {}s, {}/s'.format(os.path.basename(file),
                   fsize, elapsed, speed), flush=True)
            return # success

        except Exception as e:
            print(    '    {} for {} in {}th try'.format(
                e.__class__.__name__, os.path.basename(url), i+1), flush=True)
            pass # try again

    print("    Error while downloading from {}".format(url),
          file=sys.stderr, flush=True)
    return # fail


def interpolate_2d(inarray, method='linear'):
    ''' A simple interpolation - without assessing pixels outside of the filled convex hull.
    Methods as 'nearest', 'linear', or 'cubic'
    '''
    array = np.ma.masked_invalid(inarray)
    x = np.arange(0, array.shape[1])
    y = np.arange(0, array.shape[0])
    xx, yy = np.meshgrid(x, y)
    x1 = xx[~array.mask]
    y1 = yy[~array.mask]
    newarr = array[~array.mask]
    newarr = interpolate.griddata((x1, y1), newarr.ravel(), (xx, yy), method=method)
    newarr = np.array(newarr)
    return newarr


#%%
def fit2d(A,w=None,deg="1"):
    """
    Estimate best fit plain with indicated degree of polynomial.

    Inputs:
        A : Input ndarray (can include nan)
        w : Wieight (1/std**2) for each element of A (with the same dimention as A)
        deg : degree of polynomial of fitting plain
         - 1   -> a+bx+cy (ramp)
         - bl -> a+bx+cy+dxy (biliner)
         - 2   -> a+bx+cy+dxy+ex**2_fy**2 (2d polynomial)

    Returns:
        Afit : Best fit plain with the same demention as A
        m    : set of parameters of best fit plain (a,b,c...)

    """
    import statsmodels.api as sm

    ### Make design matrix G
    length,width = A.shape #read dimension
    Xgrid,Ygrid = np.meshgrid(np.arange(width),np.arange(length)) #mesh grid

    if str(deg) == "1":
        G = np.stack((np.ones((length*width)), Xgrid.flatten(), Ygrid.flatten())).T
    elif str(deg) == "bl":
        G = np.stack((np.ones((length*width)), Xgrid.flatten(), Ygrid.flatten(), Xgrid.flatten()*Ygrid.flatten())).T
    elif str(deg) == "2":
        G = np.stack((np.ones((length*width)), Xgrid.flatten(), Ygrid.flatten(), Xgrid.flatten()*Ygrid.flatten(), Xgrid.flatten()**2, Ygrid.flatten()**2)).T
    else:
        print('\nERROR: Not proper deg ({}) is used\n'.format(deg), file=sys.stderr)
        return False

    ### Handle nan by 0 padding and 0 weight
    # Not drop in sm because cannot return Afit
    if np.any(np.isnan(A)):
        bool_nan = np.isnan(A)
        A = A.copy() # to avoid change original value in main
        A[bool_nan] = 0
        if w is None:
            w = np.ones_like(A)
        w = w.copy() # to avoid change original value in main
        w[bool_nan] = 0

    ### Invert
    if w is None: ## Ordinary LS
        results = sm.OLS(A.ravel(), G).fit()
    else: ## Weighted LS
        results = sm.WLS(A.ravel(), G, weights=w.ravel()).fit()

    m = results.params
    Afit = np.float32(results.predict().reshape((length,width)))

    return Afit,m


#%%
def fit2dh(A, deg, hgt, hgt_min, hgt_max, gpu=False):
    """
    Estimate best fit 2d ramp and topography-correlated component simultaneously.

    Inputs:
        A   : Input ndarray (can include nan)
        deg : degree of polynomial for fitting ramp
          - 1  -> a+bx+cy (ramp, default)
          - bl -> a+bx+cy+dxy (biliner)
          - 2  -> a+bx+cy+dxy+ex**2_fy**2 (2d polynomial)
          - []  -> a (must be used with hgt)
        hgt : Input hgt to estimate coefficient of topo-corr component
              If blank, don*t estimate topo-corr component.
        hgt_min : Minimum hgt to take into account in hgt-linear
        hgt_max : Maximum hgt to take into account in hgt-linear
        gpu     : GPU flag

    Returns:
        Afit : Best fit solution with the same demention as A
        m    : Set of parameters of best fit plain (a,b,c...)

    Note: GPU option seems slow and may return error when the size is large.
          Not recommended.

    """
    if gpu:
        import cupy as xp
        A = xp.asarray(A)
        hgt = xp.asarray(hgt)
        hgt_min = xp.asarray(hgt_min)
        hgt_max = xp.asarray(hgt_max)
    else:
        xp = np

    ### Make design matrix G
    length, width = A.shape

    if not deg:
        G = xp.ones((length*width))
    else:
        Xgrid, Ygrid = xp.meshgrid(xp.arange(width), xp.arange(length))
        Xgrid1 = Xgrid.ravel()
        Ygrid1 = Ygrid.ravel()

        if str(deg) == "1":
            G = xp.stack((Xgrid1, Ygrid1)).T
        elif str(deg) == "bl":
            G = xp.stack((Xgrid1, Ygrid1, Xgrid1*Ygrid1)).T
        elif str(deg) == "2":
            G = xp.stack((Xgrid1, Ygrid1, Xgrid1*Ygrid1,
                          Xgrid1**2, Ygrid1**2)).T
        else:
            print('\nERROR: Not proper deg ({}) is used\n'.format(deg), file=sys.stderr)
            return False
        del Xgrid, Ygrid, Xgrid1, Ygrid1

        G = xp.hstack([xp.ones((length*width, 1)), G])

    if len(hgt) > 0:
        _hgt = hgt.copy()  ## Not to overwrite hgt in main
        _hgt[xp.isnan(_hgt)] = 0
        _hgt[_hgt<hgt_min] = 0
        _hgt[_hgt>hgt_max] = 0
        G2 = xp.vstack((G.T, hgt.ravel())).T ## for Afit
        G = xp.vstack((G.T, _hgt.ravel())).T
        del _hgt
    else:
        G2 = G

    G = G.astype(xp.int32)

    ### Invert
    mask = xp.isnan(A.ravel())
    m = xp.linalg.lstsq(G[~mask, :], A.ravel()[~mask], rcond=None)[0]

    Afit = ((xp.matmul(G2, m)).reshape((length, width))).astype(xp.float32)

    if gpu:
        Afit = xp.asnumpy(Afit)
        m = xp.asnumpy(m)
        del A, hgt, hgt_min, hgt_max, length, width, G, G2, mask

    return Afit, m


#%%
def get_cmap(cmap_name, cmapN=256):
    """
    Return cmap (LinearSegmentedColormap).
    cmap_name can be:
        - Matplotlib predefined name (e.g. viridis)
        - Scientific colour maps aka cmcrameri (e.g. SCM.roma or cmc.roma)
        - Generic Mapping Tools (e.g. GMT.polar)
        - cmocean (e.g. cmocean.phase)
        - colorcet (e.g. colorcet.CET_C1)
        - cm_insar, cm_isce
    All cmap can be reversed with "_r"
    """
    flag = 0 # mpl
    if cmap_name.startswith('cm_insar'):
        _cmap = cm_insar()
        flag = 1
    elif cmap_name.startswith('cm_isce'):
        _cmap = cm_isce()
        flag = 1
    elif cmap_name.startswith('SCM'):
        import cmcrameri.cm as CMAP  # or try the original 'import SCM as CMAP'
        flag = 2
    elif cmap_name.startswith('cmc'):
        import cmcrameri.cm as CMAP  # or try the original 'import SCM as CMAP'
        flag = 2
    elif cmap_name.startswith('GMT'):
        import GMT as CMAP
        flag = 2
    elif cmap_name.startswith('cmocean'):
        import cmocean as CMAP
        flag = 2
    elif cmap_name.startswith('colorcet'):
        import colorcet as CMAP
        flag = 3

    if flag >= 2:
        cmdir = os.path.dirname(CMAP.__file__)
        name = cmap_name.split('.')[1]
        if cmap_name.endswith('_r'):
            name = name[:-2]
        if flag == 2:
            file = os.path.join(cmdir, name, name+'.txt')
            if not os.path.exists(file):
                file = os.path.join(cmdir, 'cmaps', name + '.txt')
            cm_data = np.loadtxt(file)
        elif flag == 3:
            file = os.path.join(cmdir, name+'.csv')
            cm_data = np.loadtxt(file, delimiter=',')
        _cmap = LSC.from_list(name, cm_data)

    if flag >= 1:
        if cmap_name.endswith('_r'):
            _cmap = _cmap.reversed()
        try:
            plt.cm.register_cmap(name = cmap_name, cmap = _cmap)
        except:
            print('WARNING, the colourmap was already registered - not overwriting')

    cmap = plt.get_cmap(cmap_name, cmapN)

    return cmap


#%%
def get_ifgdates(ifgdir):
    """
    Get ifgdates and imdates in ifgdir.

    Returns:
        ifgdates : List of dates of ifgs
        imdates  : List of dates of images
    """
    ifgdates = [str(k) for k in sorted(os.listdir(ifgdir))
                if len(k) == 17
                and k[0] in ('1', '2')  #JF for ERS starting with 19*
                and k[8] =='_'
                and k[9] in ('1', '2') # JF
                and os.path.isdir(os.path.join(ifgdir, k))]

    return ifgdates


#%%
def get_patchrow(width, length, n_data, memory_size):
    """
    Get patch number of rows for memory size (in MB).

    Returns:
        n_patch : Number of patches (int)
        patchrow : List of the number of rows for each patch.
                ex) [[0, 1234], [1235, 2469],... ]
    """
    data_size = width*length*n_data*4/2**20  #in MiB, 4byte float
    n_patch = int(np.ceil(data_size/memory_size))
    ### Devide only row direction

    patchrow= []
    for i in range(n_patch):
        rowspacing = int(np.ceil(length/n_patch))
        patchrow.append([i*rowspacing,(i+1)*rowspacing])
        if i == n_patch-1:
            patchrow[-1][-1] = length

    return n_patch, patchrow



#%%
def ifgdates2imdates(ifgdates):
    primarylist = []
    secondarylist = []
    for ifgd in ifgdates:
        primarylist.append(ifgd[:8])
        secondarylist.append(ifgd[-8:])

    imdates = list(set(primarylist+secondarylist)) # set is a unique operator
    imdates.sort()

    return imdates


#%%
def ifgdates_to_edges(ifgdates):
    """ convert list of "20xxxxxx_20xxxxxx" into list of tuples ("20xxxxxx", "20xxxxxx") for networkx analysis"""
    edges = []
    for ifgd in ifgdates:
        edges.append(tuple((ifgd[:8], ifgd[9:])))
    return edges


def edges_to_ifgdates(edges):
    """ convert list of tuples ("20xxxxxx", "20xxxxxx") back to list of "20xxxxxx_20xxxxxx" """
    ifgdates = []
    for edge in edges:
        epoch1 = str(min(int(edge[0]), int(edge[1])))
        epoch2 = str(max(int(edge[0]), int(edge[1])))
        ifgdates.append(epoch1 + "_" + epoch2)
    return ifgdates


def select_ifgs_by_months(ifg_list, allowed_month, strict=True):
    """ Choose IFGs based on a list of allowed months given as string "1.2.3.10" separated by period
    strict = True: both epochs have to be in the allowed month
    strict = False: either epoch can be in the allowed month
    """
    primary_month = []
    secondary_month = []
    for pairs in ifg_list:
        primary_month.append(int(pairs[4:6]))
        secondary_month.append(int(pairs[13:15]))
    allowed_month = [int(i) for i in allowed_month.split(".")]
    primary_month_allowed = [month in allowed_month for month in primary_month]
    secondary_month_allowed = [month in allowed_month for month in secondary_month]
    if strict:
        mask = [a and b for a, b in zip(primary_month_allowed, secondary_month_allowed)]
    else:
        mask = [a or b for a, b in zip(primary_month_allowed, secondary_month_allowed)]
    selected_ifgs = [i for (i, v) in zip(ifg_list, mask) if v]
    return selected_ifgs

def calc_temporal_baseline(ifg_list):
    dt_list = []
    for ifg in ifg_list:
        mday = dt.datetime.strptime(ifg[:8], '%Y%m%d').toordinal()
        sday = dt.datetime.strptime(ifg[-8:], '%Y%m%d').toordinal()
        dt_ifg = sday - mday
        dt_list.append(dt_ifg)
    return dt_list

def separate_strong_and_weak_links(ifg_list, component_statsfile, remove_edge_cuts=True, remove_node_cuts=True, skip_node_cuts=False):
    """return a list of strong ifgs and a list of weak ifgs"""
    primarylist = []
    secondarylist = []
    for pairs in ifg_list:
        primarylist.append(pairs[:8])
        secondarylist.append(pairs[-8:])

    all_epochs = primarylist + secondarylist
    all_epochs.sort()
    epochs, counts = np.unique(all_epochs, return_counts=True)

    # iteratively drop weak ifgs associated with epochs with 1 or 2 links
    while len(epochs) > 0 and np.min(counts) < 2:
        strong_epoch_list = epochs[counts > 1]
        strong_primary_check = np.array([x in strong_epoch_list for x in primarylist])
        strong_secondary_check = np.array([x in strong_epoch_list for x in secondarylist])
        strong_ifg_check = np.logical_and(strong_primary_check, strong_secondary_check)
        primarylist = np.array(primarylist)[strong_ifg_check].tolist()
        secondarylist = np.array(secondarylist)[strong_ifg_check].tolist()

        epochs = primarylist + secondarylist
        epochs.sort()
        epochs, counts = np.unique(epochs, return_counts=True)

    edge_cuts = []
    node_cuts = []
    if len(epochs) > 0:
        strong_ifgs = [p+'_'+s for p, s in zip(primarylist, secondarylist)]

        # check if the ifgs after removing epochs with 1 or 2 ifgs form on connected network
        edges = ifgdates_to_edges(strong_ifgs)
        G = nx.Graph()
        G.add_edges_from(edges)
        number_of_components = len(list(nx.connected_components(G)))

        # compute other stats about the largest connected components
        if os.path.exists(component_statsfile): os.remove(component_statsfile)
        with open(component_statsfile, 'w') as f:
            print("Number_of_connected_components: {}".format(number_of_components), file=f)
            print("Number_of_connected_components: {}".format(number_of_components))

        # if not connected, extract the largest connected component based on number of epochs involved
        if not nx.is_connected(G):
            largest_cc = max(nx.connected_components(G), key=len)
            print("Not connected, hence largest_cc extracted...")
            Gs = nx.subgraph(G, largest_cc)
            G = nx.Graph(Gs)
            nx.draw(G, with_labels=True)
            plt.savefig('labels.png')


        # if the largest component network is not well-connected, highlight the edge cuts and node cuts
        if nx.edge_connectivity(G) == 1:
            print("Edge connectivity is {}".format(nx.edge_connectivity(G)))

            edge_cuts = edges_to_ifgdates(list(nx.bridges(G)))
            print("{} edge cuts".format(len(edge_cuts)))
            if remove_edge_cuts:
                # remove edge cuts and extract the largest connected component
                G.remove_edges_from(nx.bridges(G))
                largest_cc = max(nx.connected_components(G), key=len)
                Gs = nx.subgraph(G, largest_cc)
                G = nx.Graph(Gs)

        if nx.node_connectivity(G) == 1:
            print("Node connectivity is {}".format(nx.node_connectivity(G)))
            #
            # output a record of the node_cuts
            node_cuts = []
            # print("skipping node cut searching")
            if not skip_node_cuts:
                print(list(nx.all_node_cuts(G)))
                for i in list(nx.all_node_cuts(G)):
                    # print(i)
                    for j in list(i):
                        # print(j)
                        node_cuts.append(j)
                        # print(node_cuts)
                print("{} node cuts".format(len(node_cuts)))
                if remove_node_cuts:
                    # remove node cuts, which will waste edges connected to the node cuts. The remaining should be robust
                    while nx.node_connectivity(G) == 1:
                        # iteratively remove the first node cut from all_node_cuts and see if the remaining largest component has node cuts
                        G.remove_nodes_from(list(nx.all_node_cuts(G))[0])
                        largest_cc = max(nx.connected_components(G), key=len)
                        Gs = nx.subgraph(G, largest_cc)
                        G = nx.Graph(Gs)

        # compute other stats about the largest connected components
        degrees = [len(list(G.neighbors(n))) for n in G.nodes()]
        average_degree = np.mean(degrees)
        with open(component_statsfile, 'a') as f:
            print("Largest_cc_edge_number: {}".format(len(G.edges)), file=f)
            print("Largest_cc_edge_number: {}".format(len(G.edges)))
            print("Largest_cc_node_number: {}".format(len(G.nodes)), file=f)
            print("Largest_cc_node_number: {}".format(len(G.nodes)))
            print("Largest_cc_average_degree: {}".format(int(average_degree)), file=f)
            print("Largest_cc_average_degree: {}".format(int(average_degree)))
            print("Largest_cc_edge_connectivity: {}".format(nx.edge_connectivity(G)), file=f)
            print("Largest_cc_edge_connectivity: {}".format(nx.edge_connectivity(G)))
            print("Largest_cc_node_connectivity: {}".format(nx.node_connectivity(G)), file=f)
            print("Largest_cc_node_connectivity: {}".format(nx.node_connectivity(G)))

        # now only strong links in the largest connected component of the network is considered strong
        strong_ifgs = sorted(edges_to_ifgdates(G.edges))
        weak_ifgs = list(set(ifg_list)-set(strong_ifgs))
        weak_ifgs.sort()
        print("{} edges in total".format(len(ifg_list)))
        print("{} weak edges removed".format(len(weak_ifgs)))

    else:
        strong_ifgs = []
        weak_ifgs = ifg_list

    return strong_ifgs, weak_ifgs, edge_cuts, node_cuts


#%%
def multilook(array, nlook_r, nlook_c, n_valid_thre=0.5):
    """
    Nodata in input array must be filled with nan beforehand.
    if the number of valid data is less than n_valid_thre*nlook_r*nlook_c, return nan.
    """
    length, width = array.shape
    length_ml = int(np.floor(length/nlook_r))
    width_ml = int(np.floor(width/nlook_c))

    array_reshape = array[:length_ml*nlook_r,:width_ml*nlook_c].reshape(length_ml, nlook_r, width_ml, nlook_c)

    with warnings.catch_warnings(): ## To silence RuntimeWarning: Mean of empty slice
        warnings.simplefilter('ignore', RuntimeWarning)
        array_ml = np.nanmean(array_reshape, axis=(1, 3))

    n_valid = np.sum(~np.isnan(array_reshape), axis=(1, 3))
    bool_invalid = n_valid < n_valid_thre*nlook_r*nlook_c
    array_ml[bool_invalid] = np.nan

    return array_ml

def multilook_weighted(array, coherence, nlook_r, nlook_c, n_valid_thre=0.5, coh_thre=0.75):
    """
    Apply multilooking to the array, with weights based on coherence.
    Low-coherence pixels are ignored if they fall below the coherence threshold (coh_thre).
    
    Parameters:
    - array (ndarray): Input data array with `nan` for nodata.
    - coherence (ndarray): Coherence array with the same shape as `array`.
    - nlook_r (int): Number of rows to average in multilooking.
    - nlook_c (int): Number of columns to average in multilooking.
    - n_valid_thre (float): Minimum valid data fraction to keep pixel (default: 0.5).
    - coh_thre (float): Minimum coherence threshold to include pixel in multilooking.

    Returns:
    - array_ml (ndarray): Multilooked array.
    """
    length, width = array.shape
    length_ml = int(np.floor(length / nlook_r))
    width_ml = int(np.floor(width / nlook_c))

    # Reshape for block processing
    array_reshape = array[:length_ml * nlook_r, :width_ml * nlook_c].reshape(length_ml, nlook_r, width_ml, nlook_c)
    coherence_reshape = coherence[:length_ml * nlook_r, :width_ml * nlook_c].reshape(length_ml, nlook_r, width_ml, nlook_c)

    # Mask low-coherence pixels
    valid_mask = coherence_reshape >= coh_thre
    array_reshape[~valid_mask] = np.nan

    # Calculate weighted mean based on coherence
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        weighted_array = array_reshape * coherence_reshape
        sum_weights = np.nansum(coherence_reshape, axis=(1, 3))
        array_ml = np.nansum(weighted_array, axis=(1, 3)) / sum_weights

    # Apply validity threshold
    n_valid = np.sum(~np.isnan(array_reshape), axis=(1, 3))
    bool_invalid = n_valid < n_valid_thre * nlook_r * nlook_c
    array_ml[bool_invalid] = np.nan

    return array_ml

#%%
def read_point(point_str, width, length):
    if re.match('[0-9]*/[0-9]*', point_str):
        x, y = [int(s) for s in re.split('[/]', point_str)]
        if x > width-1 or y > length-1:
            print("\nERROR:", file=sys.stderr)
            print("Index exceed input dimension ({0},{1})!".format(width,length), file=sys.stderr)
            return False
    else:
        print("\nERROR:", file=sys.stderr)
        print("Point format seems to be wrong (should be x/y)", file=sys.stderr)
        return False

    return [x, y]


#%%
def read_range(range_str, width, length):
    if re.match('[0-9]*:[0-9]*/[0-9]*:[0-9]', range_str):
        x1, x2, y1, y2 = [int(s) for s in re.split('[:/]', range_str)]
        if x2 == 0:
            x2 = width
        if y2 == 0:
            y2 = length
        if x1 > width-1 or x2 > width or y1 > length-1 or y2 > length:
            print("\nERROR:", file=sys.stderr)
            print("Index exceed input dimension ({0},{1})!".format(width,length), file=sys.stderr)
            return False
        if x1 >= x2 or y1 >= y2:
            print("\nERROR: x2/y2 must be larger than x1/y1", file=sys.stderr)
            return False
    else:
        print("\nERROR:", file=sys.stderr)
        print("Range format seems to be wrong (should be x1:x2/y1:y2)", file=sys.stderr)
        return False

    return [x1, x2, y1, y2]


#%%
def read_range_line(range_str, width, length):
    if re.match('[0-9]*,[0-9]*/[0-9]*,[0-9]', range_str):
        x1, y1, x2, y2 = [int(s) for s in re.split('[,/]', range_str)]
        if x1 > width-1 or x2 > width-1 or y1 > length-1 or y2 > length-1:
            print("\nERROR:", file=sys.stderr)
            print("Index exceed input dimension ({0},{1})!".format(width ,length), file=sys.stderr)
            return False
    else:
        print("\nERROR:", file=sys.stderr)
        print("Range format seems to be wrong (must be x1,y1/x2,y2)", file=sys.stderr)
        return False

    return [x1, x2, y1, y2]



#%%
def read_range_geo(range_str, width, length, lat1, postlat, lon1, postlon):
    """
    lat1 is north edge and postlat is negative value.
    lat lon values are in grid registration
    Note: x1/y1 range 0 to width-1, while x2/y2 range 1 to width
    """
    lat2 = lat1+postlat*(length-1)
    lon2 = lon1+postlon*(width-1)

    if re.match('[+-]?\d+(?:\.\d+)?/[+-]?\d+(?:\.\d+)?/[+-]?\d+(?:\.\d+)?/[+-]?\d+(?:\.\d+)?', range_str):
        lon_w, lon_e, lat_s, lat_n = [float(s) for s in range_str.split('/')]
        x1 = int(np.round((lon_w - lon1)/postlon)) if lon_w > lon1 else 0
        x2 = int(np.round((lon_e - lon1)/postlon))+1 if lon_e < lon2 else width
        y1 = int(np.round((lat_n - lat1)/postlat)) if lat_n < lat1 else 0
        y2 = int(np.round((lat_s - lat1)/postlat))+1 if lat_s > lat2 else length
    else:
        print("\nERROR:", file=sys.stderr)
        print("Range format seems to be wrong (should be lon1/lon2/lat1/lat2)", file=sys.stderr)
        return False

    return [x1, x2, y1, y2]


#%%
def poly_mask(poly_str, lon, lat, radius=0):
    """
    lat lon values are in grid registration
    poly coords in long lat
    radius = 0 for input polygons
    radius > 0 for lines (search width in pixels for containing points)
    """

    # read coord string and split into numpy arrays
    coord_str = [float(s) for s in re.split('[,]', poly_str)]
    lon_poly, lat_poly = np.asarray(coord_str[::2]), np.asarray(coord_str[1::2])
    if radius > 0:
        lon_poly = np.concatenate([lon_poly, np.flip(lon_poly)])
        lat_poly = np.concatenate([lat_poly, np.flip(lat_poly)])
        pix = np.sqrt((lon[1] - lon[0]) ** 2 + (lat[1] - lat[0]) ** 2)
        radius = pix * radius

    # generate coordinate mesh
    lon_grid, lat_grid = np.meshgrid(lon, lat)

    # create poly from coords and return points within polygon
    poly = path.Path(np.vstack((lon_poly, lat_poly)).T)
    poly_mask = poly.contains_points(np.transpose([lon_grid.flatten(), lat_grid.flatten()]), radius=radius).reshape(np.shape(lon_grid))

    return poly_mask

#%%
def read_range_line_geo(range_str, width, length, lat_n, postlat, lon_w, postlon):
    """
    lat_n is north edge and postlat is negative value.
    lat lon values are in grid registration
    """

    if re.match('[+-]?\d+(?:\.\d+)?,[+-]?\d+(?:\.\d+)?/[+-]?\d+(?:\.\d+)?,[+-]?\d+(?:\.\d+)?', range_str):
        lon1, lat1, lon2, lat2 = [float(s) for s in re.split('[,/]', range_str)]
        x1 = int(np.round((lon1 - lon_w)/postlon))
        x2 = int(np.round((lon2 - lon_w)/postlon))
        y1 = int(np.round((lat1 - lat_n)/postlat))
        y2 = int(np.round((lat2 - lat_n)/postlat))
    else:
        print("\nERROR:", file=sys.stderr)
        print("Range format seems to be wrong (should be lon1,lat1/lon2,lat2)", file=sys.stderr)
        return False

    return [x1, x2, y1, y2]


#%%
def xy2bl(x, y, lat1, dlat, lon1, dlon):
    """
    xy index starts from 0, end with width/length-1
    """
    lat = lat1+dlat*y
    lon = lon1+dlon*x

    return lat, lon

#%%
def get_earthquake_dates(cumfile, minmag = 6.5, maxdepth=60):
    ''' ML, 20241022
    Will return dates of earthquakes in the region covered by the cum file.
    minmag, maxdepth = minimal magnitude and maximum depth [km] of the events to get the dates for.
    '''
    cumh5 = h5.File(cumfile, 'r')
    imdates = cumh5['imdates'][()].astype(str).tolist()
    cum = cumh5['cum']
    sizet, sizex, sizey = cum.shape
    lon1 = cumh5['corner_lon'][()]
    lon2 = lon1 + cumh5['post_lon'][()] * sizex
    lat1 = cumh5['corner_lat'][()]
    lat2 = lat1 + cumh5['post_lat'][()] * sizey

    # real datetime this time
    imdates_dt = ([dt.datetime.strptime(imd, '%Y%m%d') for imd in imdates])

    def _get_frametime(frame):
        ''' attempt to get frame time for better precision'''
        try:
            track = str(int(frame[:3]))
        except:
            return False
        web_path = 'https://gws-access.jasmin.ac.uk/public/nceo_geohazards/LiCSAR_products'
        fullwebpath_metadata = os.path.join(web_path, track, frame, 'metadata', 'metadata.txt')
        try:
            a = pd.read_csv(fullwebpath_metadata, sep='=', header=None)
            center_time = a[a[0] == 'center_time'][1].values[0]
            center_time_dt = dt.datetime.strptime(center_time, '%H:%M:%S.%f').time()
        except:
            return False
        return center_time_dt

    frame = os.path.realpath(cumfile).split('/')[-3]
    print('based on directory, assuming LiCSAR frame '+frame)
    print('(used only to get center_time)')
    center_time_dt = _get_frametime(frame)
    if not center_time_dt:
        print('Error getting center_time for this frame - events with the same day as acquisitions might be wrongly mapped as pre/post event.')

    datein = imdates_dt[0]
    dateout = imdates_dt[-1]
    events = search(starttime=datein + dt.timedelta(days=1),
                    endtime=dateout - dt.timedelta(days=1),
                    minmagnitude=minmag, limit=2000, maxdepth=maxdepth,
                    maxlongitude=max(lon1, lon2),
                    maxlatitude=max(lat1, lat2),
                    minlatitude=min(lat1, lat2),
                    minlongitude=min(lon1, lon2))
    offsetdates = []
    print('Setting offset dates')  # TODO - better to set the offsets at the centre time between the epochs
    for e in events:
        offdate = e.time.date()
        if center_time_dt:
            if e.time.strftime('%Y%m%d') in imdates:
                if e.time.time() < center_time_dt:
                    #print('checking the event time, an event will be set towards previous epoch')
                    offdate = offdate - dt.timedelta(days=1)
                else:
                    offdate = offdate + dt.timedelta(days=1)
        offsetdates.append(offdate)

    offsetdates = list(set(offsetdates))
    offsetdates.sort()
    return offsetdates