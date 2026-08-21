#!/usr/bin/env python3
#functions of plotting_cumulative_LoS_vs_GNSS.ipynb are imported and used here. Please refer to the notebook for the code and comments. This is just a script version of the notebook for easier execution and sharing.
import sys
import numpy as np
import xarray as xr
sys.path.append("/home/users/mnergiz/softwares/licsar_extra/python")  # adjust as needed
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MultipleLocator
import datetime as dt
import pandas as pd
import os
import pygmt
from pathlib import Path


def build_deseasonalized_gnss_dataset(
    root_dir,
    gnss_cum,
    csv_pattern="deseasonalized_*.csv",
    station_dim="station",
    time_dim="time",
    verbose=True,
):
    """
    Build an xarray GNSS dataset from station subfolders containing deseasonalized CSV files.

    Expected CSV columns
    --------------------
    date,dE_deseason,dN_deseason,dU_deseason,dE_sigma,dN_sigma,dU_sigma

    Parameters
    ----------
    root_dir : str or Path
        Directory containing one subfolder per station.
    gnss_cum : xr.Dataset
        Reference dataset used only to copy station lat/lon and to define
        which stations are valid.
    csv_pattern : str, default="deseasonalized_*.csv"
        Pattern used to find the CSV inside each station folder.
    station_dim : str, default="station"
        Name of station dimension in gnss_cum.
    time_dim : str, default="time"
        Name of time dimension in output dataset.
    verbose : bool, default=True
        Print progress messages.

    Returns
    -------
    xr.Dataset
        Dataset with variables:
            Ve, Vn, Vu, ve_sig, vn_sig, vu_sig
        and coordinates:
            station, time, lat, lon
    """

    root_dir = Path(root_dir)

    if not root_dir.exists():
        raise FileNotFoundError(f"Directory does not exist: {root_dir}")

    required_cols = [
        "date",
        "dE_deseason",
        "dN_deseason",
        "dU_deseason",
        "dE_sigma",
        "dN_sigma",
        "dU_sigma",
    ]

    valid_stations = set(gnss_cum[station_dim].values.tolist())

    station_data = {}
    all_times = set()

    # -------------------------
    # read each station folder
    # -------------------------
    for station_dir in sorted(root_dir.iterdir()):
        if not station_dir.is_dir():
            continue

        station_name = station_dir.name

        if station_name not in valid_stations:
            if verbose:
                print(f"Skipping {station_name}: not found in gnss_cum")
            continue

        csv_files = sorted(station_dir.glob(csv_pattern))

        if len(csv_files) == 0:
            if verbose:
                print(f"Skipping {station_name}: no file matching {csv_pattern}")
            continue

        if len(csv_files) > 1 and verbose:
            print(f"{station_name}: multiple CSV files found, using {csv_files[0].name}")

        csv_file = csv_files[0]

        try:
            df = pd.read_csv(csv_file)
        except Exception as e:
            if verbose:
                print(f"Skipping {station_name}: failed to read {csv_file.name} ({e})")
            continue

        # missing = [c for c in required_cols if c not in df.columns]
        # if missing:
        #     if verbose:
        #         print(f"Skipping {station_name}: missing columns {missing}")
        #     continue

        # df = df[required_cols].copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date")

        if df.empty:
            if verbose:
                print(f"Skipping {station_name}: no valid dates")
            continue

        df = df.drop_duplicates(subset="date", keep="first")
        df = df.set_index("date")

        station_data[station_name] = df
        all_times.update(df.index.to_pydatetime())

        if verbose:
            print(f"Loaded {station_name}: {len(df)} epochs")

    if len(station_data) == 0:
        raise ValueError("No valid station CSV files were loaded.")

    # -------------------------
    # common station/time axes
    # -------------------------
    stations = sorted(station_data.keys())
    times = pd.to_datetime(sorted(all_times))

    nsta = len(stations)
    nt = len(times)

    Ve = np.full((nsta, nt), np.nan, dtype=float)
    Vn = np.full((nsta, nt), np.nan, dtype=float)
    Vu = np.full((nsta, nt), np.nan, dtype=float)
    ve_sig = np.full((nsta, nt), np.nan, dtype=float)
    vn_sig = np.full((nsta, nt), np.nan, dtype=float)
    vu_sig = np.full((nsta, nt), np.nan, dtype=float)

    time_index = pd.Index(times)

    # -------------------------
    # fill arrays
    # -------------------------
    for i, sta in enumerate(stations):
        df = station_data[sta]
        idx = time_index.get_indexer(df.index)

        Ve[i, idx] = df.iloc[:, 0].to_numpy()
        Vn[i, idx] = df.iloc[:, 1].to_numpy()
        Vu[i, idx] = df.iloc[:, 2].to_numpy()
        ve_sig[i, idx] = df.iloc[:, 3].to_numpy()
        vn_sig[i, idx] = df.iloc[:, 4].to_numpy()
        vu_sig[i, idx] = df.iloc[:, 5].to_numpy()

    # -------------------------
    # copy lat/lon from gnss_cum
    # -------------------------
    lat = []
    lon = []

    for sta in stations:
        meta = gnss_cum.sel({station_dim: sta})
        lat.append(float(meta["lat"].values))
        lon.append(float(meta["lon"].values))

    lat = np.array(lat, dtype=float)
    lon = np.array(lon, dtype=float)

    # -------------------------
    # build output dataset
    # -------------------------
    ds_out = xr.Dataset(
        data_vars={
            "Ve": ((station_dim, time_dim), Ve),
            "Vn": ((station_dim, time_dim), Vn),
            "Vu": ((station_dim, time_dim), Vu),
            "ve_sig": ((station_dim, time_dim), ve_sig),
            "vn_sig": ((station_dim, time_dim), vn_sig),
            "vu_sig": ((station_dim, time_dim), vu_sig),
        },
        coords={
            station_dim: stations,
            time_dim: times,
            "lat": (station_dim, lat),
            "lon": (station_dim, lon),
        },
        attrs={
            "title": "Deseasonalized GNSS time series",
            "source_directory": str(root_dir),
            "note": "lat/lon copied from gnss_cum; stations missing in gnss_cum were skipped",
        },
    )

    return ds_out

