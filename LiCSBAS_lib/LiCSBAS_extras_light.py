#!/usr/bin/env python3
"""
Lightweight, binder-friendly interactive LiCSBAS result viewer (NO pygmt / NO GMT core).

Why this file exists
--------------------
`LiCSBAS_extras.py` provides `pygmt_plot_interactive`, a great "click the map ->
time-series" tutorial widget. Unfortunately it depends on the *core GMT* binaries
bundled with pygmt, which is not available (or only a limited build) in MyBinder.
It worked fine in Google Colab (where GMT can be built on-the-fly) but not in Binder.

This module provides a drop-in, dependency-light replacement that uses ONLY:
    matplotlib + ipympl  (for interactivity)
    numpy / pandas / xarray
No pygmt, no GMT, no native libraries -> runs in MyBinder and Colab alike.

Usage (same call as the original, just a different import):

    from LiCSBAS_extras_light import pylight_plot_interactive
    pylight_plot_interactive(cube, title, label, lims, cmap,
                             photobg=False, plotvec=None)

`cube` is an xarray Dataset opened from a LiCSBAS NetCDF, with vars
`vel`, `cum`, `mask` and coords `lon`, `lat`, `time` (plus optional scalars
`ref_lon`, `ref_lat`).

The left panel is a pcolormesh of the field (default `vel`) in lon/lat, the right
panel is the `cum` time series at the clicked point. Click the map to update it.

Credit for the original interactive concept:
Rochelle Pun, COMET Summer MSc Internship 2024 (https://github.com/chelle0425/IntPyGMT).
This lightweight port: Milan Lazecky, Uni of Leeds (2025).
"""
import warnings

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd  # noqa: F401  (kept for API symmetry with the pygmt version)

# Try to make the cmcrameri colormaps (e.g. 'polar', 'vik', 'roma') available to
# matplotlib. cmcrameri self-registers into matplotlib on import; if it is not
# installed we simply fall back to a built-in colormap below.
try:
    import cmcrameri  # noqa: F401
except Exception:
    pass


def _get_cmap(name, fallback='coolwarm'):
    """Resolve a colormap by name, falling back gracefully."""
    try:
        return plt.get_cmap(name)
    except Exception:
        try:
            return plt.get_cmap(fallback)
        except Exception:
            return matplotlib.colormaps['viridis']


def _nearest(arr, value):
    """Integer index of the element of `arr` nearest to `value`."""
    return int(np.argmin(np.abs(np.asarray(arr, dtype=float) - value)))


def _squeeze_time(da):
    """If a DataArray still has a 'time' dimension, return the last snapshot."""
    if 'time' in da.dims:
        return da.isel(time=-1)
    return da


def _refval(cube, name):
    """Safely pull a scalar coordinate/attribute like ref_lon out of a cube."""
    for src in (lambda: cube[name], lambda: cube.attrs.get(name)):
        try:
            v = np.asarray(src(), dtype=float).ravel()
            if v.size:
                return float(v[0])
        except Exception:
            continue
    return None


def _time_series_at(cube, lon, lat, dvarname='cum'):
    """Return (time_values, data_values) for the grid point nearest (lon, lat)."""
    da = cube[dvarname]
    i = _nearest(cube.lat, lat)
    j = _nearest(cube.lon, lon)
    s = da.isel(lat=i, lon=j)
    y = np.asarray(s.values, dtype=float).ravel()
    t = np.asarray(cube['time'].values)
    return t, y


# ==============================================================================
# Optional basemap backgrounds (all optional, all fail-soft so the viewer never
# crashes when a dependency or the network is unavailable, e.g. in offline Binder).
# ==============================================================================
def _dem_array(cube, dem_file=None):
    """Best effort: find a 2-D elevation grid in the cube, or at `dem_file`.

    Returns an xarray.DataArray (or None). The caller checks that its shape
    matches the cube's (lat, lon) grid before using it.
    """
    if dem_file:
        try:
            import rioxarray
            return rioxarray.open_rasterio(dem_file).squeeze()  # needs rioxarray installed
        except Exception:
            return None
    if cube is not None:
        for name in ('dem', 'topo', 'topography', 'elevation', 'height', 'altitude', 'h', 'dem_h'):
            if name in cube:
                try:
                    da = cube[name]
                    if 'time' in da.dims:
                        da = da.isel(time=0)
                    return da
                except Exception:
                    continue
    return None


