import numpy as np
import pytest
import xarray as xr

from hamocc import climatology as clim
from hamocc import variables as v


def _ds(vals_by_name, nt=2, nz=3):
    depth = [0.0, 100.0, 500.0]
    data = {}
    for name, val in vals_by_name.items():
        dims = ("time", "depth", "y", "x") if name.endswith(
            "lvl") else ("time", "y", "x")
        shape = (nt, nz, 2, 2) if name.endswith("lvl") else (nt, 2, 2)
        arr = xr.DataArray(np.full(shape, val, dtype=float), dims=dims)
        data[name] = arr
    return xr.Dataset(data, coords={"depth": depth})


def test_level_variable_scaled_to_mmol():
    out = clim.annual_mean_map(_ds({"o2lvl": 0.25}), "o2lvl", depth=100.0)
    assert out.dims == ("y", "x")
    assert float(out[0, 0]) == pytest.approx(250.0)
    assert out.attrs["units"] == "mmol m-3"


def test_aou_is_saturation_minus_o2():
    ds = _ds({"o2lvl": 0.2, "p_o2lvl": 0.3})
    out = clim.annual_mean_map(ds, "aoulvl", depth=0.0)
    assert float(out[0, 0]) == pytest.approx(100.0)


def test_co2_net_uses_molar_scale():
    out = clim.annual_mean_map(_ds({"co2fxd": 3e-9, "co2fxu": 1e-9}), "co2fxn")
    assert float(out[0, 0]) == pytest.approx(2e-9 * v.CO2_NET.scale)


def test_depth_far_from_any_level_raises():
    with pytest.raises(ValueError):
        clim.annual_mean_map(_ds({"o2lvl": 0.25}), "o2lvl", depth=3000.0)


def test_unknown_variable_raises():
    with pytest.raises(KeyError):
        clim.annual_mean_map(_ds({"foo": 1.0}), "foo")


def test_difference_keeps_units():
    a = xr.DataArray([2.0], dims="x", name="o2lvl",
                     attrs={"units": "mmol m-3"})
    b = xr.DataArray([0.5], dims="x")
    out = clim.difference(a, b)
    assert float(out[0]) == 1.5 and out.attrs["units"] == "mmol m-3"


def test_history_names():
    assert clim.history_names("aoulvl") == ["p_o2lvl", "o2lvl"]
