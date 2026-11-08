"""Plotting helpers for the HAMOCC diagnostics."""
import matplotlib.pyplot as plt


def plot_series(series, labels=None, ax=None, title=None):
    """Plot annual series (one DataArray or a list, e.g. for a second case) against model year."""
    series = list(series) if isinstance(series, (list, tuple)) else [series]
    labels = labels or [None] * len(series)
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 3.2))
    for s, label in zip(series, labels):
        ax.plot(s["year"], s.values, label=label)
    first = series[0]
    ax.set_xlabel("Model year")
    ax.set_ylabel(f"{first.attrs.get('long_name', first.name)
                     } [{first.attrs.get('units', '')}]")
    ax.set_title(title or first.attrs.get("long_name", first.name))
    ax.grid(alpha=0.3)
    if any(labels):
        ax.legend()
    return ax


def reference_labels(obs=None, control=None):
    """(reference field, test label, reference label, difference label) for obs or control.

    The reference is `obs` or, in its place, `control` (a second case); both together is an error.
    With neither, the reference is None.
    """
    if obs is not None and control is not None:
        raise ValueError(
            "Give either obs or control as the reference, not both")
    if control is not None:
        return control, "Test", "Control", "Test - control"
    return obs, "Model", "Obs", "Model - obs"


def _diff_levels(diff):
    """Symmetric levels for a difference; a zero difference (e.g. a case against itself) gets +-1."""
    import numpy as np

    from blomster.analysis import symmetric_quantile_levels

    levels = symmetric_quantile_levels(diff)
    return levels if levels[-1] > 0 else np.linspace(-1.0, 1.0, len(levels))


def map_panels(lon, lat, model, obs=None, proj="PlateCarree", title=None, area=None, control=None):
    """Model | obs | model - obs maps (model only when there is no reference). Returns the figure.

    `control` (a second case on the same grid) takes the place of `obs`: test | control | test - control.
    With a reference and `area` (cell area, e.g. `timeseries.load_parea`) the difference title shows
    the mean, bias and RMSE over common cells (`climatology.stats`).
    """
    import cartopy.crs as ccrs
    import matplotlib as mpl
    import numpy as np

    from blomster.analysis import shared_quantile_levels, symmetric_quantile_levels
    from blomster.plots import plot_map2d

    from . import climatology

    projection = ccrs.PlateCarree(
        central_longitude=90.0) if proj == "PlateCarree" else getattr(ccrs, proj)()
    ref, test_label, ref_label, diff_label = reference_labels(obs, control)
    obs = ref
    panels = [(test_label, model)] if obs is None else [
        (test_label, model), (ref_label, obs)]
    levels = shared_quantile_levels([d for _, d in panels])
    norm = mpl.colors.BoundaryNorm(
        levels, mpl.colormaps["viridis"].N, extend="both")
    n = len(panels) + (obs is not None)
    fig, axes = plt.subplots(1, n, figsize=(
        6.5 * n, 4.2), subplot_kw={"projection": projection})
    axes = np.atleast_1d(axes)
    for ax, (label, data) in zip(axes, panels):
        plot_map2d(lon, lat, data, norm=norm,
                   cmap=mpl.colormaps["viridis"], ax=ax)
        ax.set_title(label)
    if obs is not None:
        diff = climatology.difference(model, obs, label=diff_label.lower())
        dlev = _diff_levels(diff)
        dnorm = mpl.colors.BoundaryNorm(
            dlev, mpl.colormaps["RdBu_r"].N, extend="both")
        plot_map2d(lon, lat, diff, norm=dnorm,
                   cmap=mpl.colormaps["RdBu_r"], ax=axes[-1])
        if area is None:
            axes[-1].set_title(diff_label)
        else:
            st = climatology.stats(model, obs, area)
            axes[-1].set_title(f"{diff_label}\n{climatology.stats_label(st,
                               ref_label.lower())}", fontsize=9)
    fig.suptitle(title or model.attrs.get("long_name", model.name))
    return fig