def _hillshade(dem, lat, lon, zscale=1.0, sun_elev=35.0, sun_az=315.0):
    """Compute a simple hillshade relief (array 0..255) from a 2-D DEM.

    `dem` is expected to be aligned to `lat` (rows) x `lon` (columns).
    Pure numpy -- no native dependencies.
    """
    dem = np.asarray(dem, dtype=float)
    if dem.ndim != 2:
        return None
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    if lat.size < 2 or lon.size < 2:
        return None
    meanlat = float(np.mean(lat))
    dy = float(np.mean(np.abs(np.diff(lat)))) * 110574.0                     # m/pixel (N-S)
    dx = float(np.mean(np.abs(np.diff(lon)))) * 111320.0 * np.cos(np.radians(meanlat))  # m/pixel (E-W)
    if dx <= 0 or dy <= 0 or not (np.isfinite(dx) and np.isfinite(dy)):
        return None
    dzdn = np.gradient(dem, axis=0) / dy * zscale     # slope N-S
    dzde = np.gradient(dem, axis=1) / dx * zscale     # slope E-W
    elev = np.radians(90.0 - sun_elev)
    azim = np.radians(sun_az)
    slope = np.arctan(np.hypot(dzdn, dzde))
    aspect = np.arctan2(-dzdn, dzde)
    shade = np.cos(elev) * np.cos(slope) + np.sin(elev) * np.sin(slope) * np.cos(azim - aspect)
    return np.clip(shade * 255.0, 0, 255)


def _render_background(ax1, lon, lat, nlat, nlon, photobg=False, dem_hillshade=True,
                       cube=None, dem_file=None):
    """Paint a basemap background *under* the data field; returns True if one was drawn.

    Priority:
      photobg            -> satellite imagery   (contextily / Esri WorldImagery)
      else dem_hillshade -> (a) real DEM hillshade if a matching DEM grid is available
                            (b) else contextily shaded-terrain tiles (Esri WorldTopoMap / OpenTopoMap)
    Every branch is wrapped in try/except: on any failure it falls through and returns
    False (plain background) so the viewer still works offline / without contextily.
    """
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)

    def _set_extent():
        ax1.set_xlim(lon.min(), lon.max())
        ax1.set_ylim(lat.min(), lat.max())

    def _ctx_basemap(src):
        import contextily as ctx
        _set_extent()
        ctx.basemap(ax1, source=src, zoom='auto')
        _set_extent()
        return True

    # ---- (1) satellite photobackground --------------------------------------
    if photobg:
        try:
            import contextily as ctx
            return _ctx_basemap(ctx.providers.Esri.WorldImagery)
        except Exception as e:
            print("photobg skipped (contextily or network unavailable):", type(e).__name__)
            _set_extent()
            return False

    # ---- (2) DEM hillshade (default background) -----------------------------
    if dem_hillshade:
        # (a) prefer a real DEM grid -> computed hillshade (crisp, no network)
        dem = _dem_array(cube, dem_file)
        if dem is not None:
            try:
                if 'time' in getattr(dem, 'dims', ()):
                    dem = dem.isel(time=0)
                d2 = np.asarray(dem.values, dtype=float)
                if d2.shape == (nlat, nlon):
                    hs = _hillshade(d2, lat, lon)
                    if hs is not None:
                        ax1.pcolormesh(lon, lat, hs[:nlat - 1, :nlon - 1], shading='flat',
                                      cmap='gray', vmin=0, vmax=255)
                        _set_extent()
                        return True
            except Exception as e:
                print("local DEM hillshade failed:", type(e).__name__)
        # (b) fallback: contextily shaded-terrain tiles (needs a browser / internet)
        try:
            import contextily as ctx
            candidates = []
            if hasattr(ctx.providers.Esri, 'WorldTopoMap'):
                candidates.append(ctx.providers.Esri.WorldTopoMap)
            if hasattr(ctx.providers, 'OpenTopoMap'):
                candidates.append(ctx.providers.OpenTopoMap)
            for src in candidates:
                try:
                    return _ctx_basemap(src)
                except Exception:
                    continue
            print("DEM hillshade: no usable contextily tile source")
        except Exception as e:
            print("DEM hillshade skipped (contextily unavailable):", type(e).__name__)
        _set_extent()
        return False

    return False