def _get_pixel_window(da, reference, halfwin=4):
    """
    Return a subset window around the nearest pixel to (lon, lat).

    halfwin=4 means:
      x: ix-4 ... ix+4
      y: iy-4 ... iy+4
    i.e. a 9x9 window.
    """
    lon0, lat0 = reference

    # nearest pixel index
    ix = int(np.abs(da.lon.values - lon0).argmin())
    iy = int(np.abs(da.lat.values - lat0).argmin())

    # clip to image boundaries
    x1 = max(0, ix - halfwin)
    x2 = min(da.sizes["lon"], ix + halfwin + 1)
    y1 = max(0, iy - halfwin)
    y2 = min(da.sizes["lat"], iy + halfwin + 1)

    return da.isel(lon=slice(x1, x2), lat=slice(y1, y2))

def reference_ts_dataset(ds, reference, vars_to_ref=None, use_nearest=False, halfwin=4, verbose=True):

    if vars_to_ref is None:
        vars_to_ref = ["cum", "iono", "tide", "sltd"]

    ds_ref = ds.copy()

    for v in vars_to_ref:
        if v not in ds.data_vars:
            if verbose:
                print(f"Skipping '{v}': not found in dataset")
            continue

        da = ds[v]

        # ensure required dims exist
        if not {"time","lat","lon"}.issubset(da.dims):
            if verbose:
                print(f"Skipping '{v}': dims are {da.dims}")
            continue

        # 1) temporal reference
        da_tref = da - da.isel(time=0)

        if use_nearest:

            ref_ts = da_tref.sel(
                lon=reference[0],
                lat=reference[1],
                method="nearest"
            )

        else:
            # find nearest pixel index
            ix = int(np.abs(da.lon.values - reference[0]).argmin())
            iy = int(np.abs(da.lat.values - reference[1]).argmin())

            x1 = max(0, ix-halfwin)
            x2 = min(da.sizes["lon"], ix+halfwin+1)
            y1 = max(0, iy-halfwin)
            y2 = min(da.sizes["lat"], iy+halfwin+1)

            # extract window for all times
            ref_win = da_tref.isel(lon=slice(x1,x2), lat=slice(y1,y2))

            # average window → reference time series
            ref_ts = ref_win.mean(dim=("lat","lon"), skipna=True)

        ds_ref[v] = da_tref - ref_ts

        if verbose:
            if use_nearest:
                print(f"Referenced '{v}' using nearest pixel")
            else:
                print(f"Referenced '{v}' using ±{halfwin} pixel window")

    return ds_ref

