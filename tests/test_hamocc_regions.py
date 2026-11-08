import pathlib
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
    da = xr.DataArray(np.full((180, 360), 2.0), dims=(
        "lat", "lon"), coords={"lat": g["lat"], "lon": g["lon"]})
    da[0, :] = np.nan
    assert float(regions.weighted_mean(
        da, xr.ones_like(da, dtype=bool))) == pytest.approx(2.0)


def test_obs_cycle_regional_mean_file():
    da = xr.DataArray(np.arange(12.0).reshape(
        12, 1, 1), dims=("time", "lat", "lon"))
    out = regions.obs_cycle(da)
    assert out.dims == (
        "month",) and out["month"].values.tolist() == list(range(1, 13))


def test_obs_cycle_needs_twelve_steps():
    with pytest.raises(ValueError):
        regions.obs_cycle(xr.DataArray(np.zeros(5), dims="time"))


def test_monthly_cycle_ppint_and_months():
    import cftime
    times = [cftime.DatetimeNoLeap(y, m, 15)
             for y in (1, 2) for m in range(1, 13)]
    ppint = xr.DataArray(np.full((24, 2, 2), 2.0), dims=(
        "time", "y", "x"), coords={"time": times})
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
    out = obs.load_obs_region(
        {"file": "o_{region}.nc", "var": "o_an", "scale": 2.0}, tmp_path, "NATL")
    assert "depth" not in out.dims
    assert out.sizes["time"] == 12
    assert float(out.isel(time=0).squeeze()) == 0.0
    assert float(out.isel(time=1).squeeze()) == 4.0


# ---- per-variable masks --------------------------------------------------

def _write_mask(path, arr, monthly=False, depth=False, lon=None):
    """Write a legacy-style mask file (lon -179.5..179.5, optional time/depth axes)."""
    lon = np.arange(-179.5, 180, 1.0) if lon is None else lon
    lat = np.arange(-89.5, 90, 1.0)
    data = np.broadcast_to(arr, (12,) + arr.shape).copy() if monthly else arr
    dims = ("time", "lat", "lon") if monthly else ("lat", "lon")
    if depth:
        data = data[:, None] if monthly else data[None]
        dims = (dims[0], "depth") + dims[1:] if monthly else ("depth",) + dims
    coords = {"lat": lat, "lon": lon}
    if monthly:
        coords["time"] = np.arange(12.0)
    if depth:
        coords["depth"] = [0.0]
    xr.Dataset({"mask": (dims, data.astype(float))},
               coords=coords).to_netcdf(path)


def test_load_variable_mask_normalises(tmp_path):
    arr = np.zeros((180, 360))
    arr[100, 0] = 1  # lon -179.5
    _write_mask(tmp_path / "m.nc", arr, monthly=True, depth=True)
    m = regions.load_variable_mask(tmp_path / "m.nc")
    assert m.dims == ("month", "lat", "lon") and m.dtype == bool
    assert float(m["lon"].min()) == 0.5 and float(m["lon"].max()) == 359.5
    assert bool(m.sel(lat=10.5, lon=180.5, month=3))
    assert int(m.isel(month=0).sum()) == 1


def test_combine_masks_is_intersection():
    g = zonal.target_grid()
    reg = xr.DataArray(np.zeros((180, 360), bool), dims=(
        "lat", "lon"), coords={"lat": g["lat"], "lon": g["lon"]})
    reg[:, :100] = True
    var = reg.copy(data=np.zeros((180, 360), bool))
    var[:, 50:150] = True
    out = regions.combine_masks(reg, var)
    assert int(out.sum()) == 180 * 50


def _setup(tmp_path, region_cells, var_cells):
    g = zonal.target_grid()
    glb, _ = _basin(lambda la, lo: np.ones_like(la))
    masks = {"atl": glb, "glb": glb, "pac": glb * 0, "ind": glb * 0}
    natl = regions.region_mask(masks, "NATL", g)
    d = tmp_path / "pco2"
    d.mkdir()
    if region_cells is not None:
        _write_mask(d / "region_mask_1x1_NATL.nc", region_cells, monthly=True)
    if var_cells is not None:
        _write_mask(d / "pco2_mask_1x1.nc", var_cells, monthly=True)
    spec = {"root": str(tmp_path), "region_file": "{var}/region_mask_1x1_{region}.nc",
            "var_file": "{var}/{var}_mask_1x1.nc", "var": "mask", "alias": {"alias_var": "pco2"}}
    return natl, spec


