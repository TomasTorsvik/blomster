import numpy as np
import pytest

from hamocc import variables as v


def test_co2_flux_pg_per_year():
    # 1e-12 kg C m-2 s-1 over 1 m2 -> 86400*365*1e-12*1e-12 Pg/yr scale check
    assert v.FLUX_TS_VARS["co2fxd"].scale == pytest.approx(86400 * 365 * 1e-12)


def test_co2_net_molar_scale():
    # kg C m-2 s-1 -> mol C m-2 yr-1 (1000 g/kg / 12 g/mol)
    flux = 1e-9
    assert flux * \
        v.CO2_NET.scale == pytest.approx(flux * 86400 * 365 * 1000 / 12)


def test_aou_is_saturation_minus_o2():
    assert v.aou(np.array([0.2]), np.array([0.3]))[0] == pytest.approx(0.1)


def test_co2_net_sign():
    assert v.co2_net(3.0, 1.0) == 2.0


def test_regions_cover_expected_names():
    assert set(v.REGIONS) == {"ARC", "NATL", "NPAC",
                              "TATL", "TPAC", "IND", "MSO", "HSO"}
    for _, lo, hi in v.REGIONS.values():
        assert lo < hi


def test_optional_variables_registered_with_obs():
    assert v.LEVEL_VARS["delta13clvl"].units == "permil" and v.LEVEL_VARS["delta13clvl"].scale == 1.0
    assert v.SURFACE_VARS["pp_tot"].scale == v.SURFACE_VARS["ppint"].scale
    assert v.FLUX_TS_VARS["pp_tot"].scale == v.FLUX_TS_VARS["ppint"].scale
    assert "pp_tot" in v.REGIONAL_VARS


def test_optional_variables_skipped_when_absent_and_plotted_when_present():
    import numpy as np
    import xarray as xr
    from hamocc import climatology as clim, io
    time = xr.cftime_range("0001-01-01", periods=1, freq="YS", calendar="noleap")
    base = xr.DataArray(np.full((1, 2, 2), 1e-8), dims=("time", "y", "x"), coords={"time": time})
    names = ["ppint", "pp_tot", "delta13clvl"]
    ok, skipped = io.usable(xr.Dataset({"ppint": base}), names, clim.history_names)
    assert ok == ["ppint"] and set(skipped) == {"pp_tot", "delta13clvl"}
    d13 = xr.DataArray(np.full((1, 2, 2, 2), 0.5), dims=("time", "depth", "y", "x"),
                       coords={"time": time, "depth": [0.0, 100.0]})
    ds = xr.Dataset({"ppint": base, "pp_tot": base, "delta13clvl": d13})
    ok, skipped = io.usable(ds, names, clim.history_names)
    assert ok == names and not skipped
    assert float(clim.annual_mean_map(ds, "delta13clvl", 100).mean()) == pytest.approx(0.5)
    pp = clim.annual_mean_map(ds, "pp_tot")
    assert pp.attrs["units"] == "mol C m-2 yr-1"
    assert float(pp.mean()) == pytest.approx(1e-8 * v.SEC_PER_YEAR)
