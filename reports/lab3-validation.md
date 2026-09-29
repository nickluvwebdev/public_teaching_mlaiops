# Lab 3 validation

- Full repository test suite: **49 passed**, 44 dependency warnings (no failures).
- Targeted Ruff check: service, Cloud Run adapter, deployment/smoke/experiment/serialization scripts and new tests passed.
- Portability audit passed: no provider-specific strings in src, service, monitoring or tests.
- Python 3.11 serving container built successfully with hash-required dependencies and pinned base image.
- Actual Lab 2 stable artifact loaded successfully in that container: RandomForestClassifier, 100 trees. Serialization format: skops 0.14.0.
- Runtime image source commit: 29dddb48630a31a936cdeb6d274254513002e1c7. Later commits change experiment/report/documentation only.
- Tests cover health during loading, readiness failure, once-only model load, versioned errors, schema/batch behavior, immutable deployment references and scoped teardown.

Cloud latency, canary and rollback validation is recorded separately in lab3-load.md and lab3-evidence after the managed experiment finishes. Unit tests alone do not satisfy those lab items.

## Managed run, 2026-09-29

- Adapter `make smoke`: passed against the live stable deployment; single/batch predictions agreed.
- Predeclared warm concurrency-10 target: passed (p95 202.88 ms, 0% observed errors).
- Real 90/10 traffic observed: 10,749 stable and 1,251 candidate requests.
- Quality alarm: inconclusive after the predeclared 12,000-request cap; successful degradation detection is not demonstrated.
- Rollback: all 300 subsequent responses returned stable version 1 with HTTP 200.
- Experiment exited 0 and deleted both serving services; `make teardown LAB=3` then passed again with no remaining services.
- Temporary project-level model metadata read grant revoked at 16:54:02 UTC.
