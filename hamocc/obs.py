"""Observational datasets for the HAMOCC maps.

Each dataset is described in the recipe under `datasets.<key>` as
    {file: <path relative to obs_root>, var: <variable name>, scale: <factor>}
The files are the legacy preprocessed 1x1 degree products (HAMOCC_DIAG obs_data/).
"""
from pathlib import Path

import xarray as xr


def load_obs(spec, obs_root, depth=None):
    """Open one observed field in display units; select the nearest level when `depth` is given."""
    with xr.open_dataset(Path(obs_root) / spec["file"], decode_times=False) as ds:
        da = ds[spec["var"]].load()
    for dim in ("time", "month"):
        if dim in da.dims:
            da = da.mean(dim, skipna=True)
    if depth is not None:
        da = da.sel(depth=depth, method="nearest")
    da = da * spec.get("scale", 1.0)
    da.attrs["source"] = str(spec["file"])
    return da


def regrid_to_model(da, lat, lon, method="bilinear"):
    """Interpolate a regular lat/lon field onto the model's 2-D lat/lon (cell centres)."""
    import xesmf as xe

    target = xr.Dataset({"lat": (("y", "x"), lat), "lon": (("y", "x"), lon)})
    source = da.rename({d: "lat" if d.startswith(
        "lat") else "lon" for d in da.dims if d.startswith(("lat", "lon"))})
    regridder = xe.Regridder(source, target, method=method, periodic=True)
    out = regridder(source, skipna=True, na_thres=1.0)
    out.attrs.update(da.attrs)
    return out


def load_obs_region(spec, obs_root, region, depth=0.0):
    """Open the regional observed field `spec['file']` formatted with the region name.

    Returns the field in display units without averaging over time (the 12
    months are kept). Files may hold a lat/lon field or an already averaged cycle.
    Fields with a depth axis (e.g. WOA13 surface nutrients) are reduced to the
    level nearest `depth` (default 0 m, the surface).
    """
    path = Path(obs_root) / spec["file"].format(region=region)
    with xr.open_dataset(path, decode_times=False) as ds:
        da = ds[spec["var"]].load()
    if "depth" in da.dims:
        da = da.sel(depth=depth, method="nearest")
    da = da * spec.get("scale", 1.0)
    da.attrs["source"] = str(path.name)
    return da
