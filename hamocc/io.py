"""Open HAMOCC history files written by NorESM (BLOM-HAMOCC).

File names follow the legacy HAMOCC_DIAG convention (not yet verified on
NorESM3 output):
    {caseid}.blom.hbgcy.{YYYY}.nc       annual
    {caseid}.blom.hbgcm.{YYYY}-{MM}.nc  monthly
"""
from pathlib import Path

import xarray as xr
from xarray.coding.times import CFDatetimeCoder

FILE_TAGS = {"ann": "hbgcy", "mon": "hbgcm"}


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


def open_history(files, variables=None, **kwargs):
    """Open history files as one dataset, keeping `variables` plus grid/weight fields."""
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
        if missing:
            raise KeyError(f"Variables not in history files: {missing}")
        ds = ds[keep]
    return ds
