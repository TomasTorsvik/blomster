"""Basin zonal means (latitude-depth) of HAMOCC z-level fields.

As in the legacy diagnostics, the model is interpolated to a regular 1x1
degree grid, a basin mask is applied and the field is averaged over longitude.
Observations (already 1x1 degree) are put on the same grid and levels, and
the model is masked where the observations are missing so that both means
use the same cells.
"""
from pathlib import Path

import numpy as np
import xarray as xr


def target_grid(res=1.0):
    """Cell-centre latitudes and longitudes (0-360) of the regular target grid."""
    lat = np.arange(-90 + res / 2, 90, res)
    lon = np.arange(res / 2, 360, res)
    return xr.Dataset({"lat": ("lat", lat), "lon": ("lon", lon)})


def _n_fold_rows(model_lat, model_lon):
    """Number of trailing rows of a tripolar grid that only repeat points of the rows below (the fold).

    ESMF cannot build a bilinear regridder from a grid with such duplicated points.
    """
    lat, lon = np.asarray(model_lat), np.asarray(model_lon)
    n = 0
    while lat.shape[0] - n > 1:
        row = lat.shape[0] - n - 1
        below = set(zip(lat[:row].round(6).ravel(), lon[:row].round(6).ravel()))
        if all(pt in below for pt in zip(lat[row].round(6), lon[row].round(6))):
            n += 1
        else:
            break
    return n


class _TrimmedRegridder:
    """Regridder that ignores the duplicated fold rows of the model grid, so it takes full model fields."""

    def __init__(self, regridder, ny, y_dim="y"):
        self._regridder, self._ny, self._y_dim = regridder, ny, y_dim

    def __getattr__(self, name):
        return getattr(self._regridder, name)

    def __call__(self, da, **kwargs):
        if self._y_dim in da.dims and da.sizes[self._y_dim] > self._ny:
            da = da.isel({self._y_dim: slice(0, self._ny)})
        return self._regridder(da, **kwargs)


def make_regridder(model_lat, model_lon, res=1.0, method="bilinear"):
    """xesmf regridder from the model's 2-D cell centres to the regular grid.

    Duplicated fold rows at the top of a tripolar grid are left out; the returned regridder accepts
    fields on the full model grid and drops them itself.
    """
    import xesmf as xe

    ny = np.asarray(model_lat).shape[0] - _n_fold_rows(model_lat, model_lon)
    source = xr.Dataset({"lat": (("y", "x"), np.asarray(model_lat)[:ny]),
                        "lon": (("y", "x"), np.asarray(model_lon)[:ny])})
    regridder = xe.Regridder(source, target_grid(res), method=method, periodic=True,
                             unmapped_to_nan=True)
    return _TrimmedRegridder(regridder, ny)


def normalize_lon(da, lon_name="lon"):
    """Express longitudes as 0-360 and sort, so grids with -180..180 match the target."""
    return da.assign_coords({lon_name: da[lon_name] % 360}).sortby(lon_name)


def load_basin_mask(path, var):
    """Basin mask (1 inside the basin) on a lat/lon grid with 0-360 longitudes."""
    with xr.open_dataset(path) as ds:
        mask = ds[var].load()
    return normalize_lon(mask)


def on_target_grid(da, grid, depth=None):
    """Interpolate an observed field to the target lat/lon (and optionally model depths)."""
    da = normalize_lon(da)
    out = da.interp(lat=grid["lat"], lon=grid["lon"],
                    kwargs={"fill_value": np.nan})
    if depth is not None and "depth" in out.dims:
        out = out.interp(depth=depth, kwargs={"fill_value": np.nan})
    return out


def zonal_mean(da, mask):
    """Mean over longitude of `da` inside the basin `mask` (mask on the same lat/lon)."""
    mask = mask.reindex(lat=da["lat"], lon=da["lon"], method="nearest")
    return da.where(mask > 0).mean("lon", skipna=True)


def common_cells(model, obs):
    """Model with missing values wherever `obs` has none (and vice versa)."""
    return model.where(obs.notnull()), obs.where(model.notnull())


def basin_zonal_means(model, obs, mask):
    """Zonal means of model and obs over the same cells of the basin `mask`."""
    model, obs = common_cells(model, obs)
    return zonal_mean(model, mask), zonal_mean(obs, mask)
