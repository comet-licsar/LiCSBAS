#!/usr/bin/env python3
"""
========
Overview
========
Python3 library of extra functions for LiCSBAS.

=========
Changelog
=========
20241130 Milan Lazecky, Uni of Leeds
 - Original implementation

"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.image as mpimg
import pygmt
from pygmt.clib import Session
from pygmt.helpers import GMTTempFile

try:
    import contextily as ctx
except:
    print('contextily is not installed')


def plot_ts_simple(cube, lon, lat, label = 'test', dvarname = 'cum', miny=None, maxy=None):
    ''' returns a simple pygmt figure of time series of xr datacube at given lon, lat coord '''
    time = cube.time.values
    mindate = pd.Timestamp(cube.time.min().values).to_pydatetime().date()
    maxdate = pd.Timestamp(cube.time.max().values).to_pydatetime().date()
    cum_point = cube[dvarname].sel(lon=lon, lat=lat, method='nearest')
    if type(miny)==type(None):
        if dvarname.find('coh') > -1:
            miny, maxy = 0, 1
        else:
            miny = float(cum_point.min())
            maxy = float(cum_point.max())
    #
    fig = pygmt.Figure()
    pygmt.config(FONT_LABEL="10p")
    #
    with pygmt.config(FONT_TITLE="12p"):
        fig.plot(
            projection="X9c/7c",
            region=[mindate, maxdate, miny, maxy],
            # frame=["+t time series (%.3f, %.3f)" % (lon, lat),\
            frame=["xa1Yfg1Y", "yafg+l" + label, "+t%.3f, %.3f" % (lon, lat)],
            # "xa1Yfg1Y", "ya10f5+ldisplacement [mm]"],
            x=time,
            y=cum_point,
            style="c0.1c",
            fill="black"
        )
    fig.basemap(frame=True)
    return fig


def licsbas_pygmt_plot(cube, title = 'vel', vminmax = [-15, 15],
                       toplot = 'vel', volcid = None):
    ''' plots licsbas result in netcdf, loaded to xr.Dataset (cube).
    if volcano ID is set, it will add its symbol to the plot.
    '''
    import geopandas as gpd
    from shapely.geometry import Point
    refpoint = Point((cube.ref_lon, cube.ref_lat))
    refpoint = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[refpoint])
    #print('Plotting velocity layer on DEM')
    grid = cube[toplot]
    if maskit:
        grid = grid.where(cube.mask == 1)
    if volcid:
        import volcdb as v
        vid = v.get_volclip_vids(volcid)[0]
        vgpd = v.get_volclips_gpd(vid)
        # vgpd.geom.bounds
        minlon = float(vgpd.geom.bounds.minx)
        minlat = float(vgpd.geom.bounds.miny)
        maxlon = float(vgpd.geom.bounds.maxx)
        maxlat = float(vgpd.geom.bounds.maxy)
        grid = grid.sel(lon=slice(minlon, maxlon), lat=slice(minlat, maxlat))
    #grid = grid.load()
    gridgmt = pygmt_plot(grid, title, 'mm/year', vminmax)
    gridgmt.plot(data=refpoint, pen="4p,magenta4")
    if volcid:
        volctb = v.get_volc_info(volcid)
        gridgmt.plot(data=volctb.geom, style="t8p", pen="0.5p,black", fill="red")


def pygmt_plot(grid, title, label='deformation rate [mm/year]', lims=[-25, 10],
               cmap="roma", photobg=False, plotvec=None, interactive=False,
               region=None):
    ''' Function to generate (nice) plot of given grid using pyGMT

    Args:
        grid (xr.DataArray): input grid to plot
        title (str):  title (note too long title will disbalance the figure)
        label (str):  label below the colour scale
        lims (list):  colour scale limits (if None, it will do min max minus 2std)
        cmap (str):   colour scale map (try 'vik' for E-W)
        photobg (bool): will plot orthophotomap as the background (if False, DEM relief is used)
        plotvec (geopandas etc): will plot vector data to the map, using pyGMT defaults
        region (tuple/None):  either None or set using tuple (minlon, maxlon, minlat, maxlat)

    Returns:
        pygmt.figure.Figure
    '''
    try:
        grid = grid.load()
    except:
        print('error loading the input dataarray to memory')
        return False
    # try cmap 'vik' for E-W
    #
    # grid = a['U'].where(a.mask < 5) - 10
    # topo_data = '@earth_relief_03s' #3 arc second global relief (SRTM3S)
    topo_data = '@earth_relief_01s'  # 3 arc second global relief (SRTM3S)
    if not region:
        minlon, maxlon = float(np.min(grid.lon)), float(np.max(grid.lon))
        minlat, maxlat = float(np.min(grid.lat)), float(np.max(grid.lat))
    else:
        minlon, maxlon, minlat, maxlat = region
    grid = grid.where(grid != 0)
    if not lims:
        tmean = float(grid.mean())
        tstd = float(grid.std())
        stdscale = 2
        lims = [tmean - stdscale * tstd, tmean + stdscale * tstd]
    fig = pygmt.Figure()
    pygmt.config(FORMAT_GEO_MAP="ddd.xx")  # , MAP_FRAME_TYPE="plain")
    projection = "M13c"  # 'R13c' for Robinson etc.
    region = [minlon, maxlon, minlat, maxlat]
    if interactive:
        xshift = '1.5c'
        yshift = '2.5c'
        fig.shift_origin(xshift=xshift, yshift=yshift)
    fig.basemap(region=region, projection=projection, frame=["af", '+t{0}'.format(title)])
    if photobg:
        import contextily as ctx
        sourcetiles = ctx.providers.Esri.WorldImagery
        fig.tilemap(
            region=region, projection=projection,
            # region=[-157.84, -157.8, 21.255, 21.285],
            # projection="M12c",
            # Set level of details (0-22)
            # Higher levels mean a zoom level closer to the Earth's
            # surface with more tiles covering a smaller
            # geographic area and thus more details and vice versa
            # Please note, not all zoom levels are always available
            zoom=14,
            # Use tiles from OpenStreetMap tile server
            source=sourcetiles
        )
        pygmt.makecpt(cmap=cmap, series=lims, background=True)
        fig.grdview(grid=grid, cmap=True, projection=projection, surftype='c', transparency=40)
    else:
        pygmt.makecpt(cmap="gray", series=[-8000, 8000, 1000], continuous=True)
        fig.grdimage(
            grid=topo_data,
            cmap=True,
            region=[minlon, maxlon, minlat, maxlat],
            projection=projection,
            shading=True,
            frame=True
        )
        pygmt.makecpt(cmap=cmap, series=lims, background=True)
        fig.grdimage(grid=grid, cmap=True, projection=projection, frame=True, transparency=40)
    #
    fig.coast(shorelines=True, projection=projection)
    if type(plotvec) != type(None):
        fig.plot(plotvec, projection=projection, region=region)
    fig.colorbar(frame='a10+l{}'.format(label))
    # fig.show()
    if interactive:
        return fig, region, projection, xshift, yshift
    else:
        return fig


def get_region(cube):
    '''extracts pyGMT-compliant region from given xr dataset/dataarray'''
    if 'longitude' in cube:
        x='longitude'
        y='latitude'
    elif 'lon' in cube:
        x='lon'
        y='lat'
    elif 'x' in cube:
        x='x'
        y='y'
    else:
        print('no proper dimension')
        return False
    a=cube
    llcrnrlon=float(a[x].min().values) # lower left corner longitude
    llcrnrlat=float(a[y].min().values) # lower left corner latitude
    urcrnrlon=float(a[x].max().values) # upper right corner longitude
    urcrnrlat=float(a[y].max().values) # upper right corner latitude
    region=[llcrnrlon, urcrnrlon, llcrnrlat, urcrnrlat]
    return region


def generate_vel_preview(nc, lims = [-100,100], title = 'vel_msk', volcid = None, outpng = None):
    import geopandas as gpd
    import xarray as xr
    import volcdb as v
    from shapely.geometry import Point
    import framecare as fc
    #
    cube = xr.open_dataset(nc)
    refpoint = Point((cube.ref_lon, cube.ref_lat))
    refpoint = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[refpoint])
    #
    print('Plotting velocity layer on DEM')
    grid = cube.vel.where(cube.mask==1)
    if volcid:
        lbstr = v.get_licsbas_clipstring_volcano(volcid) # size as in volc portal
        minlon, maxlon, minlat, maxlat = [ float(s) for s in lbstr.split('/') ]
        grid = grid.sel(lon=slice(minlon,maxlon), lat=slice(minlat,maxlat)).load()
        volctb = v.get_volc_info(volcid)
        #title = str(volctb.name.values[0])
        poly = fc.lonlat_to_poly(minlon, maxlon, minlat, maxlat)
        allvolcsinpoly = v.get_volcanoes_in_polygon(poly, volcs=None)
    #
    gridgmt = pygmt_plot(grid, title, 'mm/year', lims, 'vik', region = (minlon, maxlon, minlat, maxlat))
    gridgmt.plot(data=refpoint, pen="4p,magenta4")
    if volcid:
        gridgmt.plot(data=allvolcsinpoly.geom, style="t6p", pen="0.5p,black", fill="blue")
        gridgmt.plot(data=volctb.geom, style="t8p", pen="0.5p,black", fill="red")
    if outpng:
        gridgmt.savefig(outpng, dpi=120)
    return gridgmt


def pygmt_plot_interactive(cube, title, label='deformation rate [mm/year]', lims=[-15, 50],
                           cmap="polar", photobg=False, plotvec=None):
    ''' This will start a simple interactive viewer in jupyter ntb.
    Note you need ipympl installed and the matplotlib widget must be set here.

    The author is Rochelle Pun, an outstanding student that was selected in highly competitive
    COMET Summer MSc Internship 2024 - and she did magnificent job interactivizing pygmt.
    Her original tool resides here: https://github.com/chelle0425/IntPyGMT

    We only modified this for CIW 2024 tutorial purposes on LiCSBAS'''
    # print("%matplotlib widget")
    # first of all generate the left plot:
    tempng = '/tmp/pygmt_pi.png'
    grid = cube['vel']
    fig, region, projection, xshift, yshift = pygmt_plot(grid, title, label, lims,
                                                         cmap, photobg, plotvec, interactive=True)
    try:
        fig.plot(x=float(cube.ref_lon), y=float(cube.ref_lat), pen="4p,magenta4")
    except:
        print('error adding ref point')
    #
    fig.savefig(tempng)
    #
    png_path = tempng
    spam_path = tempng + "ts.png"
    #
    #time_ds = cube["time"].values
    ddpi = 150
    #
    if isinstance(region, str):
        region_str = region
    elif isinstance(region, list):
        region_str = f"{region[0]}/{region[1]}/{region[2]}/{region[3]}"
    #
    def unpack_xyshift(str):
        if str[-1].isalpha():
            shift_value = str[:-1]
            shift_unit = str[-1]
        else:
            raise Exception("invalid xshift or yshift input")
        return float(shift_value), shift_unit
    #
    xshift_value, xshift_unit = unpack_xyshift(xshift)
    yshift_value, yshift_unit = unpack_xyshift(yshift)
    #
    # we are working in cm
    if xshift_unit == "c":
        xshift_value = xshift_value
    elif xshift_unit == "i":
        xshift_value = xshift_value * 2.54
    elif xshift_unit == "p":
        xshift_value = (xshift_value * 72) * 2.54
    else:
        raise Exception("invalid xshift input (must be either c, i or p)")
    #
    # similarly for y
    if yshift_unit == "c":
        yshift_value = yshift_value
    elif yshift_unit == "i":
        yshift_value = yshift_value * 2.54
    elif yshift_unit == "p":
        yshift_value = (yshift_value * 72) * 2.54
    else:
        raise Exception("invalid yshift input (must be either c, i or p)")
    #
    #    # determine image dimension
    img = Image.open(png_path)
    width, height = img.size  # canvas (width,height) tuple in pixels
    DPI_horz, DPI_vert = img.info.get('dpi')
    #
    #time = pd.to_datetime(time_ds)
    #
    #cum = cube["cum"]
    # ymin = float(cube.cum.mean() - 3*cube.cum.std())
    # ymax = float(cube.cum.mean() + 3*cube.cum.std())
    ymin = float(cube.cum.min())
    ymax = float(cube.cum.max())
    #
    def pos_to_lonlat(x, y):
        # xyshift input in cm
        x = (x / DPI_horz) * 2.54  # convert pixel to cm
        x = x - xshift_value
        y = (y / DPI_vert) * 2.54  # cm
        height_cm = (height / DPI_vert) * 2.54
        y = height_cm - y - yshift_value
        x = [x]  # must be list with one value or np array
        y = [y]
        ### lon lat conversion using mapproject ###
        with Session() as ses:
            with ses.virtualfile_from_vectors(x, y) as fin:
                args = [f'{fin}', f'-R{region_str}', f'-J{projection}', '-I', '-S']
                with GMTTempFile() as fout:
                    ses.call_module(module="mapproject", args=' '.join(args) + " ->" + fout.name)
                    out = fout.read().strip()
        lon, lat = [float(i) for i in out.split(' ')]
        return lon, lat
    #
    def onclick(event):
        # pos.append([event.xdata, event.ydata])
        lon, lat = pos_to_lonlat(event.xdata,
                                 event.ydata)  # pos[-1][0], pos[-1][1]) # pos[-1] represents last click (list with x, y)
        # lonlat.append([lon, lat]) # converts x y to lon lat and appends
        # code below shows how gmt_png can be modified for an interactive time series plot
        # alternatively retrive lon lat using coords_from_figure(ax1)
        # ax1.set_title(f'Click {len(pos)}: {lon}, {lat}')
        fig = plot_ts_simple(cube, lon, lat, label='defo towards sat [mm]', dvarname='cum', miny=ymin, maxy=ymax)
        fig.savefig(spam_path, dpi=ddpi)
        img = mpimg.imread(spam_path)
        ax2.imshow(img, origin='upper')
    #
    # fig = plt.figure(figsize=(12, 5))
    fig = plt.figure(figsize=(10, 5))
    ax1 = fig.add_subplot(121)
    img = mpimg.imread(png_path)
    ax1.imshow(img, origin='upper')
    ax1.axis('off')
    # ax1.set_title(frame+" vel.filt (mm/yr)")
    ax2 = fig.add_subplot(122)
    ax2.axis('off')
    plt.tight_layout()
    #
    label = 'defo towards sat [mm]'
    ffig = plot_ts_simple(cube, float(cube.lon.mean()), float(cube.lat.mean()), label=label, dvarname='cum', miny=ymin,
                          maxy=ymax)
    ffig.savefig(spam_path, dpi=ddpi)
    img = mpimg.imread(spam_path)
    ax2.imshow(img, origin='upper')
    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    return ax1