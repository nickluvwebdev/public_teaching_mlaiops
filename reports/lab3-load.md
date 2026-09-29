# Lab 3 — Serving, load testing and rollback

## Reproducible configuration
Cloud Run, Singapore, authenticated HTTPS, minimum zero, maximum one instance per revision, one Uvicorn worker, registry version 1.
Small: 1 vCPU / 1 GiB. Large: 2 vCPU / 1 GiB. Forest serving uses one job per prediction.
The exact image digest and revision configuration are in lab3-evidence/deployment.json.
Targets were committed before measurement in reports/lab3-plan.md (commit 454e4f4): warm p95 <500 ms at concurrency 10, errors <1%.
k6 uses 30-second closed-loop constant-concurrency runs from the local machine; results include the network path and authentication gateway. These are short experiments, not a long-term SLO guarantee. The load generator used only 4.30–5.27% CPU during small-c10; its CPU was not saturated. This does not rule out network or connection limits.

## Load results
| Run | requests/s | p50 ms | p95 ms | p99 ms | errors |
|---|---:|---:|---:|---:|---:|
| small-c1 | 18.47 | 52.27 | 59.53 | 69.12 | 0.00% |
| small-c10 | 67.67 | 147.42 | 202.88 | 240.10 | 0.00% |
| small-c50 | 70.71 | 613.36 | 1170.18 | 1232.47 | 0.00% |

First measured failing concurrency: **small-c50**. This is a measured bound; intermediate concurrency levels were not exhaustively searched.
New-revision first request: **32656.94 ms**, HTTP 200. This is separated from warm k6 results. Startup logs record 29,446 ms to load the stable model, finishing at 16:38:51.199 UTC within the first request interval (about 16:38:19.043–16:38:51.700 UTC). The response instance ID matches the startup log. This supports an on-demand cold start; it is one observed startup, not a cold-start percentile.

## Batch size
| Run | requests/s | p50 ms | p95 ms | p99 ms | errors |
|---|---:|---:|---:|---:|---:|
| batch100-c1 | 14.44 | 63.65 | 85.01 | 224.74 | 0.00% |

100 sequential single requests took 17597.59 ms; one 100-row request took 1178.67 ms: **14.9x** faster end to end for this replay.
This comparison includes separate HTTP/TLS connections in the sequential Python client. The sustained k6 batch throughput is 1444.21 rows/s; HTTP requests/s and predictions/s must not be confused.

## Payload size
| Run | requests/s | p50 ms | p95 ms | p99 ms | errors |
|---|---:|---:|---:|---:|---:|
| padding-1024 | 17.65 | 52.37 | 62.27 | 274.07 | 0.00% |
| padding-16384 | 13.88 | 65.13 | 83.99 | 293.83 | 0.00% |
| padding-65536 | 9.42 | 98.38 | 124.25 | 395.37 | 0.00% |
| padding-262144 | 4.86 | 199.97 | 242.83 | 456.99 | 0.00% |
| padding-1048576 | 1.32 | 723.82 | 951.45 | 1020.73 | 0.00% |

Padding is an explicit ignored transport field; the six features and model stay constant. Each k6 summary also contains server_handling_ms and server_scoring_ms.
Handling minus scoring includes upload/body reading, parsing, validation, queueing and framework overhead. It must not be described as pure JSON serialization time. The separate one-CPU container microbenchmark (reports/lab3-evidence/serialization.json) measured encoding + decoding at 1.97 ms for 1 MiB versus 4.90 ms scoring, rising to 10.28 ms at 4 MiB. Thus JSON CPU cost first dominates at the tested 4 MiB point, outside the API limit; live large-payload delays within the contract must not all be attributed to serialization. These are local-container CPU timings, not cloud CPU timings.

## Instance size
| Run | requests/s | p50 ms | p95 ms | p99 ms | errors |
|---|---:|---:|---:|---:|---:|
| large-c1 | 14.98 | 62.26 | 74.87 | 91.67 | 0.00% |
| large-c10 | 44.45 | 224.00 | 296.40 | 371.96 | 0.00% |
| large-c50 | 45.40 | 1101.14 | 1428.54 | 1558.28 | 0.00% |

