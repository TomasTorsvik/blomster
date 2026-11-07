"""Annual global time series of HAMOCC diagnostics.

Two kinds, as in the legacy plot_time_series_ann_{avg,fluxes}.ncl:
  * volume-weighted global means of 3-D concentrations (full depth and 0-100 m)
  * area-integrated annual fluxes (Pg C yr-1 etc.)

All functions expect the horizontal dims to be the last two dims of the
variables (y, x) and take the grid cell area `parea` (m2) as a DataArray on
the same dims.
"""
import numpy as np
import xarray as xr

from . import variables as v

HORIZONTAL_DIMS = ("y", "x")


def load_parea(grid_file, dims=HORIZONTAL_DIMS, name="parea"):
    """Grid cell area (m2) of the BLOM p-grid, labelled with the history file's horizontal dims."""
    with xr.open_dataset(grid_file) as grid:
        data = grid[name].values
    return xr.DataArray(data, dims=dims, name="parea", attrs={"units": "m2"})


def annual_index(da, offset=0):
    """Replace the cftime time axis by integer model years (plus `offset`)."""
    year = da["time"].dt.year.values + offset
    return da.assign_coords(time=year).rename(time="year")


def volume_mean(da, thickness, parea, dims=None):
    """Volume-weighted mean over all non-time dims.

    `thickness` is the layer thickness (m): `pddpo` for isopycnic layers or
    the z-level thickness. Cells where `da` is missing get zero weight.
    """
    weight = (thickness * parea).where(da.notnull())
    dims = dims or [d for d in da.dims if d != "time"]
    return (da * weight).sum(dims) / weight.sum(dims)


def level_thickness(depth_bnds, zmin=0.0, zmax=None):
    """Thickness (m) of each z-level, optionally clipped to [zmin, zmax]."""
    upper = depth_bnds.isel(bnds=0)
    lower = depth_bnds.isel(bnds=1)
    if zmax is not None:
        lower = lower.clip(max=zmax)
    upper = upper.clip(min=zmin)
    return (lower - upper).clip(min=0.0)


def upper_ocean_mean(da, depth_bnds, parea, zmax=100.0):
    """Volume-weighted mean of a z-level field over 0-`zmax` m."""
    dz = level_thickness(depth_bnds, 0.0, zmax)
    return volume_mean(da, dz, parea)


def global_mean_series(ds, name, parea, zmax=None, offset=0):
    """Annual global volume mean of `name` in display units.

    With `zmax` the z-level variable `{name}lvl` is averaged over 0-zmax m;
    otherwise the 3-D variable is weighted with `pddpo`.
    """
    var = v.CONC_TS_VARS[name]
    if zmax is None:
        series = volume_mean(ds[name], ds["pddpo"], parea)
    else:
        series = upper_ocean_mean(ds[f"{name}lvl"], ds["depth_bnds"], parea, zmax)
    series = (series * var.scale).rename(name)
    series.attrs.update(long_name=var.long_name, units=var.units)
    return annual_index(series, offset)


def flux_series(ds, name, parea, offset=0):
    """Annual area-integrated flux of `name` in display units (e.g. Pg C yr-1).

    `co2fxn` is the net flux into the ocean, co2fxd - co2fxu.
    """
    if name == "co2fxn":
        field = v.co2_net(ds["co2fxd"], ds["co2fxu"])
        var = v.FLUX_TS_VARS["co2fxd"]
        long_name = "Net CO2 flux into ocean"
    else:
        field = ds[name]
        var = v.FLUX_TS_VARS[name]
        long_name = var.long_name
    total = (field * parea).sum([d for d in field.dims if d != "time"]) * var.scale
    total = total.rename(name)
    total.attrs.update(long_name=long_name, units=var.units)
    return annual_index(total, offset)


def drift(series):
    """Linear trend of an annual series, in units of the series per year."""
    years = series["year"].values.astype(float)
    return float(np.polyfit(years, series.values, 1)[0])
