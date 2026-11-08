import matplotlib

matplotlib.use("Agg")
import numpy as np
import pytest
import xarray as xr

from hamocc import climatology, plots


def _field(values, lat=None):
    ny, nx = values.shape
    return xr.DataArray(values, dims=("y", "x"), name="v", attrs={"units": "u", "long_name": "V"})


def test_stats_constant_bias_and_rmse():
    obs = _field(np.arange(12.0).reshape(3, 4))
    s = climatology.stats(obs + 2.0, obs, xr.ones_like(obs))
    assert s["bias"] == pytest.approx(2.0)
    assert s["rmse"] == pytest.approx(2.0)
    assert s["model_mean"] - s["obs_mean"] == pytest.approx(2.0)
    assert s["n"] == 12


def test_stats_area_weighting_and_common_cells():
    obs = _field(np.zeros((2, 2)))
    model = _field(np.array([[1.0, 3.0], [np.nan, 100.0]]))
    obs[1, 1] = np.nan  # last cell valid only in model
    area = _field(np.array([[1.0, 3.0], [5.0, 5.0]]))
    s = climatology.stats(model, obs, area)
    assert s["n"] == 2
    assert s["model_mean"] == pytest.approx((1 * 1 + 3 * 3) / 4)
    assert s["bias"] == pytest.approx(2.5)
    assert s["rmse"] == pytest.approx(np.sqrt((1 * 1 + 9 * 3) / 4))


def test_stats_no_common_cells_is_nan():
    a = _field(np.full((2, 2), np.nan))
    s = climatology.stats(a, a + 1.0)
    assert s["n"] == 0 and np.isnan(s["rmse"])


def test_section_stats_use_coslat_weights():
    lat = np.array([0.0, 60.0])
    obs = xr.DataArray(np.zeros((2, 3)), dims=("lat", "depth"), coords={"lat": lat, "depth": [0.0, 10.0, 20.0]})
    model = obs.copy()
    model[0] = 1.0  # equator bias 1, 60N bias 0; weights 1 and 0.5
    s = climatology.stats(model, obs, climatology.section_area(model))
    assert s["bias"] == pytest.approx(1.0 / 1.5)
    assert s["rmse"] == pytest.approx(np.sqrt(1.0 / 1.5))


def test_zonal_panels_title_shows_numbers():
    lat = np.linspace(-80, 80, 9)
    depth = np.array([0.0, 100.0, 500.0, 1000.0])
    obs = xr.DataArray(np.ones((4, 9)) * np.arange(4)[:, None], dims=("depth", "lat"),
                       coords={"lat": lat, "depth": depth}, name="v", attrs={"units": "u"})
    model = (obs + 0.5).assign_attrs(units="u")
    fig = plots.zonal_panels(model, obs)
    title = fig.axes[2].get_title()
    assert "bias 0.5" in title and "RMSE 0.5" in title
    assert plots.zonal_panels(model, obs, area=False).axes[2].get_title() == "Model - obs"


def test_map_panels_title_shows_numbers_only_with_area():
    pytest.importorskip("cartopy")
    ny, nx = 6, 8
    lon, lat = np.meshgrid(np.arange(nx) * 45.0 - 180, np.linspace(-60, 60, ny))
    corners_lon = np.arange(nx + 1) * 45.0 - 202.5
    corners_lat = np.linspace(-70, 70, ny + 1)
    clon, clat = np.meshgrid(corners_lon, corners_lat)
    rng = np.random.default_rng(0)
    obs = xr.DataArray(rng.random((ny, nx)), dims=("y", "x"), name="v", attrs={"units": "u", "long_name": "V"})
    model = (obs + 3.0).assign_attrs(obs.attrs)
    area = xr.DataArray(np.ones((ny, nx)), dims=("y", "x"))
    fig = plots.map_panels(clon, clat, model, obs, area=area)
    assert "bias 3" in fig.axes[2].get_title() and "RMSE 3" in fig.axes[2].get_title()
    assert plots.map_panels(clon, clat, model, obs).axes[2].get_title() == "Model - obs"
