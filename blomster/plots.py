import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.path as mpath

def plot_map2d(lon, lat, var, proj='PlateCarree', norm=None, cmap=mpl.colormaps['viridis'], *,ax=None, right_labels=True, cbar_labelsize=14, cbar_ticksize=12):
    """
    Plot 2D map with a north pole view.

    Args:
        lon (np.ndarray): Longitudes.
        lat (np.ndarray): Latitudes.
        var (np.ndarray): Variable data to plot.
        levels (list or np.ndarray): Discrete levels for color normalization.
        cmap_name (str): Name of the colormap.
        figfile (str): Output file name for saving the plot.
    """

    # Create the map
    #proj = ccrs.NearsidePerspective(central_longitude=0.0, central_latitude=80.0, satellite_height=3e6)
    if ax is None:
        if proj == 'PlateCarree':
            proj = ccrs.PlateCarree(central_longitude=90.0)
        elif proj == 'NearsidePerspective':
            proj = ccrs.NearsidePerspective(central_longitude=0.0, central_latitude=80.0, satellite_height=3e6)
        elif proj == "NorthPolarStereo":
            proj = ccrs.NorthPolarStereo(central_longitude=0.0)
        else:
            print("Unknown projection type. Use PlateCarree instead.")
            proj = ccrs.PlateCarree(central_longitude=90.0)
        fig, ax = plt.subplots(1, figsize=(11.7, 8.3), dpi=96, subplot_kw={"projection": proj})
    else:
        fig=ax.figure
    # Plot the mesh
    pm = ax.pcolormesh(lon, lat, var, cmap=cmap, norm=norm,
                       transform=ccrs.PlateCarree(), shading='auto', rasterized=True)

    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    gl = ax.gridlines(ylocs=range(-90, 90, 30), draw_labels=True)
    gl.ylocator = mpl.ticker.FixedLocator(range(-90,90,30))
    gl.right_labels = right_labels

    # Add colorbar
    cb = fig.colorbar(pm, ax=ax, fraction=0.2, shrink=0.4, label='[yr]')
    cb.set_label(label=var.units, size=cbar_labelsize)
    cb.ax.tick_params(labelsize=cbar_ticksize)

    return fig, ax