def zonal_panels(zm_model, zm_obs=None, title=None, max_depth=5500.0, area="coslat", zm_control=None):
    """Latitude-depth sections: model | obs | model - obs (model only when there is no reference).

    `zm_control` takes the place of `zm_obs`: test | control | test - control.
    The difference title shows mean, bias and RMSE over common cells, weighted by `area`
    (default cos(latitude); a DataArray, or None for equal weights; `False` hides the numbers).
    """
    import matplotlib as mpl
    import numpy as np

    from blomster.analysis import shared_quantile_levels, symmetric_quantile_levels

    from . import climatology

    zm_obs, test_label, ref_label, diff_label = reference_labels(
        zm_obs, zm_control)
    panels = [(test_label, zm_model)] if zm_obs is None else [
        (test_label, zm_model), (ref_label, zm_obs)]
    levels = shared_quantile_levels([d for _, d in panels])
    n = len(panels) + (zm_obs is not None)
    fig, axes = plt.subplots(1, n, figsize=(5.5 * n, 3.8), sharey=True)
    axes = np.atleast_1d(axes)
    units = zm_model.attrs.get("units", "")
    for ax, (label, data) in zip(axes, panels):
        cs = ax.contourf(data["lat"], data["depth"], data,
                         levels=levels, cmap="viridis", extend="both")
        fig.colorbar(cs, ax=ax, label=units)
        ax.set_title(label)
    if zm_obs is not None:
        diff = climatology.difference(
            zm_model, zm_obs, label=diff_label.lower())
        cs = axes[-1].contourf(diff["lat"], diff["depth"], diff, levels=_diff_levels(diff),
                               cmap="RdBu_r", extend="both")
        fig.colorbar(cs, ax=axes[-1], label=units)
        if area is False:
            axes[-1].set_title(diff_label)
        else:
            weight = climatology.section_area(
                zm_model) if isinstance(area, str) else area
            st = climatology.stats(zm_model, zm_obs, weight)
            axes[-1].set_title(f"{diff_label}\n{climatology.stats_label(st,
                               ref_label.lower())}", fontsize=9)
    for ax in axes:
        ax.set_ylim(max_depth, 0)
        ax.set_xlabel("Latitude")
    axes[0].set_ylabel("Depth [m]")
    fig.suptitle(title or zm_model.attrs.get("long_name", zm_model.name))
    return fig


def cycle_panels(model, obs=None, ncols=4, title=None, control=None):
    """Monthly cycles per region: `model`, `obs` and `control` map region name to a DataArray over `month`.

    `control` (a second case) takes the place of `obs` and is drawn as a dashed line.
    """
    import numpy as np

    from . import variables as v

    obs, test_label, ref_label, _ = reference_labels(obs, control)
    regions = list(model)
    nrows = -(-len(regions) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(
        4.2 * ncols, 2.8 * nrows), sharex=True, squeeze=False)
    first = next(iter(model.values()))
    for ax, region in zip(axes.flat, regions):
        ax.plot(model[region]["month"], model[region].values, label=test_label)
        if obs and obs.get(region) is not None:
            ax.plot(obs[region]["month"], obs[region].values,
                    "--", label=ref_label)
        ax.set_title(v.REGIONS[region][0], fontsize=10)
        ax.set_xticks(np.arange(1, 13, 2))
        ax.grid(alpha=0.3)
    for ax in axes.flat[len(regions):]:
        ax.set_visible(False)
    for ax in axes[-1]:
        ax.set_xlabel("Month")
    for ax in axes[:, 0]:
        ax.set_ylabel(first.attrs.get("units", ""))
    axes.flat[0].legend(fontsize=8)
    fig.suptitle(title or first.attrs.get("long_name", first.name))
    fig.tight_layout()
    return fig
