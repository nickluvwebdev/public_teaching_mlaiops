# ITCS355 Lab 1 — Reproducible Training

> **Course materials live in [`course/`](course/README.md)** — syllabus, slides, the faculty
> specification, all five lab handouts, and the project brief. Every document is Markdown and
> renders on GitHub, diagrams included. New to the repo? Start with the
> [portability reference](course/reference/cloud-portability-reference.md).
> Keep this block when you edit the rest of this file; it is not part of the Lab 1 deliverable.

Predicting machine failure within 7 days from sensor readings. The model is not the point;
whether a stranger can reproduce it is.

> **This README is graded.** A grader with Docker and nothing else from your setup runs one
> command and compares the result against the claim below. Edit every `<...>` and delete the
> instruction blocks marked **REPLACE** before submitting.

---

## Reproduce

```bash
make reproduce
```

expected test_roc_auc: 0.848 ± 0.010

Runtime: about 40 seconds on 4 cores. No cloud account or credentials needed for this command —
that is deliberate, and it is why a grader can run it.

---

## The problem

240 machines, 25 readings each, 6 sensor features, binary target `failed_within_7d` with a
positive rate near 12%.

Machines have persistent characteristics — a hot-running machine reads hot in every row. So the
train/validation/test split is **grouped by `machine_id`**: every reading from one machine lands
in exactly one partition. Splitting row-wise instead lets the model memorise the machine and
reports a validation score that will never survive production. `tests/test_data.py` asserts this
property holds, and Lab 4 turns it into a CI gate.

Bringing your own dataset is allowed. Replace `scripts/make_dataset.py`, update the schema in
`src/data.py`, and keep every test passing.

---

## Layout

```
src/          Layer 1 — provider-neutral. No SDKs, no bucket names, no absolute paths.
cloudlayer/   Layer 3 — the only place a provider SDK may be imported.
scripts/      Dataset generation, cloud check, portability audit, metric verification.
tests/        Data contract tests and split property tests.
```

`src/config.py` is the single point of environment knowledge. Everything else reads from it.
`make portability-audit` enforces the rule; it fails the build if a provider string appears in
`src/` or `tests/`.

---

## Setup

```bash
cp cloud.env.example cloud.env      # fill in, never commit
make setup
make cloud-check                    # eight slots, all PASS
make data                           # generate the dataset
make test                           # 10 tests, all passing
```

Post your `make cloud-check` output in the course channel before Session 1.

---

## What you must finish

Four `TODO` markers are left in the repo deliberately. Each is a graded decision, not busywork.

| Where | What |
|---|---|
| `requirements.txt` | Regenerate with `pip-compile --generate-hashes` |
| `Dockerfile` | Pin the base image by digest; add `--require-hashes` |
| `cloudlayer/<your provider>.py` | Implement `upload`, `download`, `push_image` |
| This README | The reproducibility trade-off question below |

Then:

```bash
make image-push        # image reaches your registry, digest-pinned
dvc init && dvc remote add -d storage ${BLOB_URI}/dvc
dvc add data/raw && dvc push
```

Run five or more tracked runs varying something meaningful — not five identical runs with
different seeds.

---

## Reproducibility trade-off

Under real time pressure, I would drop the digest pin on the base image first.
I would keep hashed Python dependencies and controlled seeds because they directly
protect package versions and experiment results. Without the base-image digest,
Docker may resolve the same tag to a newer OS/Python patch image later, so the build
can change even when requirements.txt stays identical. The trade-off is acceptable
for a short deadline because the container may still build and run, but it loses
bit-for-bit base-image reproducibility and could introduce OS-level changes.

---

## Notes for the grader


---

## Checklist before you submit

- [ ] `make reproduce` works from a fresh clone, on a machine that is not yours
- [ ] `make verify` passes against your claim line
- [ ] `make test` — all tests pass
- [ ] `make portability-audit` — clean
- [ ] Image builds for `linux/amd64` and is pushed, digest-pinned
- [ ] `dvc push` completed; a grader can `dvc pull`
- [ ] Five or more tracked runs with params, metrics, data fingerprint, and commit SHA
- [ ] Every **REPLACE** block above is gone (the course-materials block at the top stays)
- [ ] `git log -p | grep -i -E "secret|password|AKIA|BEGIN PRIVATE"` returns nothing

That last check is not optional. A credential in Git history is an automatic deduction in this
course, and rotating it is your responsibility, not the grader's.

## Lab 2 execution and promotion

The study runs 12 configurations across tree count, depth and minimum leaf size on
Vertex Spot compute, then repeats the selected configuration with two more model
seeds on the same held-out machine split. Selection is predeclared: fastest fit
within 0.005 validation ROC-AUC of the best search result; test scores are never
used to select. Checkpoints and consistent MLflow SQLite snapshots are uploaded
after each completed trial. A controlled exit followed by a fresh managed job
demonstrates restart recovery; it is not represented as a naturally occurring
provider preemption.

Use the existing Python environment and Google Cloud CLI:
```bash
source ~/.venvs/itcs355/bin/activate
export PATH="$HOME/google-cloud-sdk/bin:$PATH"
python scripts/lab2.py prepare --image-uri <rebuilt-image@sha256:digest>
python scripts/lab2.py submit
# Wait for the controlled interruption, then:
python scripts/lab2.py resume
# After the resumed job succeeds:
python scripts/lab2.py sync
make compare
python scripts/lab2.py register
python scripts/reload_check.py --name <model-resource-name> --version <numeric-version>
python scripts/lab2.py promote
make teardown LAB=2
```

The runner records job IDs and the image digest in reports/lab2-execution.json.
The synchronized tracking database is reports/lab2-mlflow.db; model artifacts stay
in the cloud. Start a local MLflow UI with that database to inspect the cloud runs.
The registry version description contains all eight required lineage fields as
JSON; candidate and staging aliases express promotion. A numeric registry version
is required for reload; the script fetches its remote artifacts into an empty
temporary directory and compares artifact lineage with registry properties.

In an organisation, a model owner should propose promotion and an independent
MLOps/release owner should approve it. Required evidence: immutable code/data/image
lineage, validation and held-out test results, seed sensitivity, cost estimates,
schema checks, exact-version reload evidence, and rollback readiness. A staging
alias is not production deployment. This lab creates no serving endpoint.

Cost estimates use an explicit conservative 20 THB/hour bound rather than the
scaffold's unverified 30% Spot multiplier. Each job has a 15-minute running-time
limit; the runner caps submissions at six and reserves 50 THB outside the study
process budget for overhead. See reports/lab2-cost.md for evidence and limitations.
