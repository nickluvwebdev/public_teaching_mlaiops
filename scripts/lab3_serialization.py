"""Separate JSON CPU overhead from network/queueing; run beside the serving model."""

import argparse
import json
import statistics
import time
from pathlib import Path
import mlflow.sklearn
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("--model", required=True)
p.add_argument("--out", default="/tmp/serialization.json")
args = p.parse_args()
model = mlflow.sklearn.load_model(args.model)
model.n_jobs = 1
base = {
    "temp_c": 78.4,
    "vibration_mm_s": 3.1,
    "pressure_kpa": 315.2,
    "hours_since_service": 4200.0,
    "load_pct": 68.0,
    "ambient_humidity": 55.0,
}
frame = pd.DataFrame([base])


def measure(fn):
    samples = []
    for _ in range(5):
        fn()
    for _ in range(100):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples)


score = measure(lambda: model.predict_proba(frame))
results = []
for size in (0, 1024, 16384, 65536, 262144, 1048576, 4194304, 8388608):
    payload = {**base, "padding": "x" * size}
    encoded = json.dumps(payload)
    dump = measure(lambda: json.dumps(payload))
    parse = measure(lambda: json.loads(encoded))
    results.append(
        {
            "padding_bytes": size,
            "encoding_ms": dump,
            "decoding_ms": parse,
            "json_total_ms": dump + parse,
            "scoring_ms": score,
            "within_api_limit": size <= 1048576,
        }
    )
Path(args.out).write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
