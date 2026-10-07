# Lab 4 evidence status

## Verified work

- Local lint and portability audit passed; 54 tests passed.
- Real local serving container passed readiness, probability shape, exact version and malformed-input checks. The temporary container was removed.
- Main CI run [37621217096](https://github.com/nickluvwebdev/public_teaching_mlaiops/actions/runs/37621217096) passed all stages, including Docker build and integration.
- Deliberately broken [PR #1](https://github.com/nickluvwebdev/public_teaching_mlaiops/pull/1) removed `pressure_kpa`. [CI run 37621278395](https://github.com/nickluvwebdev/public_teaching_mlaiops/actions/runs/37621278395) failed in `test_schema_columns_present_and_typed` with `missing columns: ['pressure_kpa']`; image build was skipped. The PR was closed unmerged on 2026-10-07 at 12:31:18 UTC.
- Native Cloud Monitoring dashboard and SLO definitions are committed. The runtime emits input observations, and the scheduled-job implementation computes PSI and feature means from the latest 500 accepted rows within 15 minutes.
- Temperature threshold 0.40 is calibrated against machine-group variation, not copied from a default. See calibration, shift, scale and mix evidence. The +8 C offline shift produced PSI 0.64043; scaling by 1.5 produced 0.20257 with unchanged mean; fleet reweighting produced 0.00321. The latter two do not trigger this deliberately conservative temperature alarm.

## Not yet proven

The cloud identity setup is awaiting explicit approval after automatic approval review rejected it. CD is safely skipped while `LAB4_DEPLOY_ENABLED` is unset. No Lab 4 cloud resources or IAM changes have been made by the rejected setup.

A real staging deployment, installed dashboard, Cloud Scheduler execution, received drift email, injection-to-alert latency, cloud post-mortem and verified cloud teardown remain pending. The lab is not complete until that evidence exists. Offline drift measurements are not presented as a real scheduled alert.

The user's personal review and completion email are separate from these assessed lab artifacts.
