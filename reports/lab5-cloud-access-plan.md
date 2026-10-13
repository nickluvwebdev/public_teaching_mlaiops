# Lab 5 temporary cloud access plan

GCP: reuse the course training and serving identities; create a Lab 5 CI/orchestration identity. All added project grants expire after two hours and are removed at teardown. The serving role contains only model-metadata get and reads the lab model prefix. Training reads/writes only this lab's artifact prefix. The orchestrator has custom pipeline/metadata/job/model operations and Cloud Run release permissions; it can act as only the training/serving identities. Registry write access is limited to the course repository and removed at teardown. No service-account keys are created and no IAM-policy administration permission is given to a lab identity.

AWS: the authenticated account is 349819881336 in Sydney. A single tagged lab bucket, Lambda function and execution role will be created. The function role can read only the exported model object and write only its own logs; the API endpoint is invoked through AWS signed SDK calls, without a public function URL. No continuously running managed endpoint or account-plan upgrade is needed. Remove the role, function, objects and bucket after the real adapter roundtrip and exact-score agreement are recorded.

Removal experiment: remove serving model-read permission, force a fresh registry read with the serving identity, record the denial, then restore access and demonstrate success. The added permissions are explicitly temporary and cleaned up, including the grant used for the test.

Cost plan remains 30 THB expected gross, 50 THB operational ceiling. API invoices/credits must be reconciled afterward. A one-run retraining schedule will be paused immediately and deleted after evidence collection.
