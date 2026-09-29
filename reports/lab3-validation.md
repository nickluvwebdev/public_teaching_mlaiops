# Lab 3 validation

- Full repository test suite: **49 passed**, 44 dependency warnings (no failures).
- Targeted Ruff check: service, Cloud Run adapter, deployment/smoke/experiment/serialization scripts and new tests passed.
- Portability audit passed: no provider-specific strings in src, service, monitoring or tests.
- Python 3.11 serving container built successfully with hash-required dependencies and pinned base image.
- Actual Lab 2 stable artifact loaded successfully in that container: RandomForestClassifier, 100 trees. Serialization format: skops 0.14.0.
- Runtime image source commit: 29dddb48630a31a936cdeb6d274254513002e1c7. Later commits change experiment/report/documentation only.
- Tests cover health during loading, readiness failure, once-only model load, versioned errors, schema/batch behavior, immutable deployment references and scoped teardown.

Cloud latency, canary and rollback validation is recorded separately in lab3-load.md and lab3-evidence after the managed experiment finishes. Unit tests alone do not satisfy those lab items.
