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
