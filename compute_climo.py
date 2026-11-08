#!/usr/bin/env python

import calendar
import copy
import os
import subprocess

#import sys
from pathlib import Path

from ruamel.yaml import YAML
from pyprojroot import here
# Get project root
root_path = Path(here())

yaml=YAML()
with open(root_path.joinpath('recipe.yml')) as f:
    cfg = yaml.load(f)
    experiment = cfg["experiment"]
    variables = cfg["variables"]
    caseid = experiment["caseid"]
    input_root = experiment["input_root"]
    work_root = experiment["work_root"]
    year_start = experiment["year_start"]
    year_end = experiment["year_end"]
    
# define the frequency mapping for each tag
freq={"hy": "ann", "hm": "mth", "hbgcy": "ann", "hbgcm": "mth"}

# Optional: ensure system NCO is used, not a user-overridden version
env = os.environ.copy()
env['NCO_PATH_OVERRIDE'] = 'No'

for model, tags in variables.items():       # model: [blom, hamocc]
    for tag, entry in tags.items():         # tag: [hy, hm, hbgcy, hbgcm]
        climo = entry["climo"]
        if not climo:
            continue
        print("----------------------------------")
        print(f"Process: {model}, {tag}, {climo}")
        # ncclimo arguments
        args = [
            "nco/ncclimo",
            "-m", "blom",
            "-h", tag,
            f"--clm_md={freq[tag]}",
            "-c", cfg['experiment']['caseid'],
            "-i", f"{input_root}/{caseid}/ocn/hist",
            "-o", f"{work_root}/{caseid}/{model}/{tag}",
            "-s", str(year_start),
            "-e", str(year_end),
            "-v", ",".join(climo),
            "-p", "background",
            "-j", "12"              
        ]

        print(" ".join(args))

        # Execute ncclimo
#       process = subprocess.run(
#           args,
#           check=False,
#          #capture_output=True,
#           stdout=subprocess.PIPE,
#           stderr=subprocess.STDOUT,
#           env=env,
#           text=True
#       )
        # Check for success
#       if process.returncode == 0:
#           print("Climatology generated successfully.")
#       else:
#           print("\nERROR: Climatology generation failed.")
#           print(process.stdout)

# Save generated climatology information to a YAML file
settings_file = "notebooks/settings.yml"
with open(root_path.joinpath(settings_file), "r") as f:
    settings = yaml.load(f)

settings["climos"] = {
    "blom": {
        "hy": {},
        "hm": {},
    },
    "hamocc": {
        "hbgcy": {},
        "hbgcm": {},
    }
}
#settings["timeseries"] = settings.get("climos", {})
settings["timeseries"] = copy.deepcopy(settings["climos"])
#   "experiment": cfg["experiment"],
#   "grids": cfg["grids"],
#   "datasets": cfg["datasets"],
#   "climos": {
#       "blom": {
#           "hy": {},
#           "hm": {},
#       },
#       "hamocc": {
#           "hbgcy": {},
#           "hbgcm": {},
#       }
#   },
#   "timeseries": {
#       "blom": {
#           "hy": {},
#           "hm": {},
#       },
#       "hamocc": {
#           "hbgcy": {},
#           "hbgcm": {},
#       }
#   }
#}

#sys.exit(0)

# Common configuration based on your ncclimo output
suffix = "climo.nc"

# Define seasons with their respective start and end months (ncclimo standard)
seasons_meta = {
    "ANN": ("01", "12"),
    "DJF": ("01", "12"),  # ncclimo typically sets DJF to the full year span
    "MAM": ("03", "05"),
    "JJA": ("06", "08"),
    "SON": ("09", "11"),
}

# 1. Generate files for blom -> hm (both months and all seasons)
#blom_hm_files = []

# Monthly files (01 to 12)
for i in range(1, 13):
    m = f"{i:02d}"
    mth = calendar.month_abbr[i].upper()
    fname = f"{caseid}_{m}_{year_start}{m}_{year_end}{m}_{suffix}"
  # for model in ["blom", "hamocc"]:
  #     settings['climos'][f"{model}"]['hm'][str(i)] = fname
    settings['climos']['blom']['hm'][mth] = f"{work_root}/{caseid}/blom/hm/{fname}"
    settings['climos']['hamocc']['hbgcm'][mth] = f"{work_root}/{caseid}/hamocc/hbgcm/{fname}"

# Seasonal files
for climo_period, (start_m, end_m) in seasons_meta.items():
    fname = f"{caseid}_{climo_period}_{year_start}{start_m}_{year_end}{end_m}_{suffix}"
   #for model in ["blom", "hamocc"]:
   #    settings['climos'][model]['hm'][climo_period].append(fname)
    settings['climos']['blom']['hm'][climo_period] = f"{work_root}/{caseid}/blom/hm/{fname}"
    settings['climos']['hamocc']['hbgcm'][climo_period] = f"{work_root}/{caseid}/hamocc/hbgcm/{fname}"

# 2. Generate files for other categories (ANN only)
#def generate_ann_only():
start_m, end_m = seasons_meta["ANN"]
fname = f"{caseid}_ANN_{year_start}{start_m}_{year_end}{end_m}_{suffix}"
settings['climos']['blom']['hy']['ANN'] = f"{work_root}/{caseid}/blom/hy/{fname}"
settings['climos']['hamocc']['hbgcy']['ANN'] = f"{work_root}/{caseid}/hamocc/hbgcy/{fname}"

# Build the final dictionary
#settings_dict = {
#    "settings": {
#        "blom": {
#            "hm": blom_hm_files,
#            "hy": generate_ann_only()
#        },
#        "hamocc": {
#            "hbgcy": generate_ann_only()
#        }
#    }
#}

# Write the structure to a YAML file
with open(root_path.joinpath(settings_file), "w") as f:
    yaml.dump(settings, f)
