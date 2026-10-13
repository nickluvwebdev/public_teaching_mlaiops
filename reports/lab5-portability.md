# Lab 5 — portability verdict

Implemented second-provider methods: S3 `upload`, `download`, and authenticated managed-endpoint `invoke`. The probe downloads the exact uploaded bytes and calls the endpoint with the downloaded feature record, then requires both a probability and an exact model version. Unit tests use fake clients and are explicitly not evidence of an AWS deployment. The real probe is pending AWS account access.

Invocation is the hardest method: request authentication, endpoint names, response bodies and error semantics differ. The adapter strips the runtime transport wrapper, but it cannot make endpoint provisioning, identity trust or quota policy portable. The original swap scaffold copied the primary configuration and changed only the provider, leaving a primary bucket URI and project identifier where a second-provider bucket and endpoint were required. The updated command requires those references explicitly; this is a real configuration leak, not an SDK import leak.

A full migration would plausibly take 5–8 engineering days: identity/registry and object migration 1–2 days, training/pipeline translation 1–2, serving and monitoring 1–2, then security, rollback and billing verification 1–2. This is a planning estimate, not measured migration time.

For this small course system, building all eleven capabilities for three clouds would not repay its maintenance cost. Keeping model/data logic independent and implementing the three-method seam is worthwhile because it supports concrete byte and response contracts. The pipeline compiler and identity setup still deliberately target the primary provider. A claim of full portability would hide the migration work. This verdict remains provisional until the real second-provider probe passes.