def extract_ts_window_mean(da, point, halfwin=4):
    """
    Extract a time series from a (time, lat, lon) DataArray
    using the mean of a window around the nearest pixel to point.

    Parameters
    ----------
    da : xarray.DataArray
        Must have dims including (time, lat, lon)
    point : tuple
        (lon, lat)
    halfwin : int
        Half window size in pixels. halfwin=4 => 9x9 window

    Returns
    -------
    ts : xarray.DataArray
        1D time series
    """
    ix = int(np.abs(da.lon.values - point[0]).argmin())
    iy = int(np.abs(da.lat.values - point[1]).argmin())

    x1 = max(0, ix - halfwin)
    x2 = min(da.sizes["lon"], ix + halfwin + 1)
    y1 = max(0, iy - halfwin)
    y2 = min(da.sizes["lat"], iy + halfwin + 1)

    win = da.isel(lon=slice(x1, x2), lat=slice(y1, y2))
    ts = win.mean(dim=("lat", "lon"), skipna=True)

    return ts


def project_gnss_to_los(
    gnss_ds: xr.Dataset,
    E_unit: xr.DataArray,
    N_unit: xr.DataArray,
    U_unit: xr.DataArray | None = None,
    *,
    ve="Ve", vn="Vn", vu="Vu",
    lat="lat", lon="lon", station="station", time="time",
    method="nearest",
    los_name="gnss_los",
    keep_units=True,
    sboi=False,
    plot_enu=False,
    plot_station=None,
) -> xr.Dataset:
    """
    Project GNSS ENU (station,time) to LOS using separate ENU unit-vector DataArrays
    defined on (lat, lon).
    """

    # --------------------------------------------------
    # optional plot BEFORE LOS projection
    # --------------------------------------------------
    if plot_enu:
        if plot_station is None:
            raise ValueError("plot_station must be given when plot_enu=True")

        ds_sta = gnss_ds.sel({station: plot_station})

        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(pd.to_datetime(ds_sta[time].values), ds_sta[ve].values, "o-", label="dE", alpha=0.8)
        ax.plot(pd.to_datetime(ds_sta[time].values), ds_sta[vn].values, "o-", label="dN", alpha=0.8)

        if vu in ds_sta:
            ax.plot(pd.to_datetime(ds_sta[time].values), ds_sta[vu].values, "o-", label="dU", alpha=0.8)

        ax.set_title(f"{plot_station}: GNSS ENU before LOS projection")
        ax.set_xlabel("Date")
        ax.set_ylabel("Displacement (mm)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        plt.tight_layout()
        plt.savefig(f"{plot_station}_enu.png")
        plt.close()


    # sample unit vectors at GNSS station coordinates
    sample_points = {lat: gnss_ds[lat], lon: gnss_ds[lon]}

    if method == "nearest":
        E_u = E_unit.sel(sample_points, method="nearest")
        N_u = N_unit.sel(sample_points, method="nearest")
        U_u = None if U_unit is None else U_unit.sel(sample_points, method="nearest")
    elif method == "linear":
        E_u = E_unit.interp(sample_points)
        N_u = N_unit.interp(sample_points)
        U_u = None if U_unit is None else U_unit.interp(sample_points)
    else:
        raise ValueError("method must be 'nearest' or 'linear'")

    E_u = E_u.rename("E_unit")
    N_u = N_u.rename("N_unit")
    if U_u is not None:
        U_u = U_u.rename("U_unit")

    # dot product
    if sboi:
        los = gnss_ds[ve] * E_u + gnss_ds[vn] * N_u
    else:
        if U_u is None:
            raise ValueError("U_unit must be provided when sboi=False")
        los = gnss_ds[ve] * E_u + gnss_ds[vn] * N_u + gnss_ds[vu] * U_u

    los = los.rename(los_name)

    data_vars = {los_name: los}
    if keep_units:
        data_vars["E_unit"] = E_u
        data_vars["N_unit"] = N_u
        if U_u is not None:
            data_vars["U_unit"] = U_u

    out = xr.Dataset(
        data_vars=data_vars,
        coords={
            station: gnss_ds[station],
            time: gnss_ds[time],
            lat: gnss_ds[lat],
            lon: gnss_ds[lon],
        },
        attrs={
            "sampling": method,
            "sboi": int(bool(sboi)),
        },
    )

    return out

# def project_gnss_to_los(
#     gnss_ds: xr.Dataset,
#     E_unit: xr.DataArray,
#     N_unit: xr.DataArray,
#     U_unit: xr.DataArray | None = None,
#     *,
#     ve="Ve", vn="Vn", vu="Vu",
#     lat="lat", lon="lon", station="station", time="time",
#     method="nearest",
#     los_name="gnss_los",
#     keep_units=True,
#     sboi=False,
# ) -> xr.Dataset:
#     """
#     Project GNSS ENU (station,time) to LOS using separate ENU unit-vector DataArrays
#     defined on (lat, lon).

#     Parameters
#     ----------
#     gnss_ds : xr.Dataset
#         GNSS dataset containing velocity/displacement components and station coordinates.
#         Expected variables:
#           - ve, vn, vu with dims typically (station, time)
#         Expected coordinates:
#           - lat, lon with dim (station)
#           - station, time

#     E_unit, N_unit, U_unit : xr.DataArray
#         Unit-vector grids on (lat, lon).
#         For range LOS:
#             los = Ve*E + Vn*N + Vu*U
#         For SBOI / azimuth:
#             los = Ve*E + Vn*N
#             (U ignored)

#     method : {"nearest", "linear"}
#         Sampling method for extracting unit vectors at GNSS station locations.

#     keep_units : bool
#         If True, include sampled unit vectors in the output dataset.

#     sboi : bool
#         If True, project only horizontal components (Ve, Vn).

#     Returns
#     -------
#     xr.Dataset
#         Dataset containing:
#           - los_name : (station, time)
#           - optional sampled unit vectors: E_unit, N_unit, U_unit : (station,)
#     """

#     # sample unit vectors at GNSS station coordinates
#     sample_points = {lat: gnss_ds[lat], lon: gnss_ds[lon]}

#     if method == "nearest":
#         E_u = E_unit.sel(sample_points, method="nearest")
#         N_u = N_unit.sel(sample_points, method="nearest")
#         U_u = None if U_unit is None else U_unit.sel(sample_points, method="nearest")
#     elif method == "linear":
#         E_u = E_unit.interp(sample_points)
#         N_u = N_unit.interp(sample_points)
#         U_u = None if U_unit is None else U_unit.interp(sample_points)
#     else:
#         raise ValueError("method must be 'nearest' or 'linear'")

#     # make sure sampled vectors are station-only
#     # after sel/interp with station-wise lat/lon, xarray should return dim=(station)
#     E_u = E_u.rename("E_unit")
#     N_u = N_u.rename("N_unit")
#     if U_u is not None:
#         U_u = U_u.rename("U_unit")

#     # dot product
#     if sboi:
#         los = gnss_ds[ve] * E_u + gnss_ds[vn] * N_u
#     else:
#         if U_u is None:
#             raise ValueError("U_unit must be provided when sboi=False")
#         los = gnss_ds[ve] * E_u + gnss_ds[vn] * N_u + gnss_ds[vu] * U_u

#     los = los.rename(los_name)

#     data_vars = {los_name: los}
#     if keep_units:
#         data_vars["E_unit"] = E_u
#         data_vars["N_unit"] = N_u
#         if U_u is not None:
#             data_vars["U_unit"] = U_u

#     out = xr.Dataset(
#         data_vars=data_vars,
#         coords={
#             station: gnss_ds[station],
#             time: gnss_ds[time],
#             lat: gnss_ds[lat],
#             lon: gnss_ds[lon],
#         },
#         attrs={
#             "sampling": method,
#             "sboi": int(bool(sboi)),
#         },
#     )

#     return out

def los_points_at_time(los_ds: xr.Dataset, var="los_asc_range", t=None):
    """
    Return a pandas DataFrame with station, lon, lat, value for a chosen time.
    If t is None, use the last epoch.
    """
    if t is None:
        t = los_ds["time"].values[-1]

    da = los_ds[var].sel(time=t)
    df = da.to_dataframe(name="v").reset_index()

    return df[["station", "lon", "lat", "v"]], t

def get_station_coords(ds, station_name, lat="lat", lon="lon", station="station"):
    st = ds.sel({station: station_name})
    return float(st[lon].values), float(st[lat].values)  # (lon, lat)

def reference_gnss_dataset(
    ds,
    reference_station="KLS1",
    vars_to_ref=("Ve", "Vn", "Vu"),
    station_dim="station",
    time_dim="time",
    verbose=True,
):
    ds_ref = ds.copy()

    for v in vars_to_ref:
        if v not in ds.data_vars:
            if verbose:
                print(f"Skipping '{v}': not found")
            continue

        da = ds[v]

        if not {station_dim, time_dim}.issubset(da.dims):
            if verbose:
                print(f"Skipping '{v}': dims are {da.dims}")
            continue

        # 1) temporal reference to first epoch
        da_tref = da - da.isel({time_dim: 0})

        # 2) spatial reference to reference station
        ref_ts = da_tref.sel({station_dim: reference_station})

        # subtract KLS1 time series from all stations
        ds_ref[v] = da_tref - ref_ts

        if verbose:
            print(f"Referenced '{v}' to first epoch and station '{reference_station}'")

    ds_ref.attrs["reference_station"] = reference_station
    return ds_ref

def plot_cumulative_grid(
    da,
    outname,
    nplots=25,
    ncols=5,
    vmin=-150,
    vmax=150,
    cmap_name="RdBu",
    extend="both",
    figsize=(12, 12),
    cbar_label="Displacement (mm)",
    reference=None,
):
    """
    Plot selected cumulative epochs in a grid with one shared vertical colorbar.

    Parameters
    ----------
    da : xr.DataArray
        DataArray with dimensions including time, lat, lon.
    outname : str
        Output figure filename.
    nplots : int
        Number of epochs to plot.
    ncols : int
        Number of columns in subplot grid.
    vmin, vmax : float
        Color scale limits.
    cmap_name : str
        Matplotlib colormap name.
    extend : str
        Colorbar extend mode: 'neither', 'min', 'max', 'both'.
    figsize : tuple
        Figure size in inches.
    cbar_label : str
        Colorbar label.
    reference : tuple or None
        Optional reference point as (lon, lat).
    """
    if "time" not in da.dims:
        raise ValueError("Input DataArray must contain a 'time' dimension.")

    nt = da.sizes["time"]
    if nt == 0:
        raise ValueError("Input DataArray has zero time steps.")

    nplots = min(nplots, nt)
    idx = np.linspace(0, nt - 1, nplots, dtype=int)
    da_sel = da.isel(time=idx)

    nrows = int(np.ceil(nplots / ncols))

    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=figsize,
        constrained_layout=True,
        squeeze=False,
    )

    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad((1, 1, 1, 0))  # transparent NaNs

    im = None

    for i, ax in enumerate(axes.flat):
        if i >= nplots:
            ax.axis("off")
            continue

        da_i = da_sel.isel(time=i)

        im = da_i.plot(
            ax=ax,
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
            add_colorbar=False,
            add_labels=False,
        )

        if reference is not None:
            ax.plot(
                reference[0],
                reference[1],
                marker="o",
                markersize=4,
                markerfacecolor="none",
                markeredgecolor="k",
                markeredgewidth=1.0,
            )

        t = da_sel.time.values[i]
        try:
            title = pd.to_datetime(t).strftime("%Y-%m-%d")
        except Exception:
            title = str(t)[:10]

        ax.set_title(title, fontsize=8)
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_facecolor("none")

    cbar = fig.colorbar(
        im,
        ax=axes,
        orientation="vertical",
        fraction=0.025,
        pad=0.02,
        extend=extend,
    )
    cbar.set_label(cbar_label)

    fig.savefig(outname, dpi=300, bbox_inches="tight")
    plt.close(fig)
    
    
