# Lab 2 completed — experiment tracking and model registry

All five lab tasks were executed in Ubuntu and Google Cloud. Actual settled billing
is still pending; costs below are estimates, not invoice amounts.

| Task | Evidence |
|---|---|
| 1. Managed training | Vertex CustomJobs on one n1-standard-4 Spot worker; data and artifacts in cloud storage |
| 2. Budgeted study | 12 configurations across three hyperparameters, plus two seed checks; 14 distinct finished MLflow runs |
| Recovery | Controlled exit 75 after three checkpointed trials; a fresh managed job resumed and completed the study |
| 3. Comparison | lab2-comparison.md and lab2-comparison.csv, including the <=200-word justification |
| 4. Registry and promotion | Exact model version 1 with all eight lineage fields; staging alias verified |
| 5. Reload | Downloaded version 1 from the provider registry into an empty directory and scored five held-out rows |
| Teardown | make teardown LAB=2 ran; zero active training jobs and zero serving endpoints |

## Selected model

- Random forest: 100 trees, maximum depth 4, minimum leaf size 5.
- Model seed and split seed: 20260101.
- Validation ROC-AUC: 0.842600.
- Held-out test ROC-AUC: 0.853286.
- Across three model seeds: validation mean 0.841900, sample standard deviation 0.001755.
- Selected MLflow run: 1761e943a76b40348f359d3c528f5081.
- Registry reference: projects/775344551291/locations/asia-southeast1/models/1431682886620151808@1.
- Aliases: candidate, default, staging.
- Training source commit: 7b2285db68dbdd0e144d02ad6d622b445dba5eef.
- Training image: asia-southeast1-docker.pkg.dev/itcs355-6688058/itcs355/itcs355-lab2@sha256:7c91ed44c8ab02c02c7b00659d245dc26359e0faba6d2630845965488320132f.

The selected trial finished successfully before the first job's intentional interruption.
That parent job is therefore marked FAILED by Vertex, while the selected MLflow run is
FINISHED and its artifacts are valid. The resumed job finished SUCCEEDED. This is
controlled interruption evidence, not a claim of naturally occurring Spot preemption.

[Open model registry](https://console.cloud.google.com/vertex-ai/locations/asia-southeast1/models/1431682886620151808?project=itcs355-6688058)

## Cost

- Fit-only estimate for all trials: 0.069424 THB.
- Worker-interval estimate for both jobs: 0.6778 THB.
- Conservative create-to-end estimate, including queue time: 6.7085 THB.
- Planning budget: 150 THB; 50 THB reserved for non-fit overhead.
- Actual billed cost: pending reconciliation. Storage, image retention, operations,
  logging and transfers are additional. These compute estimates are alternative
  views of the same usage; do not add them together.

See lab2-cost.md for assumptions and official pricing sources. Registry models,
training images and artifacts are retained for Lab 3; no serving compute is running.

## Five held-out predictions

| Reading ID | Failure probability |
|---|---:|
| 125 | 0.018240 |
| 126 | 0.070234 |
| 127 | 0.028941 |
| 128 | 0.027750 |
| 129 | 0.013198 |

## Files and rerun commands

The Ubuntu project is /home/nick/projects/public_teaching_mlaiops.
The full evidence is in reports/lab2-*; the synchronized tracking database is
reports/lab2-mlflow.db. Cloud model artifacts remain at the URI recorded in the
registry evidence.

```bash
cd /home/nick/projects/public_teaching_mlaiops
source ~/.venvs/itcs355/bin/activate
make compare
python scripts/reload_check.py --name itcs355-6688058 --version 1
make cost-report
make teardown LAB=2
```

The README records the promotion owner and required evidence for an organisation.
44 local tests passed, along with portability and changed-file lint checks. Real
cloud reload, staging promotion and terminal-job state were independently verified.

## Problems encountered and resolved

1. Noninteractive WSL did not inherit the gcloud PATH; used the existing installation.
2. Vertex API was disabled; enabled it.
3. The Lab 1 user identity could not act as a training service account; created a
   dedicated keyless runtime account with Lab 2 prefix-scoped storage access.
4. Vertex rejected max_wait_duration with Spot scheduling; removed this
   FLEX_START-only option and added a regression test.
5. First-use cloud provisioning was slow; waited for that job rather than duplicating it.

No actual runtime IAM failure occurred. The scheduling error should not be presented
as an IAM failure in Drill 2. Cloud billing reconciliation remains the only pending
external verification.
