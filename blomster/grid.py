def load(grid_file, grid_type='p'):
    import numpy as np
    import xarray as xr
    """
    Load grid data of BLOM.

    Args:
        grid_file (str): Path to the grid file.
        grid_type (str): Grid type (e.g., 'p').

    Returns:
        tuple: Latitude, longitude, depth, mask and extended vertices (clat, clon).
    """
    with xr.open_dataset(grid_file) as grid:
        lat = grid[grid_type + 'lat'].data
        lon = grid[grid_type + 'lon'].data
        clat = grid[grid_type + 'clat'].data
        clon = grid[grid_type + 'clon'].data
        mask= grid[grid_type + 'mask'].data
        depth= grid[grid_type + 'depth'].data

    dims = [x + 1 for x in list(lat.shape)]
    clat_new = np.zeros(dims)
    clon_new = np.zeros(dims)
    clat_new[:-1, :-1] = clat[0, :, :]  # lower-left patch
    clat_new[0:-1, -1] = clat[1, :, -1] # last column
    clat_new[-1, 0:-1] = clat[3, -1, :] # last row
    clat_new[-1, -1] = clat[2, -1, -1]  # upper-right corner

    clon_new[:-1, :-1] = clon[0, :, :]
    clon_new[0:-1, -1] = clon[1, :, -1]
    clon_new[-1, 0:-1] = clon[3, -1, :]
    clon_new[-1, -1] = clon[2, -1, -1]

    return lat, lon, depth, clat_new, clon_new, mask