def plot_los_comparison(
    time_insar,
    cum_ts,
    time_gnss,
    gnss_los_ts,
    point_loc,
    outname=None,
    cum_filt_ts=None,
):
    """
    Plot referenced LOS time series comparison between InSAR and GNSS.
    """
    cm = 1 / 2.54  # inches per cm

    fig, ax = plt.subplots(1, 1, figsize=(12 * cm, 7 * cm))
    plt.rcParams["legend.fontsize"] = 8

    # mean_cum = np.nanmean(cum_ts)
    # std_cum = np.nanstd(cum_ts)

    # mean_gnss_cum = np.nanmean(gnss_los_ts[0])
    # std_gnss_cum = np.nanstd(gnss_los_ts[0])
    # mean_gnss_daily = np.nanmean(gnss_los_ts[1])
    # std_gnss_daily = np.nanstd(gnss_los_ts[1])

    ax.plot(
        time_insar,
        cum_ts,
        color="red",
        marker="o",
        linestyle="None",
        markeredgecolor="none",
        alpha=0.3,
        markersize=4,
        # label=f"InSAR",
    )

    if cum_filt_ts is not None:
        # mean_cum_filt = np.nanmean(cum_filt_ts)
        # std_cum_filt = np.nanstd(cum_filt_ts)
        ax.plot(
            time_insar,
            cum_filt_ts,
            color="red",
            linewidth=1,
            linestyle="-",
            label=f"InSAR",
        )

    # shadow (daily GNSS)
    ax.plot(
        time_gnss[1],
        gnss_los_ts[1],
        color="0.5",
        marker="o",
        markersize=3,
        linestyle="None",
        alpha=0.3,
        markeredgecolor="none",
        zorder=1,
    )

    ax.plot(
        time_gnss[0],
        gnss_los_ts[0],
        color="gray",
        linewidth=1,
        linestyle="-",
        zorder=3,
        alpha=0.9,
        label=f"GNSS",
    )

    ax.set_title(f"Referenced LOS comparison at {point_loc}")
    ax.set_ylabel("Displacement (mm)")
    ax.axhline(0, color="k", lw=0.8, alpha=0.4)

    locator = mdates.MonthLocator(interval=6)
    formatter = mdates.DateFormatter("%Y-%m")
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower left")

    fig.tight_layout()

    if outname is not None:
        fig.savefig(outname, dpi=300, bbox_inches="tight")

    plt.show()

