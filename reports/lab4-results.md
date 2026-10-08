# Lab 4 — measured results

## Tests and delivery

All 54 local tests passed; lint, portability and the real serving-container integration passed. [Main CI](https://github.com/nickluvwebdev/public_teaching_mlaiops/actions/runs/37622109891) tested commit `1841064072024181bc30457bc257e5c837d6ca13`. [CD](https://github.com/nickluvwebdev/public_teaching_mlaiops/actions/runs/37622705597) then succeeded with the same tested image and model version 1; see [deployment receipt](lab4-evidence/staging-deployment.json). Final documentation/evidence CI is visible in the repository Actions page.

The deliberately broken [PR #1](https://github.com/nickluvwebdev/public_teaching_mlaiops/pull/1) removed `pressure_kpa`. [Its failed run](https://github.com/nickluvwebdev/public_teaching_mlaiops/actions/runs/37621278395) reported `test_schema_columns_present_and_typed`: `missing columns: ['pressure_kpa']`. Image build was skipped. The PR was closed without merging. See [failure log](lab4-evidence/blocked-ci.log) and [PR record](lab4-evidence/blocked-pr.json).

CD initially failed because the provider expected a legacy GitHub OIDC subject; this repository uses immutable owner/repository IDs in its subject. The exact repository, owner, main branch, staging environment and workflow were constrained in the corrected provider. Artifact write access was scoped to the single image repository. No long-lived cloud key was added. IAM was explicitly authorized outside CI.

## Real scheduled drift and alert

Cloud Scheduler invoked a managed job once per minute. It used the latest 500 accepted rows in 15 minutes, a training-only reference, and published actual Cloud Monitoring metrics. Undersized windows are reported as insufficient data, not falsely scored as zero drift.

| Phase | Temperature mean (C) | PSI | Alert threshold |
|---|---:|---:|---:|
| Baseline, 500 rows | 80.2142 | 0.00495 | 0.40 |
| Same rows with +8 C producer offset | 88.2142 | 0.66020 | 0.40 |
| Clean recovery, 500 rows | 80.2142 | 0.00495 | 0.40 |

Training reference mean: 79.6689 C. The threshold was fixed before the live experiment, above the maximum 0.35720 from 500 unchanged grouped-machine windows. Independent-row bootstraps alone would underestimate fleet variation. The separate scale and mix simulations did not cross this conservative temperature threshold; this detector does not catch every possible fault.

| Event | UTC timestamp |
|---|---|
| Injection started | 2026-10-07 17:57:55.156715 |
| Injection completed | 2026-10-07 17:57:56.730805 |
| First breaching metric | 2026-10-07 17:58:24.923619 |
| First breaching detector log | 2026-10-07 17:58:28.961953 |
| Email delivered to the authorized Gmail inbox | 2026-10-07 18:01:16 |
| Clean recovery detector log | 2026-10-08T07:03:50.497946Z |

Injection-to-metric latency was **29.77 seconds**; injection-to-detector-log latency **33.81 seconds**; injection-to-received-email latency **200.84 seconds (3 minutes 21 seconds)**. The email was independently read through Gmail; [sanitized receipt](lab4-evidence/alert-delivery.json) records the real sender, subject, metric and incident. In Bangkok time, injection was October 8 at 00:57:55 and delivery at 01:01:16. These are measured notification times, not an assumed schedule interval.

The [injection dashboard](lab4-evidence/injection-dashboard.png) is rendered from actual Cloud Monitoring API series, not a console screenshot or simulated points. [Native dashboard definition](../monitoring/dashboard.json) covers request rate, separate 4xx/5xx fractions, p50/p95/p99 latency, feature statistics and model version. [Final export](lab4-evidence/dashboard-series.json) also includes recovery and startup failures on October 8; its long gap must not be interpreted as continuous healthy traffic. The measured exercise is too short to establish the 30-day availability SLO.

## Interruption and recovery

The task paused before teardown. The schedule remained enabled overnight: 407 scheduled managed executions occurred before its invoker grant expired; one failed at expiry. Many later windows had insufficient data and did not emit drift scores. Subsequent scheduler calls were denied after expiry. This is not a zero-cost run or a continuous overnight health test. See [cost and usage disclosure](lab4-cost.md).

On resumption, two service starts failed because `aiplatform.models.get` had expired. The scheduler was paused; only model-read, log-read and metric-write permissions were temporarily restored for one hour. A fresh revision used the same tested image and model, accepted 500 unmodified rows, and one manually invoked recovery job returned PSI 0.00495. The recovery was manual; the original injection alert was from a natural scheduled run. [Recovery replay](lab4-evidence/recovery-replay.json) and [detector logs](lab4-evidence/final-drift-job-logs.json) preserve the distinction.

## Decision and teardown

The [five-line post-mortem](lab4-postmortem.md) fixes the corrupt producer rather than retraining on bad measurements. Input drift alone is not proof of concept drift or accuracy loss.

`make teardown LAB=4` removes the named schedule, managed job, endpoint, alert policy and notification channel, then verifies the compute/schedule lists. Separate scoped cleanup removes temporary IAM grants, the lab CI/monitor identities and federation pool. `LAB4_DEPLOY_ENABLED=false` prevents evidence pushes from recreating paid compute. Teardown/access receipts are in `lab4-evidence/`; shared model/image storage and the historical dashboard remain. Future reruns need explicit administrator setup again. User-facing personal review and completion email are separate from assessed repository artifacts.
