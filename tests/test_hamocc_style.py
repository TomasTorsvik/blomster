import matplotlib

matplotlib.use("Agg")
import numpy as np
import pytest
import xarray as xr

from hamocc import colormaps, levels, plots
from hamocc import variables as v


def test_tables_are_sorted_and_cover_the_variables():
    for table in (levels.SURFACE_LEVELS, levels.DEPTH_MAP_LEVELS, levels.ZONAL_LEVELS):
        for name, (lev, diff) in table.items():
            assert list(lev) == sorted(lev) and list(diff) == sorted(diff), name
            assert len(lev) >= 18 and len(diff) >= 18 and min(diff) < 0 < max(diff), name
    assert set(v.LEVEL_VARS) == set(levels.DEPTH_MAP_LEVELS) == set(levels.ZONAL_LEVELS)
    for name in ("ppint", "epc100", "pco2", "co2fxn", "dmsflux"):
        assert name in levels.SURFACE_LEVELS
    # spot checks against the legacy NCL tables
    assert levels.SURFACE_LEVELS["pco2"][0][0] == 250 and levels.SURFACE_LEVELS["pco2"][1][-1] == 80
    assert levels.ZONAL_LEVELS["talklvl"][0][0] == 2.2 and levels.DEPTH_MAP_LEVELS["talklvl"][0][0] == 1.8


def test_fixed_levels_off_by_default_and_on_request():
    assert levels.fixed_levels("map", "pco2") == (None, None)
    assert levels.fixed_levels("map", "pco2", {"fixed_levels": False}) == (None, None)
    lev, diff = levels.fixed_levels("map", "pco2", {"fixed_levels": True})
    assert lev[0] == 250 and diff[0] == -80
    assert levels.fixed_levels("zonal", "po4lvl", {"fixed_levels": True})[0][0] == 0.2
    assert levels.fixed_levels("map", "pp_tot", {"fixed_levels": True}) == levels.fixed_levels(
        "map", "ppint", {"fixed_levels": True})
    assert levels.fixed_levels("map", "unknown", {"fixed_levels": True}) == (None, None)


def test_recipe_levels_win_over_the_legacy_table():
    cfg = {"fixed_levels": True, "levels": {"map": {"pco2": {"levels": [1, 2, 3]}}}}
    assert levels.fixed_levels("map", "pco2", cfg) == ([1, 2, 3], None)


def test_colormaps_legacy_and_matplotlib_names():
    assert colormaps.get_cmap(None).name == "viridis"
    assert colormaps.get_cmap("plasma").name == "plasma"
    for name in ("default", "blueyellowred"):
        cm = colormaps.get_cmap(name)
        assert cm.N == 256 and len(cm(0.5)) == 4
    # blueyellowred starts blue-ish and ends red-ish (legacy file: 49,36,100 ... red)
    cm = colormaps.get_cmap("blueyellowred")
    assert cm(0.0)[2] > cm(0.0)[0] and cm(1.0)[0] > cm(1.0)[2]
    with pytest.raises(KeyError):
        colormaps.get_cmap("no-such-map")


def _field(seed=0):
    rng = np.random.default_rng(seed)
    return xr.DataArray(rng.random((6, 8)) * 10, dims=("y", "x"), attrs={"long_name": "f", "units": "u"})


def _grid():
    lon, lat = np.meshgrid(np.linspace(0, 350, 8), np.linspace(-60, 60, 6))
    return lon, lat


def test_map_panels_use_fixed_levels_and_colormaps():
    lon, lat = _grid()
    fig = plots.map_panels(lon, lat, _field(0), _field(1), levels=[0, 2, 4, 6, 8, 10], diff_levels=[-4, -2, 2, 4],
                           cmap="blueyellowred", diff_cmap="bwr")
    norms = [c.norm for ax in fig.axes for c in ax.collections if hasattr(c, "norm")]
    boundaries = [list(n.boundaries) for n in norms if hasattr(n, "boundaries")]
    assert [0, 2, 4, 6, 8, 10] in boundaries and [-4, -2, 2, 4] in boundaries
    cmaps = {c.cmap.name for ax in fig.axes for c in ax.collections if hasattr(c, "cmap")}
    assert "legacy_blueyellowred" in cmaps and "bwr" in cmaps


def test_map_panels_default_style_is_unchanged():
    lon, lat = _grid()
    fig = plots.map_panels(lon, lat, _field(0), _field(1))
    cmaps = {c.cmap.name for ax in fig.axes for c in ax.collections if hasattr(c, "cmap")}
    assert cmaps == {"viridis", "RdBu_r"}


def test_zonal_panels_use_fixed_levels():
    zm = xr.DataArray(np.random.default_rng(0).random((5, 9)) * 3, dims=("depth", "lat"),
                      coords={"depth": np.arange(5) * 100.0, "lat": np.linspace(-80, 80, 9)},
                      attrs={"long_name": "z", "units": "u"})
    fig = plots.zonal_panels(zm, zm * 1.1, levels=[0, 1, 2, 3], diff_levels=[-1, 0, 1], cmap="plasma")
    assert len(fig.axes) >= 3
