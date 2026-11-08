import pytest

from hamocc import io


def test_history_files_selects_years(tmp_path):
    hist = tmp_path / "case" / "ocn" / "hist"
    hist.mkdir(parents=True)
    for y in (1, 2, 3):
        (hist / f"case.blom.hbgcy.{y:04d}.nc").touch()
    files = io.history_files(tmp_path, "case", "hbgcy", 2, 3)
    assert [f.name for f in files] == [
        "case.blom.hbgcy.0002.nc", "case.blom.hbgcy.0003.nc"]


def test_history_files_monthly(tmp_path):
    hist = tmp_path / "case" / "ocn" / "hist"
    hist.mkdir(parents=True)
    for m in (1, 2):
        (hist / f"case.blom.hbgcm.0001-{m:02d}.nc").touch()
    assert len(io.history_files(tmp_path, "case", "hbgcm", 1, 1)) == 2


def test_history_files_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        io.history_files(tmp_path, "case", "hbgcy", 1, 1)


def _touch_years(tmp_path, names):
    hist = tmp_path / "case" / "ocn" / "hist"
    hist.mkdir(parents=True)
    for n in names:
        (hist / n).touch()


def test_available_years_annual_and_monthly(tmp_path):
    _touch_years(tmp_path, ["case.blom.hbgcy.0003.nc",
                            "case.blom.hbgcy.0001.nc",
                            "case.blom.hbgcy.i.0002.nc",
                            "case.blom.hbgcm.0001-01.nc",
                            "case.blom.hbgcm.0001-02.nc",
                            "case.blom.hbgcm.0004-01.nc"])
    assert io.available_years(tmp_path, "case", "hbgcy") == [1, 3]
    assert io.available_years(tmp_path, "case", "hbgcm") == [1, 4]


def test_available_years_no_files(tmp_path):
    assert io.available_years(tmp_path, "case") == []


def test_period_defaults_to_experiment_years():
    exp = {"year_start": 1, "year_end": 50}
    assert io.period(exp, "climo") == (1, 50)
    assert io.period(exp, "ts") == (1, 50)


def test_period_overrides_are_independent():
    exp = {"year_start": 1, "year_end": 50, "climo_year_start": 41,
           "climo_year_end": 50, "ts_year_end": 30}
    assert io.period(exp, "climo") == (41, 50)
    assert io.period(exp, "ts") == (1, 30)


def test_period_rejects_bad_input():
    with pytest.raises(ValueError):
        io.period({"year_start": 1, "year_end": 5,
                  "climo_year_start": 9}, "climo")
    with pytest.raises(ValueError):
        io.period({"year_start": 1, "year_end": 5}, "other")


def _write_case(tmp_path, variables):
    import numpy as np
    import xarray as xr
    hist = tmp_path / "case" / "ocn" / "hist"
    hist.mkdir(parents=True)
    ds = xr.Dataset({v: (("y", "x"), np.ones((2, 2))) for v in variables})
    ds.to_netcdf(hist / "case.blom.hbgcy.0001.nc")
    return io.history_files(tmp_path, "case", "hbgcy", 1, 1)


def test_open_available_returns_present_and_missing(tmp_path):
    files = _write_case(tmp_path, ["o2lvl", "ppint"])
    ds, missing = io.open_available(
        files, ["o2lvl", "ppint", "delta13clvl", "pp_tot"])
    assert sorted(ds.data_vars) == ["o2lvl", "ppint"]
    assert missing == ["delta13clvl", "pp_tot"]


def test_open_history_strict_by_default_and_lenient_on_request(tmp_path):
    files = _write_case(tmp_path, ["o2lvl"])
    with pytest.raises(KeyError, match="pp_tot"):
        io.open_history(files, ["o2lvl", "pp_tot"])
    assert list(io.open_history(
        files, ["o2lvl", "pp_tot"], strict=False).data_vars) == ["o2lvl"]


def test_usable_splits_names_and_lists_absent_inputs(tmp_path):
    from hamocc import climatology
    files = _write_case(tmp_path, ["o2lvl", "co2fxd", "co2fxu"])
    ds, _ = io.open_available(files)
    ok, skipped = io.usable(
        ds, ["o2lvl", "aoulvl", "co2fxn", "pco2"], climatology.history_names)
    assert ok == ["o2lvl", "co2fxn"]
    assert skipped == {"aoulvl": ["p_o2lvl"], "pco2": ["pco2"]}


def test_report_skipped_names_what_is_missing(capsys):
    io.report_skipped({"aoulvl": ["p_o2lvl"]})
    out = capsys.readouterr().out
    assert "aoulvl" in out and "p_o2lvl" in out
