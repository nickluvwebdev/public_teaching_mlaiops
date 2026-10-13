# Lab 5 — identity plan and required live test

| Identity | Intended capability | Reason / scope |
|---|---|---|
| Training | Read the specific input object; write the run artifact prefix; emit tracking/logs | Cannot deploy or register models; bounded Spot job |
| Serving | Read exact registry model metadata and its artifact objects; write logs/metrics | Cannot change datasets, models or infrastructure |
| Orchestrator/CI | Push to one image repository; submit/get bounded training/pipeline jobs; act as training identity; register/deploy this lab's staging resources | Runs the DAG and handles gated release; separate from serving/training |

The orchestration identity may need `iam.serviceAccounts.actAs` on the training identity even when the worker already has object access. The pipeline also needs read access to the incumbent registry metadata to evaluate promotion. Removing an assumed-unnecessary `aiplatform.models.get` from serving would prevent cold model loads, while an already warm process could temporarily hide the dependency.

Required assessed test (not yet performed for Lab 5): remove one permission from a temporary scoped lab identity, force a fresh operation, capture the actual denial, restore only the necessary permission, and remove temporary grants during teardown. Previous Lab 4 model-load denials are background evidence, not relabelled as a new Lab 5 test. No broad IAM grants are installed by the new scripts.
