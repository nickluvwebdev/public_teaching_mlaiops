# Lab 5 — cost report (pending real billing evidence)

## 1. Estimate before running
The advance estimate is 30 THB gross incremental spend with a 50 THB operational ceiling, committed in `lab5-plan.md` before any Lab 5 paid run. Total-term ceiling is 800 THB. These are allowances, not automatic billing limits.

## 2. Actual, filtered by lab labels
Pending. No Lab 5 managed run has been executed in this session. The earlier screenshot showed 0.02 THB net for its selected period and 20.43 THB Cloud Run gross usage; it is not a Lab 5 bill and its period was not shown. Do not reuse it as Lab 5 actual cost.

## 3. Gap
Cannot calculate until actual labelled charges and credits are retrieved. The earlier Lab 4 overnight scheduler mistake is a concrete reason for immediate schedule cleanup and a separate 24-hour verification. Billing credits must be reported separately from gross usage.

## 4. Components
Training, storage, serving, pipeline and monitoring charges are pending the real run and billing export. Source/range, currency, labels and credits must accompany the numbers; no zero-cost cloud claim is made from local development.

## 5. Cost per 1,000 predictions
Pending current tariff verification and measured throughput from the Lab 5 service. Report 5%, 25% and 80% utilisation using `hourly_THB / (requests_per_second * utilisation * 3600) * 1000`. Separate provisioned-capacity assumptions from scale-to-zero request billing; do not price Cloud Run as a permanently warm machine without stating that assumption.

## 6. Applied optimisation
Prepared: scale-to-zero staging, one maximum instance, one bounded Spot training job, short-output advisory prompts, and a paused one-run schedule. Before/after cost and latency evidence still require live measurement; configuration alone is not measured savings.

## LLM token bill
The 12-case authored/offline fixtures prove the evaluation gate can fail. Their token values are not accepted as this student's provider usage. `scripts/lab5_token_report.py` requires provider-origin input/output/cache fields plus an exact model tariff and refuses fixtures. A live baseline/capped pair, measured cache hit rate and verified tariff remain pending.
