"""Control case (model-model comparison): settings helpers and the plot functions on synthetic data."""
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
import xarray as xr

from hamocc import climatology as clim
from hamocc import compare, plots, zonal


def _cfg(**cntl):
    cfg = {"experiment": {"caseid": "a", "input_root": "/in", "year_start": 1, "year_end": 5}}
    if cntl:
        cfg["experiment_cntl"] = cntl
    return cfg


def test_no_control_by_default():
    assert compare.control_case(_cfg()) is None
    assert compare.reference_kind(_cfg(), compare_obs=True) == "obs"
    assert compare.reference_kind(_cfg(), compare_obs=False) is None


def test_control_fills_input_root_and_wins_over_obs():
    cfg = _cfg(caseid="b", year_start=11, year_end=20)
    assert compare.control_case(cfg)["input_root"] == "/in"
    assert compare.reference_kind(cfg, compare_obs=True) == "control"
    assert compare.reference_kind(cfg, compare_obs=False) == "control"      # compare_obs=False + control works
    assert compare.reference_kind(cfg, compare_obs=True, compare_cntl=False) == "obs"
    cfg["experiment_cntl"]["input_root"] = "/other"
    assert compare.control_case(cfg)["input_root"] == "/other"


def test_incomplete_control_is_rejected():
    with pytest.raises(KeyError):
        compare.control_case(_cfg(caseid="b", year_start=1))
    with pytest.raises(ValueError):
        compare.control_case(_cfg(caseid="b", year_start=5, year_end=1))


def test_difference_label():
    a = xr.DataArray([3.0], dims="x", name="f", attrs={"long_name": "F", "units": "u"})
    d = clim.difference(a, a * 0 + 1, label="test - control")
    assert float(d[0]) == 2.0 and d.attrs["long_name"] == "F, test - control"
    assert clim.difference(a, a).attrs["long_name"] == "F, model - obs"


def test_obs_and_control_together_is_an_error():
    with pytest.raises(ValueError):
        plots.reference_labels(obs=1, control=2)


def _map(value):
    lat, lon = np.meshgrid(np.arange(-80, 81, 20.0), np.arange(0, 360, 30.0), indexing="ij")
    f = xr.DataArray(value + 0 * lat + lat / 100, dims=("y", "x"), name="f", attrs={"long_name": "F", "units": "u"})
    return lon, lat, f


def _titles(fig):
    return [ax.get_title() for ax in fig.axes if ax.get_title()]


def test_map_panels_control_replaces_obs():
    lon, lat, test = _map(2.0)
    _, _, cntl = _map(1.0)
    fig = plots.map_panels(lon, lat, test, control=cntl)
    assert _titles(fig) == ["Test", "Control", "Test - control"]
    plt.close(fig)
    fig = plots.map_panels(lon, lat, test, obs=cntl)                      # existing call keeps working
    assert _titles(fig) == ["Model", "Obs", "Model - obs"]
    plt.close(fig)
    fig = plots.map_panels(lon, lat, test)
    assert _titles(fig) == ["Model"]
    plt.close(fig)


def _section(value):
    lat, depth = np.arange(-80, 81, 20.0), np.array([0.0, 100.0, 500.0, 1000.0])
    data = value + 0 * lat[None, :] + 0 * depth[:, None] + depth[:, None] / 1000
    return xr.DataArray(data, dims=("depth", "lat"), coords={"depth": depth, "lat": lat}, name="f",
                        attrs={"long_name": "F", "units": "u"})


def test_zonal_panels_control_replaces_obs():
    fig = plots.zonal_panels(_section(2.0), zm_control=_section(1.0))
    assert _titles(fig) == ["Test", "Control", "Test - control"]
    plt.close(fig)
    fig = plots.zonal_panels(_section(2.0), _section(1.0))
    assert _titles(fig) == ["Model", "Obs", "Model - obs"]
    plt.close(fig)


def test_zonal_means_of_two_cases_use_common_cells():
    g = zonal.target_grid(10.0)
    mk = lambda v: xr.DataArray(np.full((18, 36), v), dims=("lat", "lon"), coords={"lat": g["lat"], "lon": g["lon"]})
    test, cntl = mk(2.0), mk(1.0)
    cntl[:, :18] = np.nan
    mask = mk(1.0)
    zt, zc = zonal.basin_zonal_means(test, cntl, mask)
    assert float(zt[0]) == 2.0 and float(zc[0]) == 1.0
    assert float(zt[0] - zc[0]) == 1.0


def test_cycle_panels_control_replaces_obs():
    month = np.arange(1, 13)
    mk = lambda v: {"NATL": xr.DataArray(v + np.sin(month), dims="month", coords={"month": month}, name="f",
                                         attrs={"long_name": "F", "units": "u"})}
    fig = plots.cycle_panels(mk(2.0), control=mk(1.0))
    lines = fig.axes[0].get_lines()
    assert [ln.get_label() for ln in lines] == ["Test", "Control"]
    assert lines[0].get_ydata().mean() - lines[1].get_ydata().mean() == pytest.approx(1.0)
    plt.close(fig)
    fig = plots.cycle_panels(mk(2.0), mk(1.0))
    assert [ln.get_label() for ln in fig.axes[0].get_lines()] == ["Model", "Obs"]
    plt.close(fig)
    plots.cycle_panels(mk(2.0))
    plt.close("all")


def test_identical_cases_give_zero_difference_panels():
    lon, lat, test = _map(2.0)
    fig = plots.map_panels(lon, lat, test, control=test.copy())
    assert _titles(fig) == ["Test", "Control", "Test - control"]
    plt.close(fig)
    fig = plots.zonal_panels(_section(2.0), zm_control=_section(2.0))
    assert len(_titles(fig)) == 3
    plt.close(fig)