def ensure_dem(
    dem_file="earth_relief_fullAHB_30s.nc",
    region_download=(1, 80, 25, 60),
    resolution="30s",
):
    """
    Ensure DEM exists in BATCH_CACHE_DIR and return its path.
    """
    batchdir = os.environ.get("BATCH_CACHE_DIR")
    if batchdir is None:
        raise EnvironmentError("BATCH_CACHE_DIR is not set")

    dem = os.path.join(batchdir, dem_file)

    if not os.path.exists(dem):
        print("DEM is downloading. After downloading, the process will be faster.")
        grid = pygmt.datasets.load_earth_relief(
            resolution=resolution,
            region=list(region_download),
        )
        grid.to_netcdf(dem)
        print(f"DEM saved to {dem}")
    else:
        print("DEM already exists")

    return dem


def plot_cumulative_pygmt(
    grid,
    df_stations,
    point1,
    reference,
    outname,
    *,
    projection="M5c",
    dem=None,
    dem_file="earth_relief_fullAHB_30s.nc",
    grid_label="",
    grid_cmap="vik",
    grid_series=(-150, 150, 1),
    dem_series=(-200, 10000, 3000),
    show_station_names=True,
    station_font="6p,Helvetica,black",
    point_style="c0.25c",
    ref_style="r0.20c/0.20c",
    point_fill="magenta1",
    ref_fill="magenta1",
):
    """
    Plot cumulative deformation over DEM using PyGMT.

    Parameters
    ----------
    grid : xarray.DataArray
        2D deformation grid to plot.
    df_stations : pandas.DataFrame
        Must contain columns: station, lon, lat, v
    point1 : tuple
        Point location as (lon, lat)
    reference : tuple
        Reference location as (lon, lat)
    outname : str
        Output figure filename

    Optional parameters control style, region, labels, etc.
    """

    # -------------------------
    # DEM
    # -------------------------
    if dem is None:
        dem = ensure_dem(dem_file=dem_file)

    # remove NaN/zero stations once here
    dfD = df_stations.dropna().copy()
    # region 
    lon_min = grid.lon.min().item()-0.1
    lon_max = grid.lon.max().item()+0.1
    lat_min = grid.lat.min().item()-0.1
    lat_max = grid.lat.max().item()+0.1
    plot_region = [lon_min, lon_max, lat_min, lat_max]
    
    # -------------------------
    # Figure and main config
    # -------------------------
    fig = pygmt.Figure()

    pygmt.config(
        MAP_FRAME_TYPE="plain",
        FONT_ANNOT_PRIMARY="20p,Helvetica,black",
        FONT_LABEL="20p,Helvetica,black",
        FORMAT_GEO_MAP="D",
        MAP_FRAME_PEN="0.5p,black",
        MAP_DEFAULT_PEN="0.5p,black",
        MAP_TICK_LENGTH="5p",
    )

    # -------------------------
    # Basemap + DEM
    # -------------------------
    fig.basemap(
        projection=projection,
        region=list(plot_region),
        frame=["WSne"],
    )

    pygmt.makecpt(
        cmap="gray",
        series=list(dem_series),
        continuous=True,
        reverse=True,
    )

    fig.grdimage(
        grid=dem,
        cmap=True,
        region=list(plot_region),
        shading=True,
        frame=False,
    )

    fig.coast(
        shorelines="black",
        water="skyblue",
    )

    # -------------------------
    # Deformation grid
    # -------------------------
    pygmt.makecpt(
        cmap=grid_cmap,
        series=list(grid_series),
        continuous=True,
    )

    fig.grdimage(
        grid=grid,
        cmap=True,
        region=list(plot_region),
        nan_transparent=True,
    )

    # -------------------------
    # Colorbar
    # -------------------------
    pygmt.config(
        MAP_FRAME_TYPE="plain",
        FONT_ANNOT_PRIMARY="25p,Helvetica,black",
        FONT_LABEL="25p,Helvetica,black",
    )

    cbar_min, cbar_max, cbar_step = grid_series
    fig.colorbar(
        frame=f"a{abs(cbar_max-cbar_min)/2:.0f}f50+l{grid_label}[mm]",
        cmap=True,
        position="JBC+o0c/0.5c+w3c/0.25c+ml+h+e",
    )

    # # -------------------------
    # # Point of interest
    # # -------------------------
    # fig.plot(
    #     x=point1[0],
    #     y=point1[1],
    #     style=point_style,
    #     fill=point_fill,
    #     pen="0.5p,black",
    # )

    # -------------------------
    # Reference point
    # -------------------------
    fig.plot(
        x=reference[0],
        y=reference[1],
        style=ref_style,
        fill=ref_fill,
        pen="0.5p,black",
    )

    # -------------------------
    # GNSS station symbols
    # -------------------------
    fig.plot(
        x=dfD["lon"].values,
        y=dfD["lat"].values,
        style="t0.2c",
        fill=dfD["v"].values,
        cmap=True,
        pen="0.2p,black",
    )

    # -------------------------
    # Station names
    # -------------------------
    if show_station_names:
        for _, row in dfD.iterrows():
            fig.text(
                x=row["lon"],
                y=row["lat"],
                text=str(row["station"]),
                font=station_font,
                justify="LT",
                offset="0.05c/0.05c",
            )

    # -------------------------
    # Final frame
    # -------------------------
    pygmt.config(
        MAP_FRAME_TYPE="inside",
        FONT_ANNOT="9p,Helvetica,black",
    )

    fig.basemap(
        projection=projection,
        region=list(plot_region),
        frame=["x2f1", "y2f1", "WSne"],
    )

    fig.savefig(outname)
    fig.show()

    return fig