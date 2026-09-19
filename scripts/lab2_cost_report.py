"""Summarize observed Lab 2 job durations without presenting estimates as invoices."""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def main():
    ledger = json.loads((REPORTS / "lab2-execution.json").read_text())
    checkpoint = json.loads((REPORTS / "lab2-checkpoint.json").read_text())
    rate = ledger["hourly_thb_upper_bound"]
    rows = []
    for i, item in enumerate(ledger["jobs"]):
        job = json.loads((REPORTS / f"lab2-job-{i}.json").read_text())
        if not job.get("endTime"):
            raise RuntimeError("Cost report requires every submitted job to have ended.")
        def parse(value):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        runtime = (parse(job["endTime"]) - parse(job["startTime"])).total_seconds()
        elapsed = (parse(job["endTime"]) - parse(job["createTime"])).total_seconds()
        rows.append({"job_id": item["id"], "runtime_s": runtime,
                     "elapsed_s_including_queue": elapsed,
                     "runtime_estimate_thb": runtime / 3600 * rate,
                     "elapsed_upper_estimate_thb": elapsed / 3600 * rate})
    summary = {
        "rate_bound_thb_per_hour": rate, "jobs": rows,
        "runtime_estimate_thb": sum(row["runtime_estimate_thb"] for row in rows),
        "elapsed_upper_estimate_thb": sum(row["elapsed_upper_estimate_thb"] for row in rows),
        "fit_estimate_thb": sum(t["metrics"]["cost_thb"] for t in checkpoint["trials"]),
        "study_process_estimate_thb": checkpoint["spent_thb"],
        "actual_billed_thb": None,
    }
    (REPORTS / "lab2-cost.json").write_text(json.dumps(summary, indent=2))
    marker = "\n## Observed execution"
    original = (REPORTS / "lab2-cost.md").read_text().split(marker)[0]
    lines = [marker, "", "| Job | Worker seconds | Create-to-end seconds | Worker estimate THB |",
             "|---|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| {row['job_id'].split('/')[-1]} | {row['runtime_s']:.1f} | "
                     f"{row['elapsed_s_including_queue']:.1f} | {row['runtime_estimate_thb']:.4f} |")
    lines += ["", f"Fit-only estimate: **{summary['fit_estimate_thb']:.6f} THB**.",
              f"Measured study-process estimate: **{summary['study_process_estimate_thb']:.4f} THB**.",
              f"Worker-interval estimate: **{summary['runtime_estimate_thb']:.4f} THB**.",
              f"Conservative create-to-end estimate, including unbilled queue time: "
              f"**{summary['elapsed_upper_estimate_thb']:.4f} THB**.", "",
              "These are different views of the same compute usage; do not add them together.",
              "Actual billed cost is unavailable until billing data is reconciled. "
              "Storage, image retention, operations, logging and egress are additional; "
              "50 THB was reserved for overhead. No serving endpoint was deployed.",
              "The retained models, image and checkpoints support Lab 3; terminated jobs "
              "have no running training workers.", ""]
    (REPORTS / "lab2-cost.md").write_text(original + "\n".join(lines))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
