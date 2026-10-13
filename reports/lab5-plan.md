# Lab 5 pre-run plan — 2026-10-13

No paid Lab 5 run has started. The objective is the smallest real managed demonstration, followed immediately by verified teardown. User preference: spend as little as possible.

Planning allowance: 30 THB expected gross incremental cost, 50 THB operational ceiling for this exercise; this is an estimate and stop rule, not a billing-enforced cap. Total term spend must remain below 800 THB. Confirm actual prior billing/credits before submission. Do not silently increase the ceiling or leave a daily/weekly retraining schedule enabled after evidence collection.

| Component | Pre-run allowance (THB) |
|---|---:|
| One managed pipeline, including one bounded Spot training job | 20 |
| Brief scale-to-zero staging service and smoke requests | 3 |
| Registry/storage/monitoring and diagnostic overhead | 5 |
| Small LLM golden-set experiment | 1 |
| Second-provider storage/invocation probe | 1 |

These allowances are conservative planning figures, not verified regional tariffs. Reconcile the actual invoice and credits afterward; missing billing data must remain marked missing. One positive run and one gate-rejection run are planned; use local gate rejection where possible to avoid repeating expensive cloud training. No cloud-only artifact will be removed until backed up.

Promotion uses validation AUC, never selection by test score. Absolute floor 0.80; improvement margin 0.005 exceeds about 2.85 times the Lab 2 measured model-seed standard deviation 0.001755, but does not cover data-split uncertainty. The incumbent must be scored on the same data/split. A weaker retrain must stop without registration; a successful full positive path cannot be claimed unless an actual candidate passes.

Choose Sunday 02:00 Asia/Bangkok retraining only after sufficient new labelled machine groups and upstream validation; create a paused schedule for evidence and delete it after the exercise. Fixed timing alone cannot justify training on corrupt or unlabelled drifted inputs.

Pending external prerequisites: AWS or Azure credentials for the real second-provider probe, access to actual billing data, and confirmation of available managed pipeline/LLM model access. Offline fixtures and mocked adapter tests are development evidence, not proof of cloud deployment or token usage.
