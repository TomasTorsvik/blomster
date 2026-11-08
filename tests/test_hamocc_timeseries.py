import cftime
import numpy as np
import pytest
import xarray as xr

from hamocc import timeseries as ts
from hamocc import variables as v


def _grid(ny=2, nx=3):
    return xr.DataArray(np.full((ny, nx), 2.0), dims=("y", "x"), name="parea")


def _time(n):
    return xr.DataArray([cftime.DatetimeNoLeap(y, 7, 1) for y in range(1, n + 1)], dims="time")


def test_volume_mean_weights_by_thickness():
    parea = _grid()
    da = xr.DataArray(np.zeros((1, 2, 2, 3)), dims=("time", "depth", "y", "x"))
    da[:, 0] = 1.0
    da[:, 1] = 3.0
    dz = xr.DataArray([10.0, 30.0], dims="depth")
    out = ts.volume_mean(da, dz, parea)
    assert out.item() == pytest.approx((1 * 10 + 3 * 30) / 40)


def test_volume_mean_ignores_missing():
    parea = _grid()
    da = xr.DataArray(np.ones((1, 1, 2, 3)), dims=("time", "depth", "y", "x"))
    da[..., 0, 0] = np.nan
    out = ts.volume_mean(da, xr.DataArray([5.0], dims="depth"), parea)
    assert out.item() == pytest.approx(1.0)


def test_level_thickness_clips_to_zmax():
    bnds = xr.DataArray([[0.0, 50.0], [50.0, 150.0], [150.0, 400.0]], dims=("depth", "bnds"))
    dz = ts.level_thickness(bnds, 0.0, 100.0)
    assert dz.values.tolist() == [50.0, 50.0, 0.0]


def test_level_thickness_uses_last_dim_as_bounds():
    """NorESM3 history files name the bounds dimension `bounds`, not `bnds`."""
    bnds = xr.DataArray([[0.0, 50.0], [50.0, 150.0]], dims=("depth", "bounds"))
    assert ts.level_thickness(bnds).values.tolist() == [50.0, 100.0]


def test_upper_ocean_mean_uses_only_top_100m():
    parea = _grid()
    bnds = xr.DataArray([[0.0, 50.0], [50.0, 150.0], [150.0, 400.0]], dims=("depth", "bnds"))
    da = xr.DataArray(np.zeros((1, 3, 2, 3)), dims=("time", "depth", "y", "x"))
    da[:, 0] = 1.0
    da[:, 1] = 2.0
    da[:, 2] = 100.0
    out = ts.upper_ocean_mean(da, bnds, parea, 100.0)
    assert out.item() == pytest.approx(1.5)


def test_flux_series_net_co2_pg_per_year():
    parea = _grid()  # total area 12 m2
    fxd = xr.DataArray(np.full((2, 2, 3), 3e-9), dims=("time", "y", "x"), coords={"time": _time(2)})
    fxu = xr.DataArray(np.full((2, 2, 3), 1e-9), dims=("time", "y", "x"), coords={"time": _time(2)})
    ds = xr.Dataset({"co2fxd": fxd, "co2fxu": fxu})
    out = ts.flux_series(ds, "co2fxn", parea)
    expected = (2e-9 * 12) * v.FLUX_TS_VARS["co2fxd"].scale
    assert out.values == pytest.approx([expected, expected])
    assert out["year"].values.tolist() == [1, 2]
    assert out.attrs["units"] == "Pg C yr-1"


def test_global_mean_series_scales_to_mmol():
    parea = _grid()
    o2 = xr.DataArray(np.full((2, 1, 2, 3), 0.25), dims=("time", "depth", "y", "x"),
                      coords={"time": _time(2)})
    bnds = xr.DataArray([[0.0, 10.0]], dims=("depth", "bounds"))
    ds = xr.Dataset({"o2lvl": o2, "depth_bnds": bnds})
    out = ts.global_mean_series(ds, "o2", parea, offset=100)
    assert out.values == pytest.approx([250.0, 250.0])
    assert out["year"].values.tolist() == [101, 102]


def test_global_mean_series_weights_levels_by_thickness_and_zmax():
    parea = _grid()
    o2 = xr.DataArray(np.zeros((1, 2, 2, 3)), dims=("time", "depth", "y", "x"), coords={"time": _time(1)})
    o2[:, 0] = 1.0
    o2[:, 1] = 3.0
    bnds = xr.DataArray([[0.0, 50.0], [50.0, 150.0]], dims=("depth", "bounds"))
    ds = xr.Dataset({"o2lvl": o2, "depth_bnds": bnds})
    full = ts.global_mean_series(ds, "o2", parea)
    top = ts.global_mean_series(ds, "o2", parea, zmax=100.0)
    assert full.item() == pytest.approx((1 * 50 + 3 * 100) / 150 * 1e3)
    assert top.item() == pytest.approx((1 * 50 + 3 * 50) / 100 * 1e3)


def test_drift():
    s = xr.DataArray([1.0, 2.0, 3.0], dims="year", coords={"year": [1, 2, 3]})
    assert ts.drift(s) == pytest.approx(1.0)
