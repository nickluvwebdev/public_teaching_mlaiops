"""Generate Lab 2 comparison and a measured, <=200-word selection justification."""
import argparse
import csv
import json
import statistics
from pathlib import Path


def report(state, out):
    if not state.get("complete") or len(state["trials"]) < 14:
        raise ValueError("A complete 12-trial study plus two seed checks is required.")
    trials = state["trials"]
    selected = trials[state["selected_index"]]
    best = max(trials[:12], key=lambda t: t["metrics"]["val_roc_auc"])
    repeats = [selected] + [t for t in trials if t["phase"] == "seed-check"]
    scores = [t["metrics"]["val_roc_auc"] for t in repeats]
    mean, std = statistics.mean(scores), statistics.stdev(scores)
    fit_cost = selected["metrics"]["cost_thb"]
    lines = ["# Lab 2 comparison", "",
             "Selection rule declared before running: choose the fastest measured fit within "
             "0.005 validation ROC-AUC of the best search trial. Test scores do not select the model.", "",
             "| Trial | Phase | Trees | Depth | Leaf | Seed | Validation AUC | Test AUC | Seconds | Estimated fit THB |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for t in trials:
        p, m = t["params"], t["metrics"]
        lines.append(f"| {t['index']} | {t['phase']} | {p['n_estimators']} | {p['max_depth']} | "
                     f"{p['min_samples_leaf']} | {t['seed']} | {m['val_roc_auc']:.6f} | "
                     f"{m['test_roc_auc']:.6f} | {m['duration_s']:.3f} | {m['cost_thb']:.6f} |")
    justification = (
        f"I selected trial {selected['index']} (run {selected['run_id']}) using the predeclared "
        f"cost-aware rule. Its validation ROC-AUC is {selected['metrics']['val_roc_auc']:.6f}; "
        f"the best search score is {best['metrics']['val_roc_auc']:.6f}. "
        f"The selected model is the fastest measured fit within 0.005 of that score. "
        f"Across three model seeds on the same machine-group split, validation AUC averages "
        f"{mean:.6f}, with sample standard deviation {std:.6f} (variance {std**2:.8f}). "
        f"This measures model randomness, not uncertainty across alternative data splits. "
        f"Estimated fit cost is {fit_cost:.6f} THB; one monthly refit has the same fit-only cost "
        f"and twelve cost {12*fit_cost:.6f} THB. Provisioning, tracking, storage, and transfers are "
        f"additional; the separate job-cost report estimates these overheads rather than claiming "
        f"fit time equals the cloud bill. This choice could be wrong if future machine populations "
        f"differ from this held-out split, or if timing noise changes which near-tied fit appears cheapest."
    )
    assert len(justification.split()) <= 200
    lines += ["", "## Selection justification", "", justification, "",
              "## Provenance", "", "```json", json.dumps(selected["lineage"], indent=2), "```", "",
              "## Checkpoint evidence", "", "```json", json.dumps(state["events"], indent=2), "```", "",
              f"Study-process estimated cost including tracking: {state['spent_thb']:.6f} THB.",
              "Rates are estimates, not settled billing. See lab2-cost.md."]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    with out.with_suffix(".csv").open("w", newline="") as handle:
        rows = [{"trial": t["index"], "phase": t["phase"], "run_id": t["run_id"],
                 "seed": t["seed"], **t["params"], **t["metrics"]} for t in trials]
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    out.with_name("lab2-selected.json").write_text(json.dumps(selected, indent=2))
    print(justification)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, default=Path("reports/lab2-checkpoint.json"))
    p.add_argument("--out", type=Path, default=Path("reports/lab2-comparison.md"))
    args = p.parse_args()
    report(json.loads(args.checkpoint.read_text()), args.out)


if __name__ == "__main__":
    main()