def _plot_geodataframe(ax1, gdf, color='#d62728', ms=10, lw=1.6, zorder=8):
    """Plot Point / LineString / (Multi)Polygon geometries from a GeoDataFrame.

    Assumes the geometries share the cube's geographic (EPSG:4326 lon/lat) frame.
    Operates on shapely geometries directly, so it works with or without geopandas
    installed (only `gdf.geometry` iteration is required).
    """
    try:
        geoms = list(gdf.geometry)
    except Exception:
        try:
            geoms = list(gdf['geometry'])
        except Exception:
            print("plotvec: could not find a 'geometry' column; skipped")
            return
    def _ring(obj, close):
        """Plot the (x, y) coordinates of a shapely line/polygon ring (shapely-1 & 2 safe)."""
        try:
            pts = np.asarray(list(obj.coords), dtype=float)
        except Exception:
            pts = np.asarray(list(obj), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 1 or pts.shape[1] < 2:
            return
        xs, ys = pts[:, 0], pts[:, 1]
        if close:
            xs = np.append(xs, xs[0])
            ys = np.append(ys, ys[0])
        ax1.plot(xs, ys, color=color, lw=lw, zorder=zorder)

    for g in geoms:
        try:
            gtype = str(getattr(g, 'geom_type', '')).lower()
            if 'point' in gtype:
                ax1.plot([g.x], [g.y], marker='^', ms=ms, color=color, zorder=zorder)
            elif 'polygon' in gtype:
                parts = list(getattr(g, 'geoms', [])) or [g]
                for p in parts:
                    _ring(p.exterior, close=True)
            elif 'line' in gtype:
                parts = list(getattr(g, 'geoms', [])) or [g]
                for ln in parts:
                    _ring(ln, close=False)
            elif hasattr(g, 'exterior') and hasattr(g.exterior, 'coords'):
                _ring(g.exterior, close=True)
            elif hasattr(g, 'coords'):
                _ring(g, close=False)
        except Exception as e:
            print("  plotvec: skipped one geometry (%s): %s" % (gtype or type(g).__name__, e))


def plot_ts_light(cube, lon, lat, label='defo towards sat [mm]', dvarname='cum',
                  miny=None, maxy=None, title=None):
    """A *light* (pure-matplotlib) single time-series plot — no pygmt.

    Mirrors the role of `plot_ts_simple` in LiCSBAS_extras.py but returns a
    matplotlib Figure so it can be embedded in the interactive widget or used
    standalone.
    """
    t, y = _time_series_at(cube, lon, lat, dvarname=dvarname)
    if miny is None or maxy is None:
        if 'coh' in dvarname:
            miny, maxy = (0, 1) if (miny is None and maxy is None) else (miny, maxy)
        else:
            finite = y[np.isfinite(y)]
            if finite.size == 0:
                miny, maxy = -1, 1
            else:
                if miny is None:
                    miny = float(finite.min())
                if maxy is None:
                    maxy = float(finite.max())
    if miny == maxy:
        miny, maxy = miny - 1, maxy + 1
    if title is None:
        title = '%.3f, %.3f' % (lon, lat)
    fig, ax = plt.subplots(figsize=(5, 3.4))
    ax.plot(t, y, color='#1f4e79', lw=1.4, zorder=3)
    ax.set_title(title, fontsize=11)
    ax.set_ylabel(label, fontsize=10)
    ax.set_ylim(miny, maxy)
    ax.grid(True, which='major', alpha=0.3)
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    return fig


def pylight_plot_interactive(
        cube, title='vel', label='deformation rate [mm/year]',
        lims=[-15, 50], cmap='polar', photobg=False, plotvec=None,
        yrange=None, dvar='vel', dts='cum', dem_hillshade=True, dem_file=None):
    """Lightweight, pygmt-free interactive viewer (drop-in for pygmt_plot_interactive).

    Args:
        cube  : xarray Dataset with vel/cum/mask and lon/lat/time coords.
        title : title shown on the map panel.
        label : colorbar / y-axis label.
        lims  : [vmin, vmax] colour-scale limits.
        cmap  : colormap name (cmcrameri names like 'polar' work if installed).
        photobg : if True, show a satellite basemap (contextily / Esri WorldImagery)
                  beneath the field. Requires contextily + a browser with internet.
        plotvec : None, or a geopandas GeoDataFrame (EPSG:4326) to draw over the field
                  (volcano points, clip polygons, line profiles, ...).
        yrange  : optional [min,max] for the time-series y-axis, e.g. [-50, 50].
        dvar    : DataArray name to show in the map panel (default 'vel').
        dts     : DataArray name to show in the time-series panel (default 'cum').
        dem_hillshade : if True (default), show a shaded-relief DEM background
                        beneath the field. Uses a matching DEM grid from `cube`/`dem_file`
                        if present, else contextily shaded-terrain tiles. Falls back to a
                        plain background silently when nothing is available (e.g. offline).
        dem_file  : optional path to a GeoTIFF/nc DEM to hillshade when the cube has none.

    Returns:
        the interactive map Axes (ax1).
    """
    # ---- data ---------------------------------------------------------------
    lon = np.asarray(cube.lon, dtype=float)
    lat = np.asarray(cube.lat, dtype=float)

    grid = cube[dvar]
    grid = _squeeze_time(grid)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        if 'mask' in cube:
            grid = grid.where(cube['mask'] == 1, other=np.nan)
        grid = grid.where(grid != 0, other=np.nan)
    v = np.asarray(grid.values, dtype=float)
    nlat, nlon = lat.size, lon.size

    vmin, vmax = (float(lims[0]), float(lims[1])) if lims else (float(np.nanmin(v)), float(np.nanmax(v)))
    cmapobj = _get_cmap(cmap)

    if yrange:
        ts_min, ts_max = float(yrange[0]), float(yrange[1])
    else:
        # per-point limits are computed in render_ts from each series
        ts_min = ts_max = None

    # ---- figure -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.2),
                                   gridspec_kw={'width_ratios': [1.35, 1.0]})

    # ---- optional basemap background, painted *under* the field -------------
    has_bg = _render_background(ax1, lon, lat, nlat, nlon,
                                photobg=photobg, dem_hillshade=dem_hillshade,
                                cube=cube, dem_file=dem_file)

    # ---- the field (translucent when a background is present) ---------------
    # NOTE: pcolormesh expects C shape (len(lat)-1, len(lon)-1) with 1-D x,y.
    c2d = v[:nlat - 1, :nlon - 1]
    pc = ax1.pcolormesh(lon, lat, c2d, shading='flat', cmap=cmapobj,
                        vmin=vmin, vmax=vmax, alpha=(0.62 if has_bg else 1.0))
    ax1.set_title(title, fontsize=12)
    ax1.set_xlabel('longitude', fontsize=9)
    ax1.set_ylabel('latitude', fontsize=9)
    ax1.set_xlim(lon.min(), lon.max())
    ax1.set_ylim(lat.min(), lat.max())
    # Approximate geographic aspect (cosine-latitude correction) so shapes don't
    # stretch; near the equator this is ~1.
    ax1.set_aspect(1.0 / max(np.cos(np.radians(np.mean(lat))), 1e-3),
                   adjustable='box')

    cb = fig.colorbar(pc, ax=ax1, pad=0.02)
    cb.set_label(label, fontsize=10)

    # vector overlay (volcanoes, clip boundaries, profile lines, ...)
    if plotvec is not None:
        _plot_geodataframe(ax1, plotvec)

    # reference point (magenta cross), if the cube provides one
    rlon = _refval(cube, 'ref_lon')
    rlat = _refval(cube, 'ref_lat')
    if rlon is not None and rlat is not None:
        ax1.plot(rlon, rlat, marker='+', ms=14, mew=2.2, color='magenta',
                 zorder=9, label='ref.')
    # marker for the last clicked point
    click, = ax1.plot([], [], marker='x', ms=12, mew=2.4, color='red', zorder=10)

    # ---- time-series panel --------------------------------------------------
    def render_ts(lonc, latc):
        ax2.clear()
        t, y = _time_series_at(cube, lonc, latc, dvarname=dts)
        finite = y[np.isfinite(y)]
        if ts_min is None and ts_max is None and finite.size:
            lo, hi = float(finite.min()), float(finite.max())
            pad = 0.08 * (hi - lo) + 1e-9
            lo, hi = lo - pad, hi + pad
        else:
            lo, hi = ts_min, ts_max
            if lo is None and hi is None:
                lo, hi = (-1, 1) if finite.size == 0 else (float(finite.min()), float(finite.max()))
        ax2.plot(t, y, color='#1f4e79', lw=1.4, zorder=3)
        ax2.set_title('%.3f, %.3f' % (lonc, latc), fontsize=11)
        if 'unit' in cube[dts].attrs.keys():
            ylabel = cube[dts].attrs['unit']
        else:
            ylabel = 'mm'
        ax2.set_ylabel(ylabel, fontsize=9)
        ax2.set_xlabel('date', fontsize=9)
        ax2.set_ylim(lo, hi)
        ax2.grid(True, which='major', alpha=0.3)
        fig.autofmt_xdate(rotation=30)

    # initial series at the centre of the region (mirrors the pygmt version)
    render_ts(float(np.mean(lon)), float(np.mean(lat)))

    # ---- interactivity ------------------------------------------------------
    def _onclick(event):
        if getattr(event, 'inaxes', None) is not ax1:
            return
        if event.xdata is None or event.ydata is None:
            return
        # keep the click inside the map extent
        if not (lon.min() <= event.xdata <= lon.max() and lat.min() <= event.ydata <= lat.max()):
            return
        lonc = float(event.xdata)
        latc = float(event.ydata)
        click.set_data([lonc], [latc])
        render_ts(lonc, latc)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect('button_press_event', _onclick)

    plt.tight_layout()
    try:
        plt.show()  # safe under ipympl/Agg; under a widget backend the figure is already live
    except TypeError:
        pass
    return ax1


