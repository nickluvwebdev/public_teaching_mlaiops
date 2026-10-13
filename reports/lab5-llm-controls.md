# Lab 5 live LLM controls

See lab5-results.md and the individual provider receipts in lab5-evidence. Twelve golden cases test ordinary grounding, missing parts, inadequate evidence, injection and unsafe instructions. Initial real baseline: 7/12. Final controlled baseline: 12/12. Final concise capped prompt: 12/12. Deliberately unsafe variant: 10/12, rejected by the golden regression gate. The rejected concise variant and failed initial provider calls are retained and included in token accounting.

The classifier probability and trusted safety fields determine the allowed decision; quoted operator notes cannot change it. JSON schema constrains that decision. Response validation rejects unexpected keys, tool calls, invalid decisions and long rationales. Advice does not execute maintenance or create work orders. These controls passed the finite golden suite, which does not guarantee all production inputs are safe.

Provider usageMetadata records actual tokens. Native THB billing-catalog prices and the prompt/cap attribution are in lab5-token-cost.md. There were zero measured cache hits; no caching savings are claimed. Posted invoice reconciliation remains pending.
