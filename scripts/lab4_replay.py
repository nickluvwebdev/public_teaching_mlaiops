"""Feed a fixed labelled-window fixture through the actual staging API.

The injected +8 C offset simulates a faulty sensor producer; never retrain on it.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import requests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config, data
from cloudlayer.gcp_run import identity_token
from monitoring.drift import compare

p = argparse.ArgumentParser()
p.add_argument("mode", choices=["baseline", "shift", "recovery"])
a = p.parse_args()
cfg = config.load()
root = config.REPO_ROOT
resources = json.loads((root / "reports/lab4-resources.json").read_text())
train, _, _ = data.split(data.load_raw(cfg.raw_path), 20260101)
window = train.sample(n=500, random_state=20261007).copy()
if a.mode == "shift":
    window["temp_c"] += 8.0
rows = window[data.FEATURES].to_dict("records")
start = datetime.now(timezone.utc).isoformat()
headers = {"Authorization": "Bearer " + identity_token()}
responses = []
for offset in range(0, len(rows), 100):
    tick = time.perf_counter()
    r = requests.post(resources["url"] + "/predict/batch", json={"rows": rows[offset:offset+100]}, headers=headers, timeout=120)
    result = {"utc": datetime.now(timezone.utc).isoformat(), "status": r.status_code,
              "ms": (time.perf_counter()-tick)*1000, "body": r.json()}
    responses.append(result)
    r.raise_for_status()
    assert r.json()["model_version"] == "1"
    assert len(r.json()["probabilities"]) == 100
# A bad caller request proves 4xx observability without contaminating accepted input rows.
invalid = requests.post(resources["url"] + "/predict", json={"temp_c": 80}, headers=headers, timeout=30)
assert invalid.status_code == 422
out = root / "reports/lab4-evidence" / (a.mode + "-replay.json")
out.write_text(json.dumps({"mode": a.mode, "injection_start": start,
    "injection_complete": datetime.now(timezone.utc).isoformat(), "rows": len(rows),
    "offset_c": 8 if a.mode == "shift" else 0, "responses": responses,
    "expected_window": [vars(x) for x in compare(train, window, data.FEATURES)],
    "invalid_request_status": invalid.status_code}, indent=2))
print(out)
print("Accepted", len(rows), "rows; window temperature mean", window.temp_c.mean())
