"""Three known payloads, plus batch/single agreement, on the deployed API."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import load
from cloudlayer.factory import get_adapter

p = argparse.ArgumentParser()
p.add_argument("--endpoint", required=True)
args = p.parse_args()
adapter = get_adapter(load())
base = {
    "temp_c": 78.4,
    "vibration_mm_s": 3.1,
    "pressure_kpa": 315.2,
    "hours_since_service": 4200.0,
    "load_pct": 68.0,
    "ambient_humidity": 55.0,
}
rows = [base, {**base, "temp_c": 92.0}, {**base, "hours_since_service": 100.0}]
results = [adapter.invoke(args.endpoint, row) for row in rows]
batch = adapter.invoke(args.endpoint, {"rows": rows})
assert all(0 <= r["probability"] <= 1 and r["model_version"] for r in results)
assert batch["probabilities"] == [r["probability"] for r in results]
print(json.dumps({"singles": results, "batch": batch}, indent=2))
