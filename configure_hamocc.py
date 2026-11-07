from pathlib import Path

import yaml
from pyprojroot import here

root_path = Path(here())

with open(root_path.joinpath('recipe_hamocc.yml'), 'r') as f:
    cfg = yaml.safe_load(f)

book = root_path.joinpath('notebooks_hamocc')

# generate TOC
toc = {
    'format': 'jb-book',
    'root': cfg['diagnostics']['root'],
    'chapters': cfg['diagnostics']['chapters'],
}
with open(book.joinpath('_toc.yml'), 'w') as f:
    yaml.dump(toc, f, default_flow_style=False, sort_keys=False)

# save settings read by the notebooks
settings = {k: cfg[k] for k in ('hamocc', 'experiment', 'variables', 'grids', 'datasets')}
with open(book.joinpath('settings.yml'), 'w') as f:
    yaml.dump(settings, f, default_flow_style=False, sort_keys=False)
