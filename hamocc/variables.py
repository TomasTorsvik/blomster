"""Registry of HAMOCC variables, unit conversions and derived fields.

Scale factors are transcribed from the legacy NCL/shell diagnostics
(NorESM-Diagnostics/packages/HAMOCC_DIAG: functions_*.ncl, plot_*.ncl,
compute_climo_means.sh, compute_ann_time_series.sh).
"""
from dataclasses import dataclass

SEC_PER_YEAR = 86400 * 365


@dataclass(frozen=True)
class Var:
    """A plottable quantity: model variable name, display units and scale factor."""
    name: str
    long_name: str
    units: str
    scale: float = 1.0
    obs: str = ""  # key into the recipe `datasets:` section, empty if none


# 3-D fields on fixed z-levels (history variables carry the `lvl` suffix)
LEVEL_VARS = {
    "o2lvl": Var("o2lvl", "Dissolved oxygen", "mmol m-3", 1e3, "WOA13"),
    "aoulvl": Var("aoulvl", "Apparent oxygen utilisation", "mmol m-3", 1e3, "WOA13"),
    "silvl": Var("silvl", "Silicate", "mmol m-3", 1e3, "WOA13"),
    "po4lvl": Var("po4lvl", "Phosphate", "mmol m-3", 1e3, "WOA13"),
    "no3lvl": Var("no3lvl", "Nitrate", "mmol m-3", 1e3, "WOA13"),
    "dissiclvl": Var("dissiclvl", "Dissolved inorganic carbon", "mol m-3", 1.0, "GLODAPv2"),
    "talklvl": Var("talklvl", "Total alkalinity", "eq m-3", 1.0, "GLODAPv2"),
    "delta13clvl": Var("delta13clvl", "delta13C of DIC", "permil", 1.0, "Eide2017"),
}

# 2-D surface fields (annual climatology)
SURFACE_VARS = {
    "pp_tot": Var("pp_tot", "Primary production (vertically integrated)", "mol C m-2 yr-1", SEC_PER_YEAR, "MODIS"),
    "ppint": Var("ppint", "Primary production (integrated)", "mol C m-2 yr-1", SEC_PER_YEAR, "MODIS"),
    "epc100": Var("epc100", "POC export at 100 m", "mol C m-2 yr-1", SEC_PER_YEAR),
    "pco2": Var("pco2", "Surface pCO2", "uatm", 1.0, "Landschuetzer2015"),
    "dmsflux": Var("dmsflux", "DMS flux", "pmol m-2 s-1", 1e12),
}

# CO2 flux: net = (co2fxd - co2fxu), kg C m-2 s-1 -> mol C m-2 yr-1
CO2_NET = Var("co2fxn", "Net air-sea CO2 flux (into ocean)", "mol C m-2 yr-1",
              SEC_PER_YEAR * 1000 / 12, "Landschuetzer2015")

# Surface concentrations used for regional monthly cycles
MONTHLY_VARS = {
    "srfo2": Var("srfo2", "Surface oxygen", "mmol m-3", 1e3, "WOA13"),
    "srfsi": Var("srfsi", "Surface silicate", "mmol m-3", 1e3, "WOA13"),
    "srfpo4": Var("srfpo4", "Surface phosphate", "mmol m-3", 1e3, "WOA13"),
    "srfno3": Var("srfno3", "Surface nitrate", "mmol m-3", 1e3, "WOA13"),
}

# Global volume-mean concentrations for time series
CONC_TS_VARS = {
    "o2": Var("o2", "Oxygen", "mmol m-3", 1e3),
    "si": Var("si", "Silicate", "mmol m-3", 1e3),
    "po4": Var("po4", "Phosphate", "mmol m-3", 1e3),
    "no3": Var("no3", "Nitrate", "mmol m-3", 1e3),
    "dissic": Var("dissic", "DIC", "mol m-3", 1.0),
    "talk": Var("talk", "Total alkalinity", "eq m-3", 1.0),
}

# Area-integrated annual fluxes for time series: scale takes kg-based
# fluxes in the history files (per m2 per s) to the printed unit per year.
FLUX_TS_VARS = {
    "co2fxd": Var("co2fxd", "CO2 flux into ocean (downward)", "Pg C yr-1", SEC_PER_YEAR * 1e-12),
    "co2fxu": Var("co2fxu", "CO2 flux out of ocean (upward)", "Pg C yr-1", SEC_PER_YEAR * 1e-12),
    "epc100": Var("epc100", "POC export at 100 m", "Pg C yr-1", 12.011 * SEC_PER_YEAR * 1e-15),
    "epcalc100": Var("epcalc100", "CaCO3 export at 100 m", "Pg C yr-1", 12 * SEC_PER_YEAR * 1e-15),
    "dmsflux": Var("dmsflux", "DMS flux", "Tg S yr-1", 62.13 * SEC_PER_YEAR * 1e-12),
    "pp_tot": Var("pp_tot", "Primary production", "Pg C yr-1", 12 * SEC_PER_YEAR * 1e-15),
    "ppint": Var("ppint", "Integrated primary production", "Pg C yr-1", 12 * SEC_PER_YEAR * 1e-15),
}

# Physical surface fields for the regional cycles (from the BLOM `hm` history files)
PHYS_MONTHLY_VARS = {
    "sst": Var("sst", "Sea surface temperature", "degC", 1.0, "WOA13"),
    "sss": Var("sss", "Sea surface salinity", "psu", 1.0, "WOA13"),
    "mld": Var("mld", "Mixed layer depth", "m", 1.0, "WOCE"),
}

# Variables shown in the regional monthly cycles, in display order
REGIONAL_VARS = ("pco2", "co2fxn", "pp_tot", "ppint", "srfo2", "srfsi", "srfpo4", "srfno3",
                 "sst", "sss", "mld")

DEPTH_LEVELS_M = (0, 100, 500, 1000, 2000, 3000, 4000)
BASINS = ("glb", "pac", "atl", "ind", "so")

# name: (long name, lat_min, lat_max); bounds as in legacy plot_reg_mon.ncl
REGIONS = {
    "ARC": ("Arctic", 66.0, 90.0),
    "NATL": ("North Atlantic", 18.0, 66.0),
    "NPAC": ("North Pacific", 18.0, 66.0),
    "TATL": ("Tropical Atlantic", -18.0, 18.0),
    "TPAC": ("Tropical Pacific", -18.0, 18.0),
    "IND": ("Indian Ocean", -18.0, 25.0),
    "MSO": ("Southern Ocean (mid-latitude)", -58.0, -18.0),
    "HSO": ("Southern Ocean (high-latitude)", -90.0, -58.0),
}


def aou(o2, o2_sat):
    """Apparent oxygen utilisation: saturation minus oxygen (legacy: p_o2lvl - o2lvl)."""
    return o2_sat - o2


def co2_net(co2fxd, co2fxu):
    """Net CO2 flux into the ocean, still in model units (kg C m-2 s-1)."""
    return co2fxd - co2fxu


# Basin (key into the zonal-mean basin masks) in which each region lies
REGION_BASINS = {
    "ARC": "glb", "NATL": "atl", "NPAC": "pac", "TATL": "atl",
    "TPAC": "pac", "IND": "ind", "MSO": "glb", "HSO": "glb",
}

# Legacy region masks remove the Gulf (25-40N, 40-65E) from the Indian Ocean region
REGION_EXCLUSIONS = {"IND": (25.0, 40.0, 40.0, 65.0)}  # lat_min, lat_max, lon_min, lon_max
