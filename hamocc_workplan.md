# HAMOCC diagnostics: work plan

Gaps between the blomster `hamocc/` toolbox and the legacy `NorESM-Diagnostics/packages/HAMOCC_DIAG`,
as tasks in suggested order. Legacy paths are relative to `HAMOCC_DIAG/`; legacy obs and grid data are in
`/scratch/data/noresm-diagnostics-data/HAMOCC_DIAG` (referred to below as `$LEGACY_DATA`).

Order: T1 fixes a bias in current output; T2 and T3 make results checkable and comparable; T4 and T5 add
legacy features; T6-T8 are robustness and options. T1-T3 are independent of each other (T3 touches the same
plot functions as T2, so do T2 first). T4 builds on T3's plot code only for the difference panels.

## T1. Per-variable obs masks for regional cycles  (bug, do first)
* Problem: legacy `code/regional_mean.sh` masks each variable with `$LEGACY_DATA/grid_files/1x1d/<var>/region_mask_1x1_<region>.nc`
  before averaging; the pre-cut obs cycles were built with those masks. blomster uses one region mask for every
  variable (`regions.region_mask`), so model and obs average over different cells (pCO2, MODIS production
  at high latitudes, MLD).
* Do: add `datasets.regional.<var>.mask` (or a `datasets.regional_mask_root`) to the recipe; add a loader in
  `hamocc/regions.py` that combines region mask and variable mask (variable masks are 1x1 files, lon -179.5..179.5,
  normalise as `zonal.load_basin_mask`); apply to the model cycle in `notebooks_hamocc/regional/regional.ipynb`.
  Check mask variable names first (`mask`?) and the srf*/sst/sss/mld/pco2/co2fxn/ppint directories.
* Done when: unit test on synthetic masks; for NATL and IND the model-side cell count per variable equals the
  mask's cell count; the real-data check (obs-only) still passes.

### Status (T1)
* Done 2026-11-08. Legacy per-variable files `grid_files/1x1d/<var>/region_mask_1x1_<region>.nc` (variable `mask`,
  lon -179.5..179.5, dims `(time=12, [depth=1], lat, lon)`) are **monthly** and already equal generic region AND
  `<var>_mask_1x1.nc` (checked for NATL and IND); co2fxn has no directory, so it uses `co2fxd` (identical to `co2fxu`).
  New: `regions.load_variable_mask`, `combine_masks`, `variable_region_mask` (order: per-variable region file, else
  generic region mask AND `<var>_mask_1x1.nc`, else generic region mask); `obs_cycle` now labels months before
  averaging so monthly masks line up; recipe `datasets.regional_mask` (root, region_file, var_file, var, alias);
  `regional.ipynb` uses per-variable masks for model and obs.
* Files: `hamocc/regions.py`, `recipe_hamocc.yml`, `notebooks_hamocc/regional/regional.ipynb`,
  `tests/test_hamocc_regions.py`, `hamocc_workplan.md`.
* Tests: `PYTHONPATH=. python -m pytest tests` -> 46 passed, including synthetic masks and a read-only check against
  the real legacy files: per-month cell counts for all ten regional variables equal the mask files' for NATL and IND.
* Not verified: the notebook was not executed (no real model output); recipe `root` is the `/nird/...` convention
  path (the local copy is `/scratch/data/noresm-diagnostics-data/HAMOCC_DIAG/grid_files/1x1d`). The generic
  `regions.region_mask` NATL has 3037 cells vs 3089 in legacy `generic/region_mask_1x1_NATL.nc` (IND matches); this
  is only seen if the fallback path is used, and could be a follow-up. Obs pre-cut regional files are unchanged.

## T2. Mean and RMSE statistics on maps and sections
* Legacy: `plot_latlon.ncl`, `plot_latlon_z.ncl` print area-weighted mean of model and obs and model-obs RMSE
  in the panel titles (computed on cells valid in both).
