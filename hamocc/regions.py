"""Regional means and monthly cycles on the regular 1x1 degree grid.

Region masks are built from the basin masks of the zonal means plus the
latitude bounds in `variables.REGIONS`. The legacy diagnostics additionally
mask every variable with its own (monthly) data-coverage mask, so model and
obs are averaged over the same cells; `variable_region_mask` reproduces that.
Means are area-weighted (cos latitude).
"""
from pathlib import Path

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


def load_variable_mask(path, var="mask"):
    """Boolean mask from a legacy 1x1 mask file, longitudes normalised to 0-360.

    Legacy per-variable files carry a monthly `time` axis (12 steps, positional)
    and sometimes a length-1 `depth`; the result has dims (lat, lon) or
    (month, lat, lon). Non-zero and non-NaN means valid.
    """
    from .zonal import normalize_lon

    with xr.open_dataset(path, decode_times=False) as ds:
        mask = ds[var].load()
    if "depth" in mask.dims:
        mask = mask.isel(depth=0, drop=True)
    if "time" in mask.dims:
        if mask.sizes["time"] != 12:
            raise ValueError(f"{path}: expected 12 monthly mask steps, got {mask.sizes['time']}")
        mask = mask.rename(time="month").assign_coords(month=np.arange(1, 13))
    mask = (mask.fillna(0) > 0).reset_coords(drop=True)
    return normalize_lon(mask)


def combine_masks(region, variable):
    """Cells that are in both `region` (lat, lon) and `variable` (optionally with `month`)."""
    variable = variable.reindex(lat=region["lat"], lon=region["lon"], method="nearest")
    return region & variable


def variable_region_mask(name, region, region_mask, spec=None, grid=None):
    """Mask used to average variable `name` over `region`.

    `spec` is `datasets.regional_mask` of the recipe (root, region_file, var_file,
    var, alias). Resolution order: (1) the legacy per-variable region file, which
    already is region AND variable mask, as used by HAMOCC_DIAG; (2) the generic
    `region_mask` combined with the variable's own mask file; (3) `region_mask`
    alone. `region_mask` is the boolean (lat, lon) mask from `region_mask()`.
    Returns a boolean mask on the grid of `region_mask`.
    """
    if not spec:
        return region_mask
    root = Path(spec["root"])
    key = spec.get("alias", {}).get(name, name)
    mvar = spec.get("var", "mask")
    path = root / spec["region_file"].format(var=key, region=region)
    if path.exists():
        m = load_variable_mask(path, mvar)
        return m.reindex(lat=region_mask["lat"], lon=region_mask["lon"], method="nearest")
    vpath = root / spec["var_file"].format(var=key)
    if vpath.exists():
        return combine_masks(region_mask, load_variable_mask(vpath, mvar))
    return region_mask


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
    da = to_month_index(da.squeeze(drop=True))
    if "lat" in da.dims or "lon" in da.dims:
        if mask is None:
            raise ValueError("Obs field has lat/lon: a region mask is required")
        from .zonal import normalize_lon

        da = weighted_mean(normalize_lon(da).reindex(lat=mask["lat"], lon=mask["lon"], method="nearest"), mask)
    return da


def model_cycle(field_1x1, mask):
    """Regional monthly cycle of a model field already on the 1x1 grid, with dim `month`.

    `mask` may be (lat, lon) or monthly (month, lat, lon); the month coordinate
    of the field must be 1-12 to line up with a monthly mask.
    """
    out = weighted_mean(field_1x1, mask)
    out.attrs.update(field_1x1.attrs)
    return out
