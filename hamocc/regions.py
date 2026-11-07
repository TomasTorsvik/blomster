"""Regional means and monthly cycles on the regular 1x1 degree grid.

Region masks are built from the basin masks of the zonal means plus the
latitude bounds in `variables.REGIONS`, so no per-variable region files are
needed. Means are area-weighted (cos latitude).
"""
import numpy as np
import xarray as xr

from . import variables as v


def region_mask(basin_masks, region, grid):
    """Boolean mask (lat, lon) of `region` on the target `grid` (see zonal.target_grid)."""
    from . import zonal

    _, lat_min, lat_max = v.REGIONS[region]
    basin = basin_masks[v.REGION_BASINS[region]]
    in_basin = basin.reindex(lat=grid["lat"], lon=grid["lon"], method="nearest") > 0
    lat = grid["lat"]
    lon = grid["lon"]
    mask = in_basin & (lat >= lat_min) & (lat < lat_max)
    if region in v.REGION_EXCLUSIONS:
        la0, la1, lo0, lo1 = v.REGION_EXCLUSIONS[region]
        mask = mask & ~((lat >= la0) & (lat <= la1) & (lon >= lo0) & (lon <= lo1))
    return mask


def weighted_mean(da, mask):
    """Area-weighted (cos lat) mean of `da` over the `mask` cells, ignoring missing values."""
    weight = np.cos(np.deg2rad(da["lat"])).where(mask).where(da.notnull())
    return (da * weight).sum(["lat", "lon"]) / weight.sum(["lat", "lon"])


def to_month_index(da):
    """Label a 12-step obs cycle by month 1-12 (the file's time/month axis is positional)."""
    dim = next((d for d in ("month", "time") if d in da.dims), None)
    if dim is None or da.sizes[dim] != 12:
        raise ValueError(f"Expected a 12-step monthly axis, got dims {dict(da.sizes)}")
    return da.rename({dim: "month"}).assign_coords(month=np.arange(1, 13))


def obs_cycle(da, mask=None):
    """Regional monthly cycle of an observed field.

    Fields that still carry lat/lon are averaged over `mask`; fields that are
    already regional means (no horizontal dims) are only relabelled by month.
    """
    da = da.squeeze(drop=True)
    if "lat" in da.dims or "lon" in da.dims:
        if mask is None:
            raise ValueError("Obs field has lat/lon: a region mask is required")
        from .zonal import normalize_lon

        da = weighted_mean(normalize_lon(da).reindex(lat=mask["lat"], lon=mask["lon"], method="nearest"), mask)
    return to_month_index(da)


def model_cycle(field_1x1, mask):
    """Regional monthly cycle of a model field already on the 1x1 grid, with dim `month`."""
    out = weighted_mean(field_1x1, mask)
    out.attrs.update(field_1x1.attrs)
    return out
