# Lab 5 cost and budget

The advance plan was committed before paid work: 30 THB expected, 50 THB operational ceiling, 800 THB term cap. These are operating limits, not an automatic cloud spending cap. Actual invoice reconciliation is pending, so compliance with the total term cap is not yet verified.

## Measured usage and pricing

The real experiment used Vertex managed pipeline stages (resolved e2-highmem-2), one bounded n1-standard-4 Spot training job, private Cloud Run with minimum zero/maximum one instance, AWS Lambda/S3, and Gemini token calls. Startup and deployment failures are included in evidence. Native job start/end timestamps and machine specs are in all-managed-jobs.json; pipeline submissions and cached recovery are recorded separately. Billing by component and label must be reconciled with the posted bill; no missing charge is treated as zero.

Cloud Run Singapore native THB catalog rate for one CPU and one GiB is 4.4866116 THB per active hour before request fees, credits and tax. Measured warm throughput was 17.5585 single predictions/sec and 2662.6990 predictions/sec with batches of 100. Request p95 was 230.71 ms and 208.93 ms respectively. This small benchmark does not prove a production SLO or cold-start latency.

| Utilisation | Single prediction THB/1000 | Batch-100 THB/1000 |
|---|---:|---:|
| 5% | 1.419575 | 0.009361 |
| 25% | 0.283915 | 0.001872 |
| 80% | 0.088723 | 0.000585 |

The table assumes allocated capacity charged for an hour and useful predictions occupying 5%, 25% or 80% of that hour. It is a capacity model, not an invoice; the actual service uses request-based billing and scales to zero. Marginal request pricing beyond the free tier adds 0.013437 THB per thousand requests (100 predictions/request divides this by 100 per thousand predictions). The applied batching optimisation improves measured throughput substantially, but actual bill savings remain pending.

Native training catalog rates and actual VM durations are saved for reconciliation. Do not apply an invented Spot discount. Pipeline creation, provisioning, failed attempts, storage and Artifact Registry must be included; they explain possible differences from the advance estimate. AWS Cost Explorer initially returned estimated zero with no posted groups; that is not a final bill.

## LLM and cleanup

See lab5-token-cost.md for real token accounting, rejected attempts, verified native THB prices, the prompt/cap optimisation and zero measured cache hits. Tariff costs exclude credits and taxes.

All temporary paid compute and scheduling are torn down after the experiment; original model and image storage remains. Repeat verification and billing review after 24 hours. Final cost figures, label breakdown, credits and the estimate-versus-actual gap cannot be completed until the billing report is available.

## Actual console figures captured on 13 October

The downloaded posted October report totals **0.037721 THB net** (displayed 0.04), including Cloud Storage 0.037602, Cloud Run 0.000117 and Artifact Registry 0.000002 THB. Displayed Cloud Run gross usage is 20.43 THB with 20.42 THB savings; use unrounded CSV totals instead of subtracting rounded display values. This period includes earlier labs and is not the Lab 5 bill.

The live SKU report for September 29–October 13 shows approximately **23.97 THB gross**, comprising about 22.46 posted gross and **1.51 THB directional live usage**, before credits. New live rows include instance-based Cloud Run CPU 1.02, memory 0.11, Gemini input 0.19 and output 0.19 THB. The Gemini 0.38 THB rounded total agrees with the provider-token calculation of 0.379346 THB. Live costs cover limited SKUs: Vertex pipeline and managed training charges are absent, so their cost is pending, not zero. The 1.51 THB cannot be substituted for final Lab 5 cost or compared with the 30 THB advance estimate as a complete experiment.

AWS Cost Explorer was checked again after teardown; the downloaded estimate is saved. Same-day zero estimates can lag usage. A complete net/gross estimate gap, resource-label breakdown and total-term budget reconciliation remain pending posted training and pipeline charges.

