# Lab 5 access setup

Only the real second-provider demonstration requires another cloud account. Existing GCP ADC can be used for Vertex LLM access if the project is entitled to an available model; no API key needs to enter Git history.

1. Create an AWS account through https://aws.amazon.com/free/ and review the account plan/payment requirements. Do not create another Google free trial. AWS account creation does not mean a managed endpoint is free.
2. Install AWS CLI v2 according to https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html . Use version 2.32.0 or newer for browser login.
3. Sign into the CLI using `aws login --profile lab5-login`. See https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html . Do not paste credentials into chat or commit them. SDKs may require the documented `credential_process` configuration to consume this login session; we will verify identity with a read-only call before creating anything.
4. Tell the assistant that the account/login is ready. The real S3 and managed invocation probe still needs a small tagged bucket and endpoint, scoped identity, and immediate cleanup. Local fake-client tests do not replace it.

For billing, export a report/CSV filtered to the project, the Lab 5 period and labels where available, with gross usage and credits shown separately. The previous 0.02 THB screenshot is historical and does not establish current remaining credit.

The remaining live checklist is: bounded primary pipeline (including a legitimate passing candidate), permission-removal experiment, one-run schedule evidence, second-provider roundtrip/invocation, real LLM baseline and output-cap run with usage metadata, cost reconciliation, console teardown screenshot and a repeat check 24 hours later. No account upgrade or new trial is performed by the development scripts.
