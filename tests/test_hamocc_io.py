import pytest

from hamocc import io


def test_history_files_selects_years(tmp_path):
    hist = tmp_path / "case" / "ocn" / "hist"
    hist.mkdir(parents=True)
    for y in (1, 2, 3):
        (hist / f"case.blom.hbgcy.{y:04d}.nc").touch()
    files = io.history_files(tmp_path, "case", "hbgcy", 2, 3)
    assert [f.name for f in files] == ["case.blom.hbgcy.0002.nc", "case.blom.hbgcy.0003.nc"]


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
    _touch_years(tmp_path, ["case.blom.hbgcy.0003.nc", "case.blom.hbgcy.0001.nc", "case.blom.hbgcy.i.0002.nc",
                            "case.blom.hbgcm.0001-01.nc", "case.blom.hbgcm.0001-02.nc", "case.blom.hbgcm.0004-01.nc"])
    assert io.available_years(tmp_path, "case", "hbgcy") == [1, 3]
    assert io.available_years(tmp_path, "case", "hbgcm") == [1, 4]


def test_available_years_no_files(tmp_path):
    assert io.available_years(tmp_path, "case") == []


def test_period_defaults_to_experiment_years():
    exp = {"year_start": 1, "year_end": 50}
    assert io.period(exp, "climo") == (1, 50)
    assert io.period(exp, "ts") == (1, 50)


def test_period_overrides_are_independent():
    exp = {"year_start": 1, "year_end": 50, "climo_year_start": 41, "climo_year_end": 50, "ts_year_end": 30}
    assert io.period(exp, "climo") == (41, 50)
    assert io.period(exp, "ts") == (1, 30)


def test_period_rejects_bad_input():
    with pytest.raises(ValueError):
        io.period({"year_start": 1, "year_end": 5, "climo_year_start": 9}, "climo")
    with pytest.raises(ValueError):
        io.period({"year_start": 1, "year_end": 5}, "other")
