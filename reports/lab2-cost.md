# Lab 2 cost controls

Checked 2026-09-19 for asia-southeast1. Machine: n1-standard-4, one replica,
Spot scheduling requested. The scaffold's 7.6 THB/hour and flat 30% Spot factor
are not used as verified prices.

Sources:
- https://cloud.google.com/vertex-ai/pricing
- https://cloud.google.com/spot-vms/pricing
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/machine-learning/training/use-spot-vms

The official pricing page states that Spot infrastructure is billed at Compute
Engine Spot rates plus custom-training management fees. Prices vary over time.
The downloaded Singapore n1-standard-4 table entries across pricing sections span
USD 0.24035805–0.367185/hour. These are not treated as one exact Spot quote.
For planning, a deliberately conservative USD/THB assumption of 40 and a rounded
20 THB/hour allowance cover the highest observed machine entry (14.6874 THB/hour)
with additional headroom. This is an upper-bound estimate, not an invoice rate
or an asserted current foreign exchange quote.

Budget: 150 THB. The study process reserves 50 THB for provisioning, storage,
registry, logging and transfer overhead, stopping before its 100 THB allowance.
Each submitted job has a 900-second running-time limit and the ledger caps
submissions at six: at most 30 THB estimated running compute under this model,
excluding platform start/stop overhead. Two jobs are planned: one controlled
interruption and one resume. Managed compute is deprovisioned after termination.
No endpoint or persistent compute is created.

Per-trial fit costs and study-process elapsed cost are estimated separately.
Job-level elapsed times and billing reconciliation are appended after execution.
Actual settled billing is not yet available; do not label estimates as actual.

## Observed execution

| Job | Worker seconds | Create-to-end seconds | Worker estimate THB |
|---|---:|---:|---:|
| 4147083806697848832 | 31.0 | 979.2 | 0.1722 |
| 6221554385055383552 | 91.0 | 228.3 | 0.5056 |

Fit-only estimate: **0.069424 THB**.
Measured study-process estimate: **0.4351 THB**.
Worker-interval estimate: **0.6778 THB**.
Conservative create-to-end estimate, including unbilled queue time: **6.7085 THB**.

These are different views of the same compute usage; do not add them together.
Actual billed cost is unavailable until billing data is reconciled. Storage, image retention, operations, logging and egress are additional; 50 THB was reserved for overhead. No serving endpoint was deployed.
The retained models, image and checkpoints support Lab 3; terminated jobs have no running training workers.
