# Lab 2 comparison

Selection rule declared before running: choose the fastest measured fit within 0.005 validation ROC-AUC of the best search trial. Test scores do not select the model.

| Trial | Phase | Trees | Depth | Leaf | Seed | Validation AUC | Test AUC | Seconds | Estimated fit THB |
|---|---|---|---|---|---|---|---|---|---|
| 0 | search | 100 | 4 | 1 | 20260101 | 0.842439 | 0.851804 | 0.543 | 0.003018 |
| 1 | search | 100 | 4 | 5 | 20260101 | 0.842600 | 0.853286 | 0.473 | 0.002628 |
| 2 | search | 100 | 8 | 1 | 20260101 | 0.831187 | 0.848761 | 0.532 | 0.002954 |
| 3 | search | 100 | 8 | 5 | 20260101 | 0.839697 | 0.846557 | 1.572 | 0.008733 |
| 4 | search | 100 | 12 | 1 | 20260101 | 0.826829 | 0.841483 | 0.541 | 0.003004 |
| 5 | search | 100 | 12 | 5 | 20260101 | 0.832168 | 0.841734 | 0.481 | 0.002673 |
| 6 | search | 300 | 4 | 1 | 20260101 | 0.840371 | 0.853683 | 1.048 | 0.005825 |
| 7 | search | 300 | 4 | 5 | 20260101 | 0.841091 | 0.854463 | 1.035 | 0.005748 |
| 8 | search | 300 | 8 | 1 | 20260101 | 0.833776 | 0.847848 | 1.374 | 0.007631 |
| 9 | search | 300 | 8 | 5 | 20260101 | 0.837698 | 0.849052 | 1.286 | 0.007147 |
| 10 | search | 300 | 12 | 1 | 20260101 | 0.826462 | 0.837361 | 1.442 | 0.008009 |
| 11 | search | 300 | 12 | 5 | 20260101 | 0.835369 | 0.843104 | 1.354 | 0.007521 |
| 12 | seed-check | 100 | 4 | 5 | 20260102 | 0.839904 | 0.854391 | 0.398 | 0.002210 |
| 13 | seed-check | 100 | 4 | 5 | 20260103 | 0.843197 | 0.853200 | 0.418 | 0.002323 |

## Selection justification

I selected trial 1 (run 1761e943a76b40348f359d3c528f5081) using the predeclared cost-aware rule. Its validation ROC-AUC is 0.842600; the best search score is 0.842600. The selected model is the fastest measured fit within 0.005 of that score. Across three model seeds on the same machine-group split, validation AUC averages 0.841900, with sample standard deviation 0.001755 (variance 0.00000308). This measures model randomness, not uncertainty across alternative data splits. Estimated fit cost is 0.002628 THB; one monthly refit has the same fit-only cost and twelve cost 0.031535 THB. Provisioning, tracking, storage, and transfers are additional; the separate job-cost report estimates these overheads rather than claiming fit time equals the cloud bill. This choice could be wrong if future machine populations differ from this held-out split, or if timing noise changes which near-tied fit appears cheapest.

## Provenance

```json
{
  "git_commit": "7b2285db68dbdd0e144d02ad6d622b445dba5eef",
  "data_version": "1c886b512c8a5c9bf723da1cd119fc80.dir",
  "data_fingerprint": "422cccb9136e8140",
  "mlflow_run_id": "1761e943a76b40348f359d3c528f5081",
  "training_job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/4147083806697848832",
  "image_digest": "asia-southeast1-docker.pkg.dev/itcs355-6688058/itcs355/itcs355-lab2@sha256:7c91ed44c8ab02c02c7b00659d245dc26359e0faba6d2630845965488320132f",
  "seed": 20260101,
  "split_seed": 20260101,
  "metric_val": 0.84259989736441,
  "metric_test": 0.8532857870606215
}
```

## Checkpoint evidence

```json
[
  {
    "event": "trial_completed",
    "index": 0,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/4147083806697848832"
  },
  {
    "event": "trial_completed",
    "index": 1,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/4147083806697848832"
  },
  {
    "event": "trial_completed",
    "index": 2,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/4147083806697848832"
  },
  {
    "event": "controlled_interruption",
    "completed": 3
  },
  {
    "event": "resumed",
    "completed": 3
  },
  {
    "event": "trial_completed",
    "index": 3,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/6221554385055383552"
  },
  {
    "event": "trial_completed",
    "index": 4,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/6221554385055383552"
  },
  {
    "event": "trial_completed",
    "index": 5,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/6221554385055383552"
  },
  {
    "event": "trial_completed",
    "index": 6,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/6221554385055383552"
  },
  {
    "event": "trial_completed",
    "index": 7,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/6221554385055383552"
  },
  {
    "event": "trial_completed",
    "index": 8,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/6221554385055383552"
  },
  {
    "event": "trial_completed",
    "index": 9,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/6221554385055383552"
  },
  {
    "event": "trial_completed",
    "index": 10,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/6221554385055383552"
  },
  {
    "event": "trial_completed",
    "index": 11,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/6221554385055383552"
  },
  {
    "event": "trial_completed",
    "index": 12,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/6221554385055383552"
  },
  {
    "event": "trial_completed",
    "index": 13,
    "job_id": "projects/itcs355-6688058/locations/asia-southeast1/customJobs/6221554385055383552"
  }
]
```

Study-process estimated cost including tracking: 0.435073 THB.
Rates are estimates, not settled billing. See lab2-cost.md.
