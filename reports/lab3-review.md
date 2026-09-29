# Lab 3 review and Drill 3 notes

## What was built

The FastAPI service has `/predict`, `/predict/batch`, `/health`, and `/ready`. It validates inputs and rejects bad requests with HTTP 422. Every application response identifies the model version. Startup loads one exact registered version through the cloud adapter; each request reuses that model. JSON logs record request ID, model version, and latency.

The GCP adapter deploys a digest-pinned Docker image to a private Cloud Run service and invokes it with an identity token. The managed experiment tests real cloud requests, not just a local container. The image includes the skops dependency required by the actual Lab 2 model artifact.

Docker Desktop was recovered by backing up its broken transient socket directories and restarting it. Images and volumes were preserved. Earlier cloud startup attempts failed because the runtime could not read version-qualified registry metadata; those failed services were deleted. A temporary, one-hour metadata-read permission allowed the measured run. Future runs need manual permission setup, documented in README.

## Answers to practise in your own words

**What was your target?** Before measuring, I committed a warm p95 below 500 milliseconds at 10 concurrent users, with fewer than 1% request errors.

**What did you measure?** With 1 CPU and 1 GiB memory at concurrency 10, p50 was 147 ms, p95 was 203 ms, p99 was 240 ms, and throughput was 67.67 requests per second. No requests failed in that sample. A p95 of 203 ms means about 95% of measured requests completed within 203 ms; it is not the average.

**Where did it break?** Concurrency 50 was the first tested level that failed the target: p95 was 1,170 ms. Concurrency 10 passed. I did not test every level between them, so I cannot claim the exact boundary is 50.

**Why have health and readiness?** Health says the process is alive. Readiness says the loaded model can make a prediction. Returning ready too early can send user traffic to a process that cannot score yet. This service stays not-ready while the model loads.

**What about cold starts?** The first request took 32.7 seconds, including about 29.4 seconds of model loading. I report this separately from warm latency. Scale-to-zero saves idle compute cost but makes first-request delay a practical concern.

**Did batching help?** Yes. A 100-row request was 14.9 times faster than 100 sequential single calls in the timing comparison. Sustained batch testing achieved about 1,444 predictions per second. Requests per second and predictions per second are different when one request contains 100 rows.

**Did larger payloads hurt?** Yes: at 1 MiB padding, p95 reached 951 ms. This includes network transfer and framework overhead. A separate local container test showed JSON encoding and decoding only exceeded model scoring at the tested 4 MiB point, beyond this API's 1 MiB padding limit. I should not call every network delay serialization cost.

**Was a bigger instance better?** Not in this short experiment. Two CPUs gave p95 296 ms at concurrency 10, compared with 203 ms for one CPU, and active hourly compute cost rose by 90.57%. I chose the smaller configuration because it met the target at lower cost. More repeated tests are needed before claiming a general cause for the larger instance's slower result.

**How much per 1,000 predictions?** About USD 0.000948 for the small instance at measured concurrency-10 throughput, assuming 100% paid active-time utilisation. This includes CPU, memory, and request charges, but excludes network, storage, logging, tax and billing credits. It is an estimate, not the actual bill. Lower throughput during the same paid time increases cost per prediction.

**What is a canary?** Route a small fraction of real requests to a candidate, compare measured behaviour, then either expand traffic or return it to the stable version. The experiment starts with 90% stable and 10% candidate. The detector compares labelled prediction quality using masked cohort IDs. In this run, 10,749 requests went to stable and 1,251 to candidate. The alarm did not trigger in 274.68 seconds and 12,000 requests: the paired difference was uncertain and its confidence interval included zero. I must say detection was inconclusive, not invent a detection time. The run rolled back at the request cap. Successful degradation detection, required by Task 4, remains unproven.

## Where to look

- `reports/lab3-load.md`: measured results, five-line canary reflection, cost calculation, and cleanup evidence.
- `reports/lab3-evidence/`: raw k6 summaries, deployment snapshots, startup logs, canary observations and rollback responses.
- `reports/lab3-plan.md`: the decision rules committed before measurements.
- `reports/lab3-validation.md`: automated checks and actual container model-load validation.
- `scripts/lab3_experiment.py`: bounded cloud experiment with teardown in `finally`.

These are short lab measurements on replayed held-out data. They do not establish a production SLO or prove how the model behaves on future data.
