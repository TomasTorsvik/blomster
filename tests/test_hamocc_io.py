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
