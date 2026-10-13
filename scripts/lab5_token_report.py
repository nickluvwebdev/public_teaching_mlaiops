"""Price only genuine usage records with a supplied, verified tariff."""

import argparse
import json
from pathlib import Path


def totals(report):
    rows = report["recorded_responses"]
    if not rows or any(x.get("usage_source") != "provider_usageMetadata" for x in rows):
        raise ValueError(
            "Actual token cost requires live provider usage; fixtures are not billing evidence"
        )
    return {
        "requests": len(rows),
        "input": sum(x["input_tokens"] for x in rows),
        "output": sum(x["output_tokens"] for x in rows),
        "cached": sum(x.get("cached_input_tokens", 0) for x in rows),
        "cache_hits": sum(x.get("cached_input_tokens", 0) > 0 for x in rows),
    }


def price(usage, tariff):
    fresh = usage["input"] - usage["cached"]
    if "input_thb_per_million" in tariff:
        thb = (
            fresh * tariff["input_thb_per_million"]
            + usage["cached"] * tariff["cached_thb_per_million"]
            + usage["output"] * tariff["output_thb_per_million"]
        ) / 1_000_000
        return thb * 1000 / usage["requests"]
    usd = (
        fresh * tariff["input_usd_per_million"]
        + usage["cached"] * tariff["cached_usd_per_million"]
        + usage["output"] * tariff["output_usd_per_million"]
    ) / 1_000_000
    return usd * tariff["thb_per_usd"] * 1000 / usage["requests"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--capped", type=Path, required=True)
    ap.add_argument("--tariff", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("reports/lab5-token-cost.md"))
    a = ap.parse_args()
    base = json.loads(a.baseline.read_text())
    capped = json.loads(a.capped.read_text())
    tariff = json.loads(a.tariff.read_text())
    for key in [
        "model",
        "verified_date",
        "source_url",
        "input_usd_per_million",
        "output_usd_per_million",
        "cached_usd_per_million",
        "thb_per_usd",
        "cache_write_factor",
    ]:
        if key not in tariff:
            raise ValueError("Missing verified tariff field: " + key)
    for report in [base, capped]:
        if report["pass_rate"] != 1:
            raise ValueError("Cost optimization must pass all golden cases")
        if any(x.get("model_version") != tariff["model"] for x in report["recorded_responses"]):
            raise ValueError("Tariff must match the provider-returned exact model version")
    before, after = totals(base), totals(capped)
    b, aft = price(before, tariff), price(after, tariff)
    read = tariff["cached_usd_per_million"] / tariff["input_usd_per_million"]
    write = tariff["cache_write_factor"]
    if not 0 <= read < 1 or write < 1:
        raise ValueError("Invalid cache tariff assumptions")
    breakeven = (write - 1) / (write - read) if write > 1 else 0
    currency = (
        "Native Cloud Billing Catalog THB unit rates; no assumed FX conversion."
        if "input_thb_per_million" in tariff
        else f"Currency conversion: {tariff['thb_per_usd']} THB/USD."
    )
    working = (
        "(fresh input × native THB input rate + cached input × native THB cache rate + output × native THB output rate) / 1,000,000 × 1,000 / requests"
        if "input_thb_per_million" in tariff
        else "(fresh input × USD input rate + cached input × USD cache rate + output × USD output rate) / 1,000,000 × THB/USD × 1,000 / requests"
    )
    content = f"""# Lab 5 — real token cost

Provider tariff: {tariff["source_url"]}, verified {tariff["verified_date"]}; model {tariff["model"]}. {currency} This is a tariff-based usage figure; reconcile invoices and credits separately.

| | Baseline | Output-capped |
|---|---:|---:|
| Requests | {before["requests"]} | {after["requests"]} |
| Provider input tokens | {before["input"]} | {after["input"]} |
| Provider output/thinking tokens | {before["output"]} | {after["output"]} |
| Provider cached input tokens | {before["cached"]} | {after["cached"]} |
| THB per 1,000 requests | {b:.6f} | {aft:.6f} |

Working: {working}. Capped saving: {b - aft:.6f} THB per 1,000; both golden sets passed.

Cache break-even hit rate: (write factor − 1)/(write factor − read factor) = {breakeven:.4%}. Measured hit rate: {after["cache_hits"]}/{after["requests"]} = {after["cache_hits"] / after["requests"]:.4%}. Include cache storage charges separately if applicable; the generic surcharge model does not include storage rent.

Budget defence: At this measured workload the advisory step costs about {b:.6f} THB per 1,000 requests before the output cap and {aft:.6f} afterward, excluding infrastructure, taxes and credits. The cap reduces response length; all tested safety and grounding cases still pass. This small golden set does not guarantee safety on every production input.
"""
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(content)
    print(a.out)


if __name__ == "__main__":
    main()