def test_variable_region_mask_prefers_region_file(tmp_path):
    cells = np.zeros((180, 360))
    cells[130:140, 10:20] = 1   # lat 40.5-49.5, lon -170..-160
    natl, spec = _setup(tmp_path, cells, np.ones((180, 360)))
    out = regions.variable_region_mask("pco2", "NATL", natl, spec)
    assert out.dims == ("month", "lat", "lon")
    # the region file's count, not the generic one
    assert int(out.isel(month=0).sum()) == 100
    assert int(natl.sum()) != 100
    alias = regions.variable_region_mask("alias_var", "NATL", natl, spec)
    assert int(alias.isel(month=5).sum()) == 100


def test_variable_region_mask_falls_back_to_variable_mask(tmp_path):
    var = np.ones((180, 360))
    # lon -179.5..-0.5 invalid -> 180.5..359.5 invalid
    var[:, :180] = 0
    natl, spec = _setup(tmp_path, None, var)
    out = regions.variable_region_mask("pco2", "NATL", natl, spec)
    assert int(out.isel(month=0).sum()) == int(
        (natl & (natl["lon"] < 180)).sum())
    # no files at all, or no spec: generic region mask
    assert regions.variable_region_mask("pco2", "NATL", natl, None) is natl
    (tmp_path / "empty").mkdir()
    natl2, spec2 = _setup(tmp_path / "empty", None, None)
    assert regions.variable_region_mask(
        "pco2", "NATL", natl2, spec2).equals(natl2)


def test_model_and_obs_cycles_share_monthly_mask(tmp_path):
    g = zonal.target_grid()
    mask = xr.DataArray(np.zeros((12, 180, 360), bool), dims=("month", "lat", "lon"),
                        coords={"month": np.arange(1, 13), "lat": g["lat"], "lon": g["lon"]})
    mask[:, 100:110, 100:110] = True
    # January has fewer valid cells
    mask[0, 100:110, 100:105] = False
    field = np.full((12, 180, 360), 5.0)
    field[:, 100:110, 105:110] = 7.0
    da = xr.DataArray(field, dims=("month", "lat", "lon"),
                      coords={"month": np.arange(1, 13), "lat": g["lat"], "lon": g["lon"]})
    model = regions.model_cycle(da, mask)
    assert float(model.sel(month=1)) == pytest.approx(
        7.0)    # only the 7.0 cells are valid
    assert float(model.sel(month=2)) == pytest.approx(6.0, abs=0.01)
    obs_da = da.rename(month="time").assign_coords(lon=da["lon"].where(
        # obs-style: time axis, lon -180..180
        da["lon"] < 180, da["lon"] - 360))
    obs = regions.obs_cycle(obs_da, mask)
    np.testing.assert_allclose(obs.values, model.values)
    assert obs.dims == ("month",)


_LEGACY = pathlib.Path(
    "/scratch/data/noresm-diagnostics-data/HAMOCC_DIAG/grid_files/1x1d")


@pytest.mark.skipif(not _LEGACY.exists(), reason="legacy HAMOCC_DIAG grid files not available")
@pytest.mark.parametrize("region", ["NATL", "IND"])
def test_real_masks_cell_counts(region):
    """Per-variable cell counts on the 1x1 target grid equal the legacy mask files' (read-only check)."""
    g = zonal.target_grid()
    glb = zonal.load_basin_mask(
        _LEGACY / "generic/region_mask_1x1_glb.nc", "mask")
    basins = {b: zonal.load_basin_mask(_LEGACY / f"generic/region_mask_1x1_{b}.nc", "mask")
              for b in ("atl", "ind", "pac")}
    basins["glb"] = glb
    gen = regions.region_mask(basins, region, g)
    spec = {"root": str(_LEGACY), "region_file": "{var}/region_mask_1x1_{region}.nc",
            "var_file": "{var}/{var}_mask_1x1.nc", "var": "mask", "alias": {"co2fxn": "co2fxd"}}
    for name in ("pco2", "co2fxn", "ppint", "srfo2", "srfsi", "srfpo4", "srfno3", "sst", "sss", "mld"):
        key = spec["alias"].get(name, name)
        with xr.open_dataset(_LEGACY / f"{key}/region_mask_1x1_{region}.nc", decode_times=False) as ds:
            ref = (ds["mask"].squeeze() > 0).sum(
                ["lat", "lon"]).values   # per month
        out = regions.variable_region_mask(name, region, gen, spec)
        np.testing.assert_array_equal(out.sum(["lat", "lon"]).values, ref)
        # fallback path (generic region AND variable mask) agrees for IND, where generic == legacy region
        if region == "IND":
            fb = regions.combine_masks(gen, regions.load_variable_mask(
                _LEGACY / f"{key}/{key}_mask_1x1.nc"))
            np.testing.assert_array_equal(fb.sum(["lat", "lon"]).values, ref)