* Do: add `climatology.stats(model, obs, area)` (area-weighted mean, bias, RMSE over common cells); show in
  `plots.map_panels` titles and `plots.zonal_panels` (use cos-lat weights for sections); pass `parea` from the grid.
* Done when: tests for stats on synthetic fields (known bias and RMSE); titles show the numbers.
* Why early: a quick check on the obs scale factors (units_verified) once real model output is available.

## T3. Model-model comparison (legacy CNTL=USER)
* Legacy: all four sets accept a control case and plot test, control and difference. blomster supports a second
  case only in the time-series notebook.
* Do: add optional `experiment_cntl` (caseid, years, input_root) to `recipe_hamocc.yml` and `configure_hamocc.py`;
  extend `plots.map_panels`, `zonal_panels`, `cycle_panels` to take a control in place of obs (test | control |
  test - control, with the same stats as T2); refactor the notebooks to loop over (case, field) so obs and control
  share code.
* Done when: synthetic two-case test; each notebook runs with `compare_obs=False` and a control case.

## T4. Separate averaging periods
* Legacy: climatology period (first year + number of years) differs from the time-series period;
  `code/determine_ts_yrs.sh` detects time-series years.
* Do: add `experiment.climo_year_start`, `climo_year_end` (default to the time-series years) and optional
  `ts_year_start`, `ts_year_end`; use them in the notebooks; optional helper in `hamocc/io.py` to detect the
  available years from file names.
* Done when: defaults reproduce the current behaviour; test for year detection and the defaults.

## T5. Missing-variable handling
* Legacy: `code/check_history_vars.sh` found the variables present and skipped the plots that need others.
* Do: make `io.open_history` return the present variables plus a list of missing ones (keep a strict mode);
  notebooks skip panels for missing variables with a printed note, e.g. `pp_tot`, `delta13clvl`, 3-D `o2`.
* Done when: test with a dataset lacking some variables; notebooks run on the real test case without errors
  and name what was skipped.

## T6. Delta13C and `pp_tot` (optional, only if the model writes them)
* Delta13C: add `delta13clvl` to `variables.LEVEL_VARS`, obs entry for `$LEGACY_DATA/obs_data/EideM-etal_2017/C13_Climatology.nc`
  (legacy variable `c13_pi`; check units and depth axis), include in maps and zonal means.
* `pp_tot`: add to `SURFACE_VARS` and `REGIONAL_VARS` with the MODIS `pp` obs, as legacy.
* Depends on T5 (skipped cleanly when absent). Neither exists in the test case, so only a synthetic test is possible
  until a run writes them.

## T7. More grids
* Legacy offers 16 predefined grids (`determine_grid_type.sh`; files in `$LEGACY_DATA/grid_files/<grid>/`).
* Do: add the grids to the recipe `grids:` section (with `parea`, corners check as for `tnx1v4`) or a lookup by
  the `experiment.grid` name; verify `blomster.grid.load` works for gx1v6 as well as the tnx grids.
* Done when: `grid.load` runs on each grid file and the unit tests cover at least one non-tnx grid.

## T8. Fixed contour levels and output options (optional)
* Legacy uses fixed contour levels per variable (`cntrs_*`, `dcntrs_*` in `plot_latlon*.ncl`, `plot_zonal_mean.ncl`),
  so runs can be compared side by side; blomster uses per-field quantile levels.
* Do: optional `levels` per variable in `hamocc/variables.py` or the recipe, used when given; optional colormap
  setting (legacy `colormap`: default or blueyellowred). `density` and `publish_html` have no counterpart and can
  stay out (Jupyter Book replaces them).

## Cross-cutting
* Keep `python -m pytest tests` fast and synthetic; add real-data checks as scripts outside the repo.
* After each task: update `CLAUDE.md` (status and caveats) and the "not yet verified" notes in the notebooks.
* Still unverified for all of the above: `xesmf` regridding and model-vs-obs maps on real output; run the
  notebooks on the test case in `noresm-test-data` once the grid file path is in place.
