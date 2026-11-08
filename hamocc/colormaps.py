"""Colormaps of the legacy HAMOCC_DIAG (`colormap` option) plus a lookup by name.

`default`: the legacy purple-brown palette (rainbow_marco.rgb); `blueyellowred`: the MICOM palette
(blueyellowred2.rgb). RGB values are 0-255 as in the legacy rgb files. Any matplotlib colormap name also works.
"""
import matplotlib as mpl

_RAINBOW_MARCO = [
    (229, 204, 255),
    (217, 185, 255),
    (204, 166, 255),
    (191, 147, 255),
    (179, 127, 255),
    (134, 121, 210),
    (89, 115, 166),
    (45, 108, 121),
    (0, 102, 77),
    (61, 137, 57),
    (121, 172, 38),
    (182, 207, 19),
    (242, 242, 0),
    (245, 188, 0),
    (249, 134, 0),
    (252, 80, 0),
    (255, 26, 0),
    (214, 19, 0),
    (172, 13, 0),
    (131, 6, 0),
    (89, 0, 0),
]

_BLUEYELLOWRED = [
    (49, 36, 100),
    (59, 76.5, 140),
    (69, 117, 180),
    (92.5, 145, 194.5),
    (116, 173, 209),
    (143.5, 195, 221),
    (171, 217, 233),
    (197.5, 230, 240.5),
    (224, 243, 248),
    (239.5, 249, 219.5),
    (255, 255, 191),
    (254.5, 239.5, 167.5),
    (254, 224, 144),
    (253.5, 199, 120.5),
    (253, 174, 97),
    (248.5, 141.5, 82),
    (244, 109, 67),
    (229.5, 78.5, 53),
    (215, 48, 39),
    (159, 24, 38.5),
    (103, 0, 38),
]

_LEGACY = {"default": _RAINBOW_MARCO, "blueyellowred": _BLUEYELLOWRED}


def get_cmap(name=None):
    """Colormap for `name`: a legacy name ('default', 'blueyellowred'), any matplotlib name, or viridis for None."""
    if name is None:
        return mpl.colormaps["viridis"]
    if name in _LEGACY:
        rgb = [(r / 255, g / 255, b / 255) for r, g, b in _LEGACY[name]]
        return mpl.colors.LinearSegmentedColormap.from_list(f"legacy_{name}", rgb, N=256)
    return mpl.colormaps[name]
