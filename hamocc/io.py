"""Open HAMOCC history files written by NorESM (BLOM-HAMOCC).

File names follow the legacy HAMOCC_DIAG convention (not yet verified on
NorESM3 output):
    {caseid}.blom.hbgcy.{YYYY}.nc       annual
    {caseid}.blom.hbgcm.{YYYY}-{MM}.nc  monthly
"""
import re
from pathlib import Path

import xarray as xr
from xarray.coding.times import CFDatetimeCoder

FILE_TAGS = {"ann": "hbgcy", "mon": "hbgcm"}

_YEAR_RE = re.compile(r"\.(\d{4})(?:-\d{2})?\.nc$")


def available_years(input_root, caseid, tag="hbgcy", component="blom"):
    """Sorted years for which `tag` history files exist (detected from the file names)."""
    hist = Path(input_root) / caseid / "ocn" / "hist"
    years = set()
    for f in hist.glob(f"{caseid}.{component}.{tag}.[0-9][0-9][0-9][0-9]*.nc"):
        m = _YEAR_RE.search(f.name)
        if m:
            years.add(int(m.group(1)))
    return sorted(years)


def period(case, kind="climo"):
    """(first, last) year to average over for `kind` = 'climo' (maps, sections, cycles) or 'ts' (time series).

    Reads `<kind>_year_start` / `<kind>_year_end` from the case settings; each defaults to the case's
    `year_start` / `year_end`, so a recipe without them behaves as before.
    """
    if kind not in ("climo", "ts"):
        raise ValueError(f"kind must be 'climo' or 'ts', not {kind!r}")
    ys = case.get(f"{kind}_year_start", case["year_start"])
    ye = case.get(f"{kind}_year_end", case["year_end"])
    if ye < ys:
        raise ValueError(f"{kind}: year_end {ye} is before year_start {ys}")
    return ys, ye


def history_files(input_root, caseid, tag, year_start, year_end, component="blom"):
    """Return the sorted history files for `tag` between the two years (inclusive)."""
    hist = Path(input_root) / caseid / "ocn" / "hist"
    files = []
    for year in range(year_start, year_end + 1):
        pattern = f"{caseid}.{component}.{tag}.{year:04d}*.nc"
        files.extend(sorted(hist.glob(pattern)))
    if not files:
        raise FileNotFoundError(f"No {tag} files for {caseid} in {hist}, years {year_start}-{year_end}")
    return files


def open_available(files, variables=None, **kwargs):
    """Open history files keeping the `variables` that are present: returns (dataset, sorted list of missing names)."""
    ds = xr.open_mfdataset(
        files,
        combine="by_coords",
        decode_times=CFDatetimeCoder(use_cftime=True),
        data_vars="minimal",
        coords="minimal",
        compat="override",
        **kwargs,
    )
    if variables is not None:
        keep = [v for v in variables if v in ds]
        missing = sorted(set(variables) - set(keep))
        ds = ds[keep]
    else:
        missing = []
    return ds, missing


def open_history(files, variables=None, strict=True, **kwargs):
    """Open history files as one dataset, keeping `variables` plus grid/weight fields.

    Strict (default): raise KeyError if any of `variables` is absent. With `strict=False` the
    absent ones are dropped silently; use `open_available` to also get their names.
    """
    ds, missing = open_available(files, variables, **kwargs)
    if missing and strict:
        raise KeyError(f"Variables not in history files: {missing}")
    return ds


def usable(ds, names, needs):
    """Split `names` into those whose inputs are all in `ds` and the rest.

    `needs(name)` lists the history variables a name is built from (e.g. `climatology.history_names`).
    Returns (usable names in order, {skipped name: [missing history variables]}).
    """
    ok, skipped = [], {}
    for name in names:
        absent = [h for h in needs(name) if h not in ds]
        if absent:
            skipped[name] = absent
        else:
            ok.append(name)
    return ok, skipped


def report_skipped(skipped, what="Skipped"):
    """Print one line per skipped name, with the history variables it lacks."""
    for name, absent in skipped.items():
        print(f"{what} {name}: not in the history files ({', '.join(absent)})")
