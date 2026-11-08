"""Optional control case (legacy CNTL=USER) for model-model comparison.

The recipe may hold an `experiment_cntl` section with `caseid`, `year_start`, `year_end` and optionally
`input_root` (default: the test case's). When present, the maps, zonal means and regional cycles show
test | control | test - control in place of the observations.
"""

REQUIRED_KEYS = ("caseid", "year_start", "year_end")


def control_case(cfg):
    """The control case settings (with `input_root` filled in), or None when the recipe has none."""
    cntl = cfg.get("experiment_cntl")
    if not cntl:
        return None
    missing = [k for k in REQUIRED_KEYS if k not in cntl]
    if missing:
        raise KeyError(f"experiment_cntl is missing {missing}")
    if cntl["year_end"] < cntl["year_start"]:
        raise ValueError("experiment_cntl: year_end is before year_start")
    out = dict(cntl)
    out.setdefault("input_root", cfg["experiment"]["input_root"])
    return out


def reference_kind(cfg, compare_obs=True, compare_cntl=True):
    """'control', 'obs' or None: what the test case is compared with (a control case wins over obs)."""
    if compare_cntl and control_case(cfg) is not None:
        return "control"
    return "obs" if compare_obs else None
