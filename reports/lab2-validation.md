# Lab 2 local validation

- Full suite: 44 tests passed (2026-09-19).
- Real offline study: interrupted after three completed trials, resumed in a new
  working directory from persisted state and SQLite snapshot, and finished 14
  distinct run IDs without repeating the first three results.
- Checkpoint identity mismatch rejected when code revision changes.
- Selection test confirms held-out test scores do not influence selection.
- Registry contract tests retain all eight lineage properties and reject a
  mutable alias in the exact-version reload command.
- Provider portability audit passed.
- Lint passed for all changed Python files; unrelated pre-existing unused imports
  remain in the AWS and Azure scaffolds.
- The built Python 3.11 container imports the study and displays its CLI help.
- DVC manifest records sensors.csv MD5 63ec074c360e4e75d5ac2acb431feaca;
  the working dataset MD5 matches.

Offline tests establish code behavior. Cloud execution and registry evidence are
recorded separately and must not be inferred from these tests.