At concurrency 10, p95 changes from 202.88 to 296.40 ms.
Active hourly compute cost rises from USD 0.13356 to USD 0.25452, a 90.57% increase. Same image, model, region and memory; CPU allocation changes. Choose 1 CPU / 1 GiB: it meets the declared concurrency-10 target at lower measured latency and cost. These single short runs do not prove that adding CPU generally makes serving slower; repeated randomized comparisons would be needed to distinguish scheduling, thread contention and run-to-run variation.

## Canary and rollback
The candidate is real Lab 2 trial 4, registered as version 2. Held-out Brier loss is 0.082300 versus stable 0.080347; lower is better.
The detector receives prediction/label pairs and hashed cohort IDs. It does not use model settings or map hashes to stable/candidate while deciding.
A 90/10 service traffic configuration was applied at 2026-09-29T16:47:45.322408+00:00.
Observed cohort counts: {'f8c2e86fd688': 1251, 'e9fa2ac74f9b': 10749}. Final paired statistic: {"cohorts": ["e9fa2ac74f9b", "f8c2e86fd688"], "paired_rows": 773, "difference": -0.0003598253545336342, "ci95": [-0.004100926032081703, 0.0033812753230144346]}. The planned request cap was reached after 274.68 seconds; this elapsed time is not a detection time.
Alarm: INCONCLUSIVE within the predeclared request cap; no claimed detection time.
Rollback configuration was confirmed at 2026-09-29T16:52:26.540478+00:00. Subsequent 300 requests returned version counts {'1': 300}.
The confidence interval is an exploratory repeated-check alarm on unique replayed rows, not a calibrated sequential test. Rows within machines are correlated and the held-out replay is not new production data; both limit generalization.
Evidence includes configuration snapshots plus returned versions, rather than configuration alone. **Task 4 limitation:** degradation detection was not demonstrated under the predeclared rule. Rollback was exercised at the request cap, not triggered by a successful quality alarm. The complete Lab 3 detection requirement therefore remains unmet; no claim of full marks is made.

### Five-line reflection
1. Paired Brier loss compares probability quality using known labels; HTTP errors alone would miss this regression.
2. No alarm fired within the experiment cap; detection time is unknown.
3. Faster labels and more candidate observations could shorten detection, with the same predeclared decision rule.
4. A 50/50 split gives roughly five times as many candidate requests per unit of total traffic, while exposing five times as many requests to the candidate.
5. That does not guarantee five-times-faster detection; sample overlap, correlated readings and the size of the quality gap also matter.

## Cost per 1,000 predictions
Singapore request-based rates verified 2026-09-29: CPU USD 0.0000336/vCPU-second, memory USD 0.0000035/GiB-second, requests USD 0.40/million.
Source: [Google Cloud Run pricing](https://cloud.google.com/run/pricing), Singapore selected. Detailed inputs: lab3-pricing.md.
Hourly active cost = 3600 × (CPU count × CPU rate + GiB × memory rate).
Assume **100% active-time utilisation at the measured concurrency-10 throughput** and no free-tier credit.
Small cost/1000 = 0.13356 × 1000 / (3600 × 67.67) + 0.0004 = **USD 0.000948**.
At 50% throughput with the same paid active time, the compute component doubles. Scale-to-zero idle periods instead stop active-time charges; these are different utilisation assumptions.
Large cost/1000 = **USD 0.001991**. Batch100 marginal cost/1000 rows = **USD 0.000030** at 1444.21 rows/s and one request charge per 100 predictions.
Network, artifact storage, logging, tax and billing credits are excluded; this is an estimate, not an invoice.

Batch alternative (two lines): A 1-CPU/1-GiB minimum-one service costs at least USD 0.6048/day while idle; a daily Cloud Run Job costs approximately 0.000024 × max(60, 32.66 + N/1444.21), using observed first-request latency as a startup proxy and HTTP batch throughput as a conservative job-throughput proxy. Batch is cheaper even than this idle-only baseline below approximately 36,346,919 rows/day under those assumptions; active warm-service requests add further cost.
Our actual service uses minimum zero, so it has no continuously warm 24-hour baseline: this illustrative threshold does not apply universally, and real job startup/throughput and request timing must be measured for a production decision.

## Teardown
Verified 2026-09-29T16:53:31.211329+00:00: deleted ['itcs355-lab3', 'itcs355-lab3-large']. Cloud Run services remaining in the region: 0.
Registry models, artifacts and evidence are retained for reproduction; serving compute is removed.