Evidence: [posted CSV](lab5-evidence/gcp-posted-billing-20261013.csv), [live CSV](lab5-evidence/gcp-live-billing-20261013.csv), [posted screenshot](lab5-evidence/lab5-posted-billing.jpg), [live summary](lab5-evidence/lab5-live-billing-summary.jpg), [live SKU screenshot](lab5-evidence/lab5-live-billing-skus.jpg), [empty Cloud Run console](lab5-evidence/lab5-empty-cloud-run.jpg). A read-only follow-up is scheduled for 14 October 19:20 Bangkok, after the 24-hour teardown interval. The repeated same-day inventory is empty; it is not labelled a 24-hour check.

## Posted reconciliation after 24 hours — 14 October

This section supersedes the same-day missing-training status above. GCP has now posted the training and pipeline charges. The downloaded October service and SKU CSVs agree on **5.172942 THB net**, with tax currently zero. Service totals are Vertex AI 4.931621, Compute Engine 0.195910, Cloud Storage 0.045126, Cloud Run 0.000281 and Artifact Registry 0.000004 THB. This is the account's October-to-date report, including earlier labs, not an exclusively label-filtered Lab 5 invoice.

| Component | Posted net THB | Evidence/interpretation |
|---|---:|---|
| Pipeline orchestration | 3.023325 | Three charged pipeline jobs, versus four submissions in the run receipts; use billed count rather than assuming every failed submission was charged |
| E2 stage CPU and RAM | 1.227658 | 0.619682 CPU + 0.607976 RAM |
| Vertex SSD disk | 0.281312 | October total includes earlier disk usage; not exclusively Lab 5 |
| Spot N1 CPU and RAM | 0.195910 | Compute Engine posted Spot rates, not an invented discount |
| N1 management fees | 0.020011 | 0.013318 core + 0.006693 RAM |
| LLM | 0.379315 | Exact provider-token counts: 22,065 input and 3,851 output |
| Original model/object storage | 0.045126 | Retained storage, including earlier labs |
| Cloud Run | 0.000281 | Displayed 21.56 THB gross offset by displayed 21.56 savings; nonzero net is egress |
| Artifact Registry | 0.000004 | Very small posted egress; retained storage can accrue later |

The component totals sum to 5.172942 THB. Provider-token tariff calculation was 0.379346 THB; the posted 0.379315 differs by approximately 0.000031 THB, consistent with event-time tariff/conversion and precision differences. Both totals exclude unrelated infrastructure from the LLM figure.

The posted service SKU includes **instance-based** Cloud Run CPU/memory (1,402.32 seconds, gross 1.02 + 0.11 THB), correcting the earlier assumption that all live serving was request-based. The utilisation table above is an explicit capacity model at its stated tariff, not the experiment's invoice or measured invoice savings. Free-tier savings offset compute; batching/token reductions are measured experiments, not claimed dollar savings from these zero-net compute rows.

The observed October GCP net is 24.827058 THB below the 30 THB advance estimate, but that comparison is provisional because its period includes earlier labs and AWS is unresolved. Spot training, cached recovery and free-tier Cloud Run savings explain much of the low observed net. The 800 THB term cap cannot be fully reconciled from this October report alone.

**24-hour resource check:** GCP active pipelines, training, schedules and services are all empty at 2026-10-14 12:21 UTC. AWS's temporary authentication session expired; its current bill and 24-hour inventory could not be read. The verified teardown receipts from 13 October remain valid historical evidence, but do not replace a current check. AWS reauthentication is required to complete the remaining reconciliation. No cloud resource was started and no IAM access was changed.

Evidence: [posted services](lab5-evidence/gcp-posted-24h-services.csv), [posted SKUs](lab5-evidence/gcp-posted-24h-skus.csv), [bill total screenshot](lab5-evidence/lab5-billing-24h-total.jpg), [SKU screenshot](lab5-evidence/lab5-billing-24h-skus.jpg), [24-hour inventory](lab5-evidence/teardown-24h-verification.json).
