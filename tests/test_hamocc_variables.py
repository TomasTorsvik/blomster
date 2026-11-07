import numpy as np
import pytest

from hamocc import variables as v


def test_co2_flux_pg_per_year():
    # 1e-12 kg C m-2 s-1 over 1 m2 -> 86400*365*1e-12*1e-12 Pg/yr scale check
    assert v.FLUX_TS_VARS["co2fxd"].scale == pytest.approx(86400 * 365 * 1e-12)


def test_co2_net_molar_scale():
    # kg C m-2 s-1 -> mol C m-2 yr-1 (1000 g/kg / 12 g/mol)
    flux = 1e-9
    assert flux * v.CO2_NET.scale == pytest.approx(flux * 86400 * 365 * 1000 / 12)


def test_aou_is_saturation_minus_o2():
    assert v.aou(np.array([0.2]), np.array([0.3]))[0] == pytest.approx(0.1)


def test_co2_net_sign():
    assert v.co2_net(3.0, 1.0) == 2.0


def test_regions_cover_expected_names():
    assert set(v.REGIONS) == {"ARC", "NATL", "NPAC", "TATL", "TPAC", "IND", "MSO", "HSO"}
    for _, lo, hi in v.REGIONS.values():
        assert lo < hi
