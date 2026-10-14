# Lab 5 execution review

Status: real technical experiments completed; final billing reconciliation, 24-hour cost verification remain pending. The user authorized publication on 13 October.

## Managed pipeline and promotion

The six-stage Vertex pipeline performed ingestion, validation, Spot training, validation-metric gating, registration and private Cloud Run deployment. The first complete execution failed only at deployment authentication. A repaired managed recovery reused the five successful upstream stages and completed deployment and the private smoke test. Earlier startup permission failures are preserved in evidence, not hidden.

Candidate validation ROC AUC was 0.859642 versus incumbent 0.842600. The 0.017042 improvement exceeded the 0.005 promotion threshold and absolute 0.80 minimum. Held-out test AUC 0.865181 was not used for selection. A deliberate stronger incumbent rejected the candidate. Registered model 8230851686554402816@1 is a separate Lab 5 model; the old production model was preserved.

The trained source commit is 947b20118191af0e502fe44e453cca2b4599dfd2; deployment repair is a57644b540b18aa9f991865a76f5cff96a27f602. Images are digest pinned. Model lineage and actual managed job metadata are retained in reports/lab5-evidence.

## Identities, scheduling and portability

CI/orchestration, training and serving use separate identities with resource-scoped permissions. The live permission-removal test produced success, denial, then restored success. The weekly Bangkok schedule was created paused with one maximum run and subsequently removed during teardown.

AWS Sydney Lambda and S3 implemented upload_blob, download_blob and invoke with the actual managed logistic model weights. Uploaded and downloaded bytes matched. GCP returned 0.014802283475923952 and AWS 0.014802283475923968, agreeing within floating-point rounding. This validates these three methods, not equivalent training or registry portability.

## LLM controls

Twelve real Gemini 3.1 Flash Lite golden cases include grounding, injection, unsafe instructions, missing inputs and malformed probabilities. The initial live baseline failed five cases. Trusted-input decision checks, constrained JSON output and response validation brought baseline and the concise capped variant to 12/12. A deliberately unsafe prompt still failed two cases and the regression gate rejected it. An initial concise variant also failed and was preserved before repair. Advice never creates a work order or performs an action.

Actual provider token receipts and tariffs are recorded. The combined concise prompt and 96-token ceiling reduced modeled cost from 4.604903 to 4.089826 THB per thousand requests, about 11.19%. Cap-only changes were small because ordinary outputs were already below the cap. No cache hits were measured.

## Cleanup and remaining evidence

Cloud artifacts were downloaded with SHA-256 manifests before deleting temporary resources. Primary compute, schedule, secondary Lambda/S3/log resources and temporary identity grants are removed by make teardown LAB=5; teardown-verification.json and secondary-cleanup.json record verification. Registered models and original bucket/image artifacts are retained and may incur small storage charges.

Remaining: reconcile the posted GCP and AWS bill, credits and total-term spending; repeat inventory and cost checks after 24 hours. Console automation recovered on the next turn. An actual empty Cloud Run screenshot and posted/live billing CSVs and screenshots are now saved. A read-only 24-hour follow-up is scheduled for 14 October at 19:20 Bangkok. Do not describe tariff estimates as actual billing or claim full lab completion until these items are supplied.

## 24-hour follow-up

GCP inventory remains empty. Training and pipeline charges are now posted and reconciled in lab5-cost.md; October net is 5.172942 THB. AWS authentication expired, so its final bill/current inventory and complete term reconciliation remain pending. The report is not labelled fully complete.
