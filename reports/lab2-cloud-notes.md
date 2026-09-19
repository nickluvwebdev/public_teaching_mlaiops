# Cloud setup and observed errors

- Enabled Vertex AI API; it was initially disabled (SERVICE_DISABLED).
- Created keyless itcs355-training service account. Object access is restricted to
  the itcs355/lab2/ prefix; image reads are limited to the course repository.
- Submitter and runtime identities differ. The configured Lab 1 user identity
  was replaced with the dedicated runtime identity. No runtime permission failure
  has yet been observed, and none is invented for the Drill 2 report.
- First submission was rejected with INVALID_ARGUMENT: max_wait_duration is only
  supported for FLEX_START. Removed that option from Spot jobs and added a test.
  This was a request validation error before compute was created.

## Observed managed execution

The first Spot job 4147083806697848832 completed three trials and deliberately
exited with status 75 after its durable checkpoint. Its Vertex status is FAILED
because the interruption was intentional, not because training or storage failed.
The second Spot job 6221554385055383552 restored the checkpoint, skipped those
three completed trials, and finished all 14 runs with JOB_STATE_SUCCEEDED.
Both jobs used one n1-standard-4 replica, Spot scheduling, the dedicated runtime
service account and a 900-second running-time limit. Recovery evidence is in
lab2-comparison.md, the cloud checkpoint, and the saved job logs.

No runtime IAM failure occurred after the scoped grants. The actual observed
request failure was the FLEX_START-only scheduling option, recorded above.
Do not describe it as an IAM error in Drill 2.
