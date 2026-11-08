import numpy as np
import pytest
import xarray as xr

from hamocc import zonal


def _field(values, lats=(-0.5, 0.5), lons=(10.0, 20.0, 30.0, 40.0)):
    return xr.DataArray(values, dims=("lat", "lon"), coords={"lat": list(lats), "lon": list(lons)})


def test_target_grid_is_cell_centred():
    g = zonal.target_grid(1.0)
    assert g["lat"].values[0] == -89.5 and g["lat"].values[-1] == 89.5
    assert g["lon"].values[0] == 0.5 and g["lon"].values[-1] == 359.5


def test_zonal_mean_uses_only_basin_cells():
    da = _field([[1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0]])
    mask = _field([[0, 1, 1, 0], [0, 1, 1, 0]])
    out = zonal.zonal_mean(da, mask)
    assert out.values == pytest.approx([2.5, 2.5])


def test_zonal_mean_skips_nan():
    da = _field([[1.0, np.nan, 3.0, 5.0], [np.nan] * 4])
    mask = _field(np.ones((2, 4)))
    out = zonal.zonal_mean(da, mask)
    assert out.values[0] == pytest.approx(3.0)
    assert np.isnan(out.values[1])


def test_common_cells_masks_both():
    model = _field([[1.0, 2.0, 3.0, 4.0]] * 2)
    obs = _field([[1.0, np.nan, 3.0, np.nan]] * 2)
    m, o = zonal.common_cells(model, obs)
    assert np.isnan(m.values[0, 1]) and np.isnan(m.values[0, 3])
    assert m.values[0, 0] == 1.0


def test_basin_zonal_means_same_cells():
    model = _field([[10.0, 20.0, 30.0, 40.0]] * 2)
    obs = _field([[1.0, np.nan, 3.0, 4.0]] * 2)
    mask = _field(np.ones((2, 4)))
    zm, zo = zonal.basin_zonal_means(model, obs, mask)
    assert zm.values[0] == pytest.approx((10 + 30 + 40) / 3)
    assert zo.values[0] == pytest.approx((1 + 3 + 4) / 3)


def test_normalize_lon_wraps_and_sorts():
    da = xr.DataArray([1, 2, 3], dims="lon", coords={
                      "lon": [-90.0, 0.0, 90.0]})
    out = zonal.normalize_lon(da)
    assert out["lon"].values.tolist() == [0.0, 90.0, 270.0]
    assert out.values.tolist() == [2, 3, 1]


def test_on_target_grid_interpolates_depth():
    obs = xr.DataArray(np.arange(3.0).reshape(3, 1, 1) * np.ones((3, 180, 360)),
                       dims=("depth", "lat", "lon"),
                       coords={"depth": [0.0, 10.0, 20.0],
                               "lat": np.arange(-89.5, 90, 1.0), "lon": np.arange(0.5, 360, 1.0)})
    out = zonal.on_target_grid(obs, zonal.target_grid(
        1.0), depth=xr.DataArray([5.0, 15.0], dims="depth"))
    assert float(out.isel(lat=90, lon=100)[0]) == pytest.approx(0.5)
    assert float(out.isel(lat=90, lon=100)[1]) == pytest.approx(1.5)


def test_fold_rows_detected_and_regridder_takes_full_field():
    import numpy as np
    import xarray as xr

    from hamocc import zonal

    lon1, lat1 = np.meshgrid(np.arange(0.5, 360, 5.0) - 180, np.arange(-60, 85, 5.0))
    lat = np.vstack([lat1, lat1[-1:]])  # last row repeats the one below, like a tripolar fold
    lon = np.vstack([lon1, lon1[-1:]])
    assert zonal._n_fold_rows(lat, lon) == 1
    assert zonal._n_fold_rows(lat1, lon1) == 0
    regridder = zonal.make_regridder(lat, lon, res=5.0)
    out = regridder(xr.DataArray(np.ones(lat.shape), dims=("y", "x")), skipna=True, na_thres=1.0)
    assert out.shape[-2:] == (36, 72)
