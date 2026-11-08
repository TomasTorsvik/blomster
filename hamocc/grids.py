"""Model grids (legacy `determine_grid_type.sh` / `grid_files/<grid>/grid.nc`).

`experiment.grid` in the recipe names the grid. `grid_file(cfg)` returns its file: an explicit
`grids.<name>.grid_file` entry if there is one, else `<grids.root>/<name>/grid.nc` (the legacy
HAMOCC_DIAG layout). Every grid file holds the p-grid fields read by `blomster.grid.load` and
`timeseries.load_parea`.
"""
from pathlib import Path

# name: (ny, nx) of the p-grid, as in the legacy grid-size table. The legacy
# `grid_files/g1xv6` directory is a duplicate of `gx1v6`.
KNOWN_GRIDS = {
    "gx3v7": (116, 100),
    "gx1v5": (384, 320),
    "gx1v6": (384, 320),
    "tnx2v1": (193, 180),
    "tnx1.5v1": (257, 240),
    "tnx1v1": (385, 360),
    "tnx1v2": (385, 360),
    "tnx1v3": (385, 360),
    "tnx1v4": (385, 360),
    "tnx1v1_lgm": (385, 360),
    "tnx1v1_lgm2": (385, 360),
    "tnx1v1_mis3": (385, 360),
    "tnx1v1_PlioMIP2": (385, 360),
    "tnx0.5v1": (641, 720),
    "tnx0.25v1": (1153, 1440),
    "tnx0.25v3": (1153, 1440),
    "tnx0.25v4": (1153, 1440),
    "tnx0.083v1": (3457, 4320),
}


def grid_file(cfg, name=None):
    """Path of the grid file of grid `name` (default `cfg['experiment']['grid']`)."""
    name = name or cfg["experiment"]["grid"]
    grids = cfg.get("grids") or {}
    entry = grids.get(name)
    if isinstance(entry, dict) and entry.get("grid_file"):
        return str(entry["grid_file"])
    if name not in KNOWN_GRIDS:
        raise KeyError(f"Unknown grid {name!r}: give grids.{name}.grid_file in the recipe "
                       f"or use one of {sorted(KNOWN_GRIDS)}")
    if not grids.get("root"):
        raise KeyError(f"No grids.{name}.grid_file and no grids.root in the recipe")
    return str(Path(grids["root"]) / name / "grid.nc")


def candidates(shape):
    """Known grids with p-grid shape `shape` = (ny, nx); the versions of one size share a shape."""
    return [n for n, s in KNOWN_GRIDS.items() if s == tuple(shape)]
