"""Bounded, authenticated Lab 3 experiments; always remove serving services."""

from __future__ import annotations
import concurrent.futures
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import load, REPO_ROOT
from cloudlayer.factory import get_adapter
from cloudlayer import gcp_run
from src import data

OUT = REPO_ROOT / "reports" / "lab3-evidence"
OUT.mkdir(parents=True, exist_ok=True)
K6 = "grafana/k6@sha256:3ddc8b1a33a2c3d8edc6e99b6a762ae36cba08788463458f5e6a7703e14eb77d"
BASE = {
    "temp_c": 78.4,
    "vibration_mm_s": 3.1,
    "pressure_kpa": 315.2,
    "hours_since_service": 4200.0,
    "load_pct": 68.0,
    "ambient_humidity": 55.0,
}


def now():
    return datetime.now(timezone.utc).isoformat()


def save(name, obj):
    (OUT / (name + ".json")).write_text(json.dumps(obj, indent=2))


def call(url, payload, token):
    start = time.perf_counter()
    r = requests.post(
        url + ("/predict/batch" if "rows" in payload else "/predict"),
        json=payload,
        headers={"Authorization": "Bearer " + token},
        timeout=90,
    )
    result = {
        "utc": now(),
        "ms": (time.perf_counter() - start) * 1000,
        "status": r.status_code,
        "headers": {k: v for k, v in r.headers.items() if k.lower().startswith("x-")},
    }
    try:
        result["body"] = r.json()
    except ValueError:
        result["body"] = {"error": r.text[:500]}
    return result


def performance(url, token, label, vus, batch=1, padding=0):
    env = os.environ.copy()
    env.update(
        TARGET=url,
        TOKEN=token,
        VUS=str(vus),
        BATCH=str(batch),
        PADDING=str(padding),
        DURATION="30s",
        SUMMARY="/results/" + label + ".json",
    )
    cmd = [
        "docker",
        "run",
        "--rm",
        "--user",
        str(os.getuid()),
        "-v",
        str(REPO_ROOT / "loadtest") + ":/scripts:ro",
        "-v",
        str(OUT) + ":/results",
    ]
    for key in ["TARGET", "TOKEN", "VUS", "BATCH", "PADDING", "DURATION", "SUMMARY"]:
        cmd += ["-e", key]
    cmd += [K6, "run", "/scripts/k6.js"]
    with (OUT / (label + ".log")).open("w") as log:
        r = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
    if r.returncode not in (0, 99):
        raise RuntimeError(f"k6 runner failed ({r.returncode}); see {label}.log")
    result = json.loads((OUT / (label + ".json")).read_text())
    print(
        label,
        json.dumps(
            {
                k: result["metrics"][k]["values"]
                for k in ["http_reqs", "http_req_duration", "http_req_failed"]
            }
        ),
        flush=True,
    )
    return result


