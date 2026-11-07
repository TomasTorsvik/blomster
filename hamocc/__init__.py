# hamocc/__init__.py
"""HAMOCC (ocean biogeochemistry) diagnostics, separate from the BLOM diagnostics."""

from . import climatology, io, obs, plots, regions, timeseries, variables, zonal

__all__ = ["climatology", "io", "obs", "plots", "regions", "timeseries", "variables", "zonal"]
