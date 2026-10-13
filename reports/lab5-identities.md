# Lab 5 — measured least privilege

| Identity | Actual permission scope | Why it was needed |
|---|---|---|
| `itcs355-training` | Read/write the Lab 5 run prefix; write logs; no model release permission | Bounded Spot classifier training and durable checkpoint artifacts |
| `itcs355-serving` | `aiplatform.models.get`; read only model artifact prefixes; logs | Exact-version cold model load, no training or deployment |
| `itcs355-lab5-ci` | Custom pipeline/job/metadata/model-release operations; Cloud Run release; act as only the two execution identities; registry access on one repository | Orchestrates the gated release without IAM administration or a long-lived key |
| AWS Lambda execution role | Get only `model/portable-weights.json` in the private lab bucket; write only its log group | Serverless scoring of the exported candidate, no bucket listing or public endpoint |

All new GCP project grants expire after two hours and are explicitly removed during teardown. Prefix-scoped access to existing course data is retained. Vertex requires bucket-level preflight permission checks for pipeline outputs; a separate private pipeline-only bucket has full object access for the CI identity and metadata-only `storage.buckets.get`. This avoids widening access to unrelated existing data.

Real removal experiment: a fresh serving-identity model read returned 200, removing only `aiplatform.models.get` returned 403, and restoration returned 200 after IAM propagation. See `lab5-evidence/permission-removal.json`. A warm loaded process could hide the dependency; the experiment used fresh impersonated requests.

Actual setup failures exposed two additional dependencies. Vertex's service agent needs token creation on the pipeline/training execution identities; the first run failed without it. Bucket preflight also rejects otherwise valid object-prefix conditions. Both failures are retained as evidence rather than concealed. Service-agent token grants are limited to those identities and the same two-hour window. No lab identity receives IAM-policy administration rights.
