"""Annual-mean model fields for the HAMOCC maps, in display units."""
import numpy as np
import xarray as xr

from . import variables as v

DEPTH_TOLERANCE_M = 1.0


def _spec(name):
    """Registry entry for a mappable variable (z-level, surface or net CO2)."""
    for table in (v.LEVEL_VARS, v.SURFACE_VARS, v.MONTHLY_VARS, v.PHYS_MONTHLY_VARS):
        if name in table:
            return table[name]
    if name == v.CO2_NET.name:
        return v.CO2_NET
    raise KeyError(f"Unknown HAMOCC map variable: {name}")


def history_names(name, monthly=False):
    """History variables needed to build `name` (`monthly`: from the hbgcm files)."""
    if name == "aoulvl":
        return ["p_o2lvl", "o2lvl"]
    if name == "co2fxn":
        return ["co2fxd", "co2fxu"]
    return [name]


def raw_field(ds, name):
    """The field in model units, before scaling (derived fields are computed here)."""
    if name == "aoulvl":
        return v.aou(ds["o2lvl"], ds["p_o2lvl"])
    if name == "co2fxn":
        return v.co2_net(ds["co2fxd"], ds["co2fxu"])
    return ds[name]


def select_depth(da, depth):
    """Pick the z-level closest to `depth` (m); fail if none is within DEPTH_TOLERANCE_M."""
    level = da.sel(depth=depth, method="nearest")
    if abs(float(level["depth"]) - depth) > DEPTH_TOLERANCE_M:
        raise ValueError(f"No level near {
                         depth} m (nearest is {float(level['depth'])} m)")
    return level


def annual_mean_map(ds, name, depth=None):
    """Time-mean 2-D field of `name` in display units, optionally at `depth` (m)."""
    spec = _spec(name)
    da = raw_field(ds, name)
    if depth is not None:
        da = select_depth(da, depth)
    out = (da.mean("time", skipna=True) * spec.scale).rename(name)
    out.attrs.update(long_name=spec.long_name, units=spec.units)
    return out


def difference(model, obs, label="model - obs"):
    """Model minus obs (or test minus control) on the same grid, keeping the units."""
    diff = (model - obs).rename(model.name)
    diff.attrs.update(long_name=f"{model.attrs.get('long_name', model.name)}, {label}",
                      units=model.attrs.get("units", ""))
    return diff


def section_area(da, lat_name="lat"):
    """cos(latitude) weights on the latitude axis of `da`, for latitude-depth sections."""
    return np.cos(np.deg2rad(da[lat_name])).clip(min=0.0)


def stats(model, obs, area=None):
    """Area-weighted mean, bias and RMSE of `model` against `obs` over the cells valid in both.

    `area` is a weight on (a subset of) the dims of `model`, e.g. `parea` for maps or
    `section_area(model)` for sections; None means equal weights. The means of model and obs
    are over the common cells too, so `bias == model_mean - obs_mean`.
    Returns a dict with `model_mean`, `obs_mean`, `bias`, `rmse` (floats, display units)
    and `n` (number of common cells); the values are NaN if there is no common cell.
    """
    model, obs = xr.align(model, obs, join="exact")
    weight = xr.ones_like(
        model, dtype=float) if area is None else xr.broadcast(area, model)[0]
    valid = model.notnull() & obs.notnull() & weight.notnull()
    w = weight.where(valid, 0.0)
    wsum = float(w.sum())
    n = int(valid.sum())
    if n == 0 or wsum == 0.0:
        nan = float("nan")
        return {"model_mean": nan, "obs_mean": nan, "bias": nan, "rmse": nan, "n": n}
    m = float((model.where(valid, 0.0) * w).sum()) / wsum
    o = float((obs.where(valid, 0.0) * w).sum()) / wsum
    sq = float((((model - obs) ** 2).where(valid, 0.0) * w).sum()) / wsum
    return {"model_mean": m, "obs_mean": o, "bias": m - o, "rmse": sq ** 0.5, "n": n}


def stats_label(s, ref="obs"):
    """Short text with the numbers of `stats`, for panel titles (`ref` names the reference field)."""
    return f"mean {s['model_mean']:.3g}, {ref} {s['obs_mean']:.3g}, bias {s['bias']:.3g}, RMSE {s['rmse']:.3g}"


def layer_sum(da, exclude=("time", "y", "x")):
    """Sum over the vertical (layer) dimension, i.e. every dim not in `exclude`."""
    dims = [d for d in da.dims if d not in exclude]
    return da.sum(dims, skipna=True, min_count=1)


def monthly_raw(ds, name):
    """Monthly field in model units."""
    return raw_field(ds, name)


def monthly_cycle(ds, name):
    """Multi-year mean annual cycle of `name` in display units, with dim `month` (1-12)."""
    spec = _spec(name)
    da = monthly_raw(ds, name)
    out = da.groupby("time.month").mean("time", skipna=True) * spec.scale
    out = out.rename(name)
    out.attrs.update(long_name=spec.long_name, units=spec.units)
    return out
