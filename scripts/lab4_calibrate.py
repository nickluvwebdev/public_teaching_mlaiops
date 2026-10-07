"""Reproduce the pre-exercise temperature PSI calibration without cloud access."""
import json
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import data, config
from monitoring.drift import psi

train, _, _ = data.split(data.load_raw(config.load(strict=False).raw_path), 20260101)
rng = np.random.default_rng(20261007)
a = train.temp_c.to_numpy()
iid = [psi(a, rng.choice(a, 500)) for _ in range(500)]
groups = train.machine_id.unique()
cluster = []
for _ in range(500):
    selected = rng.choice(groups, 20, replace=False)
    cluster.append(psi(a, train[train.machine_id.isin(selected)].temp_c.to_numpy()))
result = dict(seed=20261007, rows=500, bootstrap_windows=500,
              iid_p99=float(np.quantile(iid, .99)), iid_max=max(iid),
              machine_group_p99=float(np.quantile(cluster, .99)), machine_group_max=max(cluster))
print(json.dumps(result, indent=2))