def light_preview_example():
    """Build a tiny synthetic cube and open the interactive viewer (self-test)."""
    import xarray as xr
    nt, nlat, nlon = 30, 41, 61
    lon = np.linspace(15.0, 16.0, nlon)
    lat = np.linspace(44.0, 45.0, nlat)
    time = pd.date_range('2020-01-01', periods=nt, freq='D')
    LON, LAT = np.meshgrid(lon, lat)
    base = np.sin(LAT * 2) * np.cos(LON * 2)
    vel = base * 10 + 0.1 * np.random.randn(nlat, nlon)
    tidx = np.arange(nt)[:, None, None]
    amp = np.random.rand(nlat, nlon) + 0.2
    cum = (amp[None, :, :] * tidx + 4.0 * np.sin(tidx / 3.0)) * 2.0
    mask = np.ones((nlat, nlon))
    ds = xr.Dataset(
        data_vars=dict(
            vel=(('lat', 'lon'), vel),
            cum=(('time', 'lat', 'lon'), cum),
            mask=(('lat', 'lon'), mask),
        ),
        coords=dict(lon=lon, lat=lat, time=time,
                    ref_lon=np.float32(15.5), ref_lat=np.float32(44.5)),
    )
    return pylight_plot_interactive(ds, 'Synthetic LiCSBAS: time series',
                                    'velocity [mm/year]', [-15, 15], 'polar')


if __name__ == '__main__':
    # Headless-friendly smoke test (use `%matplotlib widget` in a notebook).
    light_preview_example()
