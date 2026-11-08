import pathlib

import numpy as np
import pytest
import xarray as xr

from blomster import grid
from hamocc import grids, timeseries

_LEGACY = pathlib.Path("/scratch/data/noresm-diagnostics-data/HAMOCC_DIAG/grid_files")


def _write_grid(path, ny, nx):
    """A minimal BLOM grid file: regular lat/lon with 4 corners per cell (BLOM corner order)."""
    lat1 = np.linspace(-80, 80, ny)
    lon1 = np.linspace(-179, 179, nx)
    lat, lon = np.meshgrid(lat1, lon1, indexing="ij")
    dy, dx = 160 / ny, 358 / nx
    corner_lat = np.stack([lat - dy / 2, lat - dy / 2, lat + dy / 2, lat + dy / 2])
    corner_lon = np.stack([lon - dx / 2, lon + dx / 2, lon + dx / 2, lon - dx / 2])
    dims = ("y", "x")
    xr.Dataset({
        "plat": (dims, lat), "plon": (dims, lon),
        "pclat": (("nv",) + dims, corner_lat), "pclon": (("nv",) + dims, corner_lon),
        "pmask": (dims, np.ones((ny, nx))), "pdepth": (dims, np.full((ny, nx), 4000.0)),
        "parea": (dims, np.full((ny, nx), 5.1e14 / (ny * nx))),
    }).to_netcdf(path)


@pytest.mark.parametrize("name", ["tnx1v4", "gx3v7"])
def test_grid_load_and_parea_on_tnx_and_non_tnx_shapes(tmp_path, name):
    ny, nx = grids.KNOWN_GRIDS[name]
    f = tmp_path / name / "grid.nc"
    f.parent.mkdir()
    _write_grid(f, ny, nx)
    lat, lon, depth, clat, clon, mask = grid.load(f)
    assert lat.shape == (ny, nx) and clat.shape == (ny + 1, nx + 1)
    area = timeseries.load_parea(f)
    assert area.shape == (ny, nx) and float(area.sum()) == pytest.approx(5.1e14)


def test_grid_file_default_layout_and_override(tmp_path):
    cfg = {"experiment": {"grid": "gx1v6"}, "grids": {"root": str(tmp_path)}}
    assert grids.grid_file(cfg) == str(tmp_path / "gx1v6" / "grid.nc")
    cfg["grids"]["gx1v6"] = {"grid_file": "/elsewhere/grid.nc"}
    assert grids.grid_file(cfg) == "/elsewhere/grid.nc"


def test_grid_file_errors():
    with pytest.raises(KeyError, match="Unknown grid"):
        grids.grid_file({"experiment": {"grid": "nope"}, "grids": {"root": "/x"}})
    with pytest.raises(KeyError, match="grids.root"):
        grids.grid_file({"experiment": {"grid": "tnx1v4"}, "grids": {}})
    # an unknown grid is fine when its file is given explicitly
    assert grids.grid_file({"experiment": {"grid": "mine"}, "grids": {"mine": {"grid_file": "g.nc"}}}) == "g.nc"


def test_candidates_by_shape():
    assert "gx1v6" in grids.candidates((384, 320)) and "tnx1v4" not in grids.candidates((384, 320))
    assert {"tnx1v1", "tnx1v4"} <= set(grids.candidates((385, 360)))
    assert grids.candidates((1, 1)) == []


@pytest.mark.skipif(not _LEGACY.exists(), reason="legacy HAMOCC_DIAG grid files not available")
@pytest.mark.parametrize("name", sorted(grids.KNOWN_GRIDS))
def test_every_legacy_grid_loads(name):
    """Read-only: grid.load and load_parea work on each legacy grid file, with the registered shape."""
    f = grids.grid_file({"experiment": {"grid": name}, "grids": {"root": str(_LEGACY)}})
    lat, lon, _, clat, clon, mask = grid.load(f)
    ny, nx = grids.KNOWN_GRIDS[name]
    assert lat.shape == (ny, nx) and clat.shape == (ny + 1, nx + 1) and clon.shape == clat.shape
    assert timeseries.load_parea(f).shape == (ny, nx)
