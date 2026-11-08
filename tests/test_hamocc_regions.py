import numpy as np
import pytest
import xarray as xr

from hamocc import climatology as clim
from hamocc import regions, zonal


def _basin(value_fn):
    g = zonal.target_grid(1.0)
    lat, lon = np.meshgrid(g["lat"], g["lon"], indexing="ij")
    return xr.DataArray(value_fn(lat, lon).astype(float), dims=("lat", "lon"),
                        coords={"lat": g["lat"], "lon": g["lon"]}), g


def test_region_mask_uses_basin_and_latitude():
    atl, g = _basin(lambda la, lo: (lo > 280) | (lo < 20))
    glb, _ = _basin(lambda la, lo: np.ones_like(la))
    masks = {"atl": atl, "glb": glb, "pac": glb * 0, "ind": glb * 0}
    natl = regions.region_mask(masks, "NATL", g)
    assert bool(natl.sel(lat=40.5, lon=300.5))
    assert not bool(natl.sel(lat=40.5, lon=180.5))   # outside basin
    assert not bool(natl.sel(lat=10.5, lon=300.5))   # outside latitude band
    arc = regions.region_mask(masks, "ARC", g)
    assert bool(arc.sel(lat=80.5, lon=180.5))


def test_indian_region_excludes_gulf():
    ind, g = _basin(lambda la, lo: np.ones_like(la))
    masks = {"ind": ind, "glb": ind, "atl": ind, "pac": ind}
    m = regions.region_mask(masks, "IND", g)
    assert not bool(m.sel(lat=25.5, lon=50.5))
    assert bool(m.sel(lat=10.5, lon=50.5))


def test_weighted_mean_downweights_high_latitudes():
    g = zonal.target_grid(1.0)
    da = xr.DataArray(np.where(np.abs(g["lat"].values) < 45, 1.0, 3.0)[:, None] * np.ones(360),
                      dims=("lat", "lon"), coords={"lat": g["lat"], "lon": g["lon"]})
    mask = xr.ones_like(da, dtype=bool)
    out = float(regions.weighted_mean(da, mask))
    assert 1.0 < out < 2.0  # unweighted mean would be 2.0


def test_weighted_mean_ignores_nan_cells():
    g = zonal.target_grid(1.0)
    da = xr.DataArray(np.full((180, 360), 2.0), dims=("lat", "lon"), coords={"lat": g["lat"], "lon": g["lon"]})
    da[0, :] = np.nan
    assert float(regions.weighted_mean(da, xr.ones_like(da, dtype=bool))) == pytest.approx(2.0)


def test_obs_cycle_regional_mean_file():
    da = xr.DataArray(np.arange(12.0).reshape(12, 1, 1), dims=("time", "lat", "lon"))
    out = regions.obs_cycle(da)
    assert out.dims == ("month",) and out["month"].values.tolist() == list(range(1, 13))


def test_obs_cycle_needs_twelve_steps():
    with pytest.raises(ValueError):
        regions.obs_cycle(xr.DataArray(np.zeros(5), dims="time"))


def test_monthly_cycle_ppint_and_months():
    import cftime
    times = [cftime.DatetimeNoLeap(y, m, 15) for y in (1, 2) for m in range(1, 13)]
    ppint = xr.DataArray(np.full((24, 2, 2), 2.0), dims=("time", "y", "x"), coords={"time": times})
    out = clim.monthly_cycle(xr.Dataset({"ppint": ppint}), "ppint")
    assert out.sizes["month"] == 12
    assert float(out[0, 0, 0]) == pytest.approx(2.0 * 86400 * 365)
    assert clim.history_names("ppint", monthly=True) == ["ppint"]


def test_load_obs_region_selects_surface(tmp_path):
    import xarray as xr
    from hamocc import obs

    da = xr.DataArray(np.arange(24.0).reshape(12, 2, 1, 1) + np.array([0, 100.0]).reshape(1, 2, 1, 1),
                      dims=("time", "depth", "lat", "lon"),
                      coords={"depth": [0.0, 50.0]})
    da.to_dataset(name="o_an").to_netcdf(tmp_path / "o_NATL.nc")
    out = obs.load_obs_region({"file": "o_{region}.nc", "var": "o_an", "scale": 2.0}, tmp_path, "NATL")
    assert "depth" not in out.dims
    assert out.sizes["time"] == 12
    assert float(out.isel(time=0).squeeze()) == 0.0
    assert float(out.isel(time=1).squeeze()) == 4.0