def canary(cfg, url, stable, candidate, token):
    _, _, test = data.split(data.load_raw(cfg.raw_path), 20260101)
    rows = test[data.FEATURES].to_dict("records")
    labels = test[data.TARGET].tolist()
    order = random.Random(20260101)

    def cohort(version):
        return hashlib.sha256(("blind-lab3:" + version).encode()).hexdigest()[:12]

    state = {}
    observations = []
    alarm = None
    traffic = gcp_run.traffic(cfg, "itcs355-lab3", {stable: 90, candidate: 10})
    save("canary-traffic-90-10", {"utc": now(), "resource": traffic})
    start = time.perf_counter()

    def one(index):
        result = call(url, rows[index], token)
        if result["status"] != 200:
            return {"index": index, **result}
        version = result["body"]["model_version"]
        return {
            "index": index,
            "label": labels[index],
            "cohort": cohort(version),
            "probability": result["body"]["probability"],
            "utc": result["utc"],
            "status": 200,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        for offset in range(0, 12000, 100):
            batch = list(pool.map(one, [order.randrange(len(rows)) for _ in range(100)]))
            observations.extend(batch)
            for result in batch:
                if result["status"] == 200:
                    state.setdefault(result["cohort"], {})[result["index"]] = (
                        result["probability"] - result["label"]
                    ) ** 2
            if len(state) == 2:
                a, b = sorted(state)
                shared = sorted(state[a].keys() & state[b].keys())
                if len(shared) >= 100:
                    diffs = [state[a][i] - state[b][i] for i in shared]
                    mean = statistics.mean(diffs)
                    se = statistics.stdev(diffs) / len(diffs) ** 0.5
                    if abs(mean) > 0.001 and abs(mean) > 1.96 * se:
                        alarm = {
                            "utc": now(),
                            "seconds": time.perf_counter() - start,
                            "requests": len(observations),
                            "paired_examples": len(shared),
                            "mean_brier_difference": mean,
                            "ci95": [mean - 1.96 * se, mean + 1.96 * se],
                            "worse_cohort": a if mean > 0 else b,
                        }
                        break
            if offset % 1000 == 0:
                print("canary requests", len(observations), flush=True)
    save(
        "canary-detection",
        {
            "alarm": alarm,
            "elapsed_seconds": time.perf_counter() - start,
            "observations": observations,
        },
    )
    rollback = gcp_run.traffic(cfg, "itcs355-lab3", {stable: 100})
    save("rollback-traffic", {"utc": now(), "resource": rollback})
    post = [call(url, BASE, token) for _ in range(300)]
    save("rollback-responses", post)
    save(
        "cohort-reveal",
        {
            "versions": {v: cohort(v) for v in ("1", "2")},
            "note": "Revealed only after metric detector stopped",
        },
    )
    if not all(r["status"] == 200 and r["body"]["model_version"] == "1" for r in post):
        raise RuntimeError("Rollback response verification failed")
    print("canary result", alarm, flush=True)
    return alarm


def main():
    cfg = load()
    stable_ref = json.loads((REPO_ROOT / "reports/lab2-registry.json").read_text())["model_ref"]
    candidate_ref = json.loads((REPO_ROOT / "reports/lab3-registry.json").read_text())["candidate"]
    token = gcp_run.identity_token()
    stamp = datetime.now(timezone.utc).strftime("%m%d%H%M%S")
    try:
        current = replace(cfg, serving_revision="s" + stamp, serving_no_traffic=False)
        url = get_adapter(current).deploy(stable_ref, "itcs355-lab3", "1cpu-1Gi")
        save("deployment", {"utc": now(), "resource": gcp_run.describe(cfg, "itcs355-lab3")})
        cold = call(url, BASE, token)
        save("cold-first-request", cold)
        if cold["status"] != 200:
            raise RuntimeError(f"First request failed: {cold}")
        stable = gcp_run.describe(cfg, "itcs355-lab3")["status"]["latestReadyRevisionName"]
        smoke = [call(url, {**BASE, "temp_c": t}, token) for t in (50.0, 78.4, 92.0)]
        save("smoke", smoke)
        if not all(r["status"] == 200 for r in smoke):
            raise RuntimeError("Smoke failure")
        for vus in (1, 10, 50):
            performance(url, token, f"small-c{vus}", vus)
        c50 = json.loads((OUT / "small-c50.json").read_text())
        if c50["metrics"]["http_req_duration"]["values"]["p(95)"] < 500:
            for vus in (100, 200):
                r = performance(url, token, f"small-c{vus}", vus)
                if r["metrics"]["http_req_duration"]["values"]["p(95)"] >= 500:
                    break
        performance(url, token, "batch100-c1", 1, batch=100)
        t = time.perf_counter()
        singles = [call(url, BASE, token) for _ in range(100)]
        singles_ms = (time.perf_counter() - t) * 1000
        batch = call(url, {"rows": [BASE] * 100}, token)
        save(
            "batch-vs-singles", {"single_total_ms": singles_ms, "singles": singles, "batch": batch}
        )
        for padding in (1024, 16384, 65536, 262144, 1048576):
            performance(url, token, f"padding-{padding}", 1, padding=padding)
        large_cfg = replace(cfg, serving_revision="l" + stamp, serving_no_traffic=False)
        large_url = get_adapter(large_cfg).deploy(stable_ref, "itcs355-lab3-large", "2cpu-1Gi")
        save(
            "large-deployment",
            {"utc": now(), "resource": gcp_run.describe(cfg, "itcs355-lab3-large")},
        )
        save("large-cold-first-request", call(large_url, BASE, token))
        for vus in (1, 10, 50):
            performance(large_url, token, f"large-c{vus}", vus)
        canary_cfg = replace(cfg, serving_revision="c" + stamp, serving_no_traffic=True)
        get_adapter(canary_cfg).deploy(candidate_ref, "itcs355-lab3", "1cpu-1Gi")
        resource = gcp_run.describe(cfg, "itcs355-lab3")
        candidate = resource["status"]["latestReadyRevisionName"]
        tagged = next(
            t["url"] for t in resource["status"]["traffic"] if t.get("tag") == "candidate"
        )
        save("canary-prewarm", call(tagged, BASE, token))
        canary(cfg, url, stable, candidate, token)
    finally:
        deleted = get_adapter(cfg).teardown(cfg.tags(3))
        save(
            "teardown",
            {
                "utc": now(),
                "deleted": deleted,
                "remaining": gcp_run.command(cfg, "run", "services", "list"),
            },
        )
        print("TEARDOWN VERIFIED", deleted, flush=True)


if __name__ == "__main__":
    main()
