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
