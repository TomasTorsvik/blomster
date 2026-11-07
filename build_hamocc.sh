#!/usr/bin/env -S -i bash
set -e

# activate conda
for conda_sh in \
  "/conda/miniconda3/etc/profile.d/conda.sh" \
  "/cluster/software/Miniforge3/24.1.2-0/etc/profile.d/conda.sh"
do
  if [ -f "${conda_sh}" ]; then
    . "${conda_sh}"
    break
  fi
done
conda activate /nird/datalake/NS16000B/blomster-env

# parse experiment info
recipe=recipe_hamocc.yml
caseid=$(yq -r '.experiment.caseid' ${recipe})
year_start=$(yq -r '.experiment.year_start' ${recipe})
year_end=$(yq -r '.experiment.year_end' ${recipe})
www_root=$(yq -r '.experiment.www_root' ${recipe})
work_root=$(yq -r '.experiment.work_root' ${recipe})
project=$(echo $www_root |grep -oP 'NS\d+K' |tr '[:upper:]' '[:lower:]')
user=$(echo $work_root |cut -d/ -f3)
if echo $www_root | grep 'datalake' >/dev/null 2>&1 ; then
  dataservice='datalake'
else
  dataservice='datapeak'
fi

umask 002

# generate TOC and settings
python configure_hamocc.py

# build the book
jupyter-book build -qq -n notebooks_hamocc

# Backup configs
cp ${recipe} notebooks_hamocc/{_config.yml,_toc.yml,settings.yml} notebooks_hamocc/_build/jupyter_execute/

# Publish
chmod -R g+w notebooks_hamocc/_build/html
if test -w ${www_root} ; then
  www_sub=${caseid}/yrs${year_start}to${year_end}-obs
  mkdir -p ${www_root}/${www_sub}
  rsync -au --delete --remove-source-files notebooks_hamocc/_build/html/ ${www_root}/${www_sub}
  echo 'Generated diagnostics is at:'
  echo "https://${project}.web.sigma2.no/${dataservice}/diagnostics/hamocc/$user/${www_sub}"
else
  echo "You do not have write permission to ${www_root}."
  echo "Generated diagnostics is under:"
  echo "notebooks_hamocc/_build/html"
fi
