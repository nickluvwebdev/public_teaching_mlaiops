"""Render the Lab 3 report from captured measurements (never invented values)."""

import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "reports/lab3-evidence"


def read(name):
    return json.loads((E / (name + ".json")).read_text())


def metrics(name):
    return read(name)["metrics"]


def table(names):
    lines = [
        "| Run | requests/s | p50 ms | p95 ms | p99 ms | errors |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in names:
        m = metrics(name)
        d = m["http_req_duration"]["values"]
        lines.append(
            f"| {name} | {m['http_reqs']['values']['rate']:.2f} | {d['p(50)']:.2f} | {d['p(95)']:.2f} | {d['p(99)']:.2f} | {m['http_req_failed']['values']['rate']:.2%} |"
        )
    return "\n".join(lines)


small = [f"small-c{n}" for n in (1, 10, 50, 100, 200) if (E / f"small-c{n}.json").exists()]
large = [f"large-c{n}" for n in (1, 10, 50) if (E / f"large-c{n}.json").exists()]
breaks = [
    name
    for name in small
    if metrics(name)["http_req_duration"]["values"]["p(95)"] >= 500
    or metrics(name)["http_req_failed"]["values"]["rate"] >= 0.01
]
cold = read("cold-first-request")
b = read("batch-vs-singles")
det = read("canary-detection")
alarm = det["alarm"]
counts = Counter(r.get("cohort", "ERROR") for r in det["observations"])
post = read("rollback-responses")
teardown = read("teardown")
rate = metrics("small-c10")["http_reqs"]["values"]["rate"]
large_rate = metrics("large-c10")["http_reqs"]["values"]["rate"]
batch_rate = metrics("batch100-c1")["http_reqs"]["values"]["rate"] * 100
hourly = 0.13356
large_hourly = 0.25452
cost = hourly * 1000 / (3600 * rate) + 0.0004
large_cost = large_hourly * 1000 / (3600 * large_rate) + 0.0004
batch_cost = hourly * 1000 / (3600 * batch_rate) + 0.000004
text = f"""# Lab 3 — Serving, load testing and rollback

## Reproducible configuration
Cloud Run, Singapore, authenticated HTTPS, minimum zero, maximum one instance per revision, one Uvicorn worker, registry version 1.
Small: 1 vCPU / 1 GiB. Large: 2 vCPU / 1 GiB. Forest serving uses one job per prediction.
The exact image digest and revision configuration are in lab3-evidence/deployment.json.
Targets were committed before measurement in reports/lab3-plan.md (commit 454e4f4): warm p95 <500 ms at concurrency 10, errors <1%.
k6 uses 30-second closed-loop constant-concurrency runs from the local machine; results include the network path and authentication gateway. These are short experiments, not a long-term SLO guarantee. The load generator used only 4.30–5.27% CPU during small-c10; its CPU was not saturated. This does not rule out network or connection limits.

## Load results
{table(small)}

First measured failing concurrency: **{breaks[0] if breaks else "not reached in tested range"}**. This is a measured bound; intermediate concurrency levels were not exhaustively searched.
New-revision first request: **{cold["ms"]:.2f} ms**, HTTP {cold["status"]}. This is separated from warm k6 results. Startup logs record 29,446 ms to load the stable model, finishing at 16:38:51.199 UTC within the first request interval (about 16:38:19.043–16:38:51.700 UTC). The response instance ID matches the startup log. This supports an on-demand cold start; it is one observed startup, not a cold-start percentile.

## Batch size
{table(["batch100-c1"])}

100 sequential single requests took {b["single_total_ms"]:.2f} ms; one 100-row request took {b["batch"]["ms"]:.2f} ms: **{b["single_total_ms"] / b["batch"]["ms"]:.1f}x** faster end to end for this replay.
This comparison includes separate HTTP/TLS connections in the sequential Python client. The sustained k6 batch throughput is {batch_rate:.2f} rows/s; HTTP requests/s and predictions/s must not be confused.

## Payload size
{table([f"padding-{p}" for p in (1024, 16384, 65536, 262144, 1048576)])}

Padding is an explicit ignored transport field; the six features and model stay constant. Each k6 summary also contains server_handling_ms and server_scoring_ms.
Handling minus scoring includes upload/body reading, parsing, validation, queueing and framework overhead. It must not be described as pure JSON serialization time. The separate one-CPU container microbenchmark (reports/lab3-evidence/serialization.json) measured encoding + decoding at 1.97 ms for 1 MiB versus 4.90 ms scoring, rising to 10.28 ms at 4 MiB. Thus JSON CPU cost first dominates at the tested 4 MiB point, outside the API limit; live large-payload delays within the contract must not all be attributed to serialization. These are local-container CPU timings, not cloud CPU timings.

## Instance size
{table(large)}

At concurrency 10, p95 changes from {metrics("small-c10")["http_req_duration"]["values"]["p(95)"]:.2f} to {metrics("large-c10")["http_req_duration"]["values"]["p(95)"]:.2f} ms.
Active hourly compute cost rises from USD {hourly:.5f} to USD {large_hourly:.5f}, a {(large_hourly / hourly - 1) * 100:.2f}% increase. Same image, model, region and memory; CPU allocation changes. Choose 1 CPU / 1 GiB: it meets the declared concurrency-10 target at lower measured latency and cost. These single short runs do not prove that adding CPU generally makes serving slower; repeated randomized comparisons would be needed to distinguish scheduling, thread contention and run-to-run variation.

## Canary and rollback
The candidate is real Lab 2 trial 4, registered as version 2. Held-out Brier loss is 0.082300 versus stable 0.080347; lower is better.
The detector receives prediction/label pairs and hashed cohort IDs. It does not use model settings or map hashes to stable/candidate while deciding.
A 90/10 service traffic configuration was applied at {read("canary-traffic-90-10")["utc"]}.
Observed cohort counts: {dict(counts)}. Final paired statistic: {json.dumps(read("canary-final-statistic"))}. The planned request cap was reached after {det["elapsed_seconds"]:.2f} seconds; this elapsed time is not a detection time.
Alarm: {json.dumps(alarm) if alarm else "INCONCLUSIVE within the predeclared request cap; no claimed detection time."}
Rollback configuration was confirmed at {read("rollback-traffic")["utc"]}. Subsequent {len(post)} requests returned version counts {dict(Counter(r.get("body", {}).get("model_version", "ERROR") for r in post))}.
The confidence interval is an exploratory repeated-check alarm on unique replayed rows, not a calibrated sequential test. Rows within machines are correlated and the held-out replay is not new production data; both limit generalization.
Evidence includes configuration snapshots plus returned versions, rather than configuration alone. **Task 4 limitation:** degradation detection was not demonstrated under the predeclared rule. Rollback was exercised at the request cap, not triggered by a successful quality alarm. The complete Lab 3 detection requirement therefore remains unmet; no claim of full marks is made.

### Five-line reflection
1. Paired Brier loss compares probability quality using known labels; HTTP errors alone would miss this regression.
2. {"Detection took " + str(round(alarm["seconds"], 2)) + " seconds" if alarm else "No alarm fired within the experiment cap; detection time is unknown"}.
3. Faster labels and more candidate observations could shorten detection, with the same predeclared decision rule.
4. A 50/50 split gives roughly five times as many candidate requests per unit of total traffic, while exposing five times as many requests to the candidate.
5. That does not guarantee five-times-faster detection; sample overlap, correlated readings and the size of the quality gap also matter.

## Cost per 1,000 predictions
Singapore request-based rates verified 2026-09-29: CPU USD 0.0000336/vCPU-second, memory USD 0.0000035/GiB-second, requests USD 0.40/million.
Source: [Google Cloud Run pricing](https://cloud.google.com/run/pricing), Singapore selected. Detailed inputs: lab3-pricing.md.
Hourly active cost = 3600 × (CPU count × CPU rate + GiB × memory rate).
Assume **100% active-time utilisation at the measured concurrency-10 throughput** and no free-tier credit.
Small cost/1000 = 0.13356 × 1000 / (3600 × {rate:.2f}) + 0.0004 = **USD {cost:.6f}**.
At 50% throughput with the same paid active time, the compute component doubles. Scale-to-zero idle periods instead stop active-time charges; these are different utilisation assumptions.
Large cost/1000 = **USD {large_cost:.6f}**. Batch100 marginal cost/1000 rows = **USD {batch_cost:.6f}** at {batch_rate:.2f} rows/s and one request charge per 100 predictions.
Network, artifact storage, logging, tax and billing credits are excluded; this is an estimate, not an invoice.

Batch alternative (two lines): A 1-CPU/1-GiB minimum-one service costs at least USD 0.6048/day while idle; a daily Cloud Run Job costs approximately 0.000024 × max(60, {cold["ms"]/1000:.2f} + N/{batch_rate:.2f}), using observed first-request latency as a startup proxy and HTTP batch throughput as a conservative job-throughput proxy. Batch is cheaper even than this idle-only baseline below approximately {int((25200-cold["ms"]/1000)*batch_rate):,} rows/day under those assumptions; active warm-service requests add further cost.
Our actual service uses minimum zero, so it has no continuously warm 24-hour baseline: this illustrative threshold does not apply universally, and real job startup/throughput and request timing must be measured for a production decision.

## Teardown
Verified {teardown["utc"]}: deleted {teardown["deleted"]}. Cloud Run services remaining in the region: {len(teardown["remaining"])}.
Registry models, artifacts and evidence are retained for reproduction; serving compute is removed.
"""
(ROOT / "reports/lab3-load.md").write_text(text)
print(text)
