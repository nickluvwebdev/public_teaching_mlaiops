# Lab 5 — real token cost

Provider tariff: https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing, verified 2026-10-13; model gemini-3.1-flash-lite. Prices use the native THB billing catalog: input 8.398, output 50.388, cached input 0.839 THB per million tokens. This is a tariff estimate, to reconcile with invoiced THB and credits.

| | Baseline | Output-capped |
|---|---:|---:|
| Requests | 12 | 12 |
| Provider input tokens | 3772 | 3786 |
| Provider output/thinking tokens | 468 | 343 |
| Provider cached input tokens | 0 | 0 |
| THB per 1,000 requests | 4.604903 | 4.089826 |

Working: (fresh input × native THB input rate + cached input × native THB cache rate + output × native THB output rate) / 1,000,000 × 1,000 / requests. Capped saving: 0.515077 THB per 1,000; both golden sets passed.

Cache break-even hit rate: (write factor − 1)/(write factor − read factor) = 0.0000%. Measured hit rate: 0/12 = 0.0000%. Include cache storage charges separately if applicable; the generic surcharge model does not include storage rent.

Budget defence: At this measured workload the advisory step costs about 4.604903 THB per 1,000 requests before the output cap and 4.089826 afterward, excluding infrastructure, taxes and credits. The combined shorter prompt and cap reduce response length; all tested safety and grounding cases still pass. This small golden set does not guarantee safety on every production input.

## Attribution and complete experiment usage

With the same prompt, reducing the ceiling 200 to 96 measured 4.550316 THB/1,000 against baseline 4.604903. Average output was already below 96, so that small change alone is not reliable evidence that the cap bound. Combining the ceiling with a shorter rationale and explicit missing-parts wording measured 4.089826, saving 0.515077 THB/1,000 (11.19%). All 12 cases pass. The earlier concise prompt failed and was rejected; its calls remain in the experiment cost.

`output_cap_saving` gives a worst-case ceiling reduction of 5.240352 THB/1,000 for outputs 200 to 96, not claimed as measured savings. The provider's implicit-cache write factor is 1, not the scaffold's 1.25; `cache_breakeven_hit_rate` gives 0% excluding storage. Measured cache hits were zero. No explicit cache storage was created.

Deduplicated provider records include 86 calls, 21751 input tokens and 3822 output/thinking tokens, including failed baselines and rejected optimisations. Native tariff gross: 0.375248 THB, excluding credits/taxes/infrastructure. This is measured usage priced by the billing catalog, not a retrieved invoice.

The final classifier-to-advisory smoke call used 314 input and 29 output tokens. Including it, all 87 experiment calls consumed 22,065 input and 3,851 output tokens, tariff gross 0.379346 THB before infrastructure, credits and tax.
