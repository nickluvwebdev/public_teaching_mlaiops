# Lab 3 experiment plan — declared before measurement

Use authenticated Cloud Run, one container per revision, minimum zero, maximum one, Singapore. Preserve Lab 2 model version 1. Warm acceptance target: p95 < 500 ms at concurrency 10 and request error rate < 1%. Measure concurrency 1, 10, 50, then increase only until the target fails (maximum 200). Report first-request startup separately.

Compare batch 100 against 100 single rows; measure padding up to 1 MiB and separate client latency, server handling and scoring time. Compare 1 CPU / 1 GiB against 2 CPU / 1 GiB using the same image and model.

Canary: replay labelled held-out examples through a real 90/10 revision split. Detector sees opaque cohort IDs and prediction/label pairs only. After at least 100 shared examples, signal when paired mean Brier loss difference is > 0.001 and its normal-approximation 95% confidence interval excludes zero. This is an exploratory sequential alarm, not a fixed-horizon significance claim. Maximum 12000 requests. If inconclusive, report it honestly. Roll back to 100% stable and collect 300 responses after the traffic update.

Budget guard: scale-to-zero, maximum one instance per revision, bounded tests, teardown in finally. Keep estimated serving spend below 20 THB; do not claim estimates are the invoice. Preserve registry versions and reports, delete Lab 3 serving services after evidence collection.
