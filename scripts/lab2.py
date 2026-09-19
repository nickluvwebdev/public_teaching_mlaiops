"""Run Lab 2 cloud stages explicitly and retain an execution ledger."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yaml

from cloudlayer.factory import get_adapter
from src import config

LEDGER = config.REPO_ROOT / "reports/lab2-execution.json"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=["prepare", "submit", "resume", "sync", "register", "promote", "teardown"])
    p.add_argument("--image-uri")
    args = p.parse_args()
    cfg = config.load()
    adapter = get_adapter(cfg)
    state = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
    if args.stage == "prepare":
        if state:
            raise ValueError("An execution ledger already exists; do not overwrite prior evidence.")
        if not args.image_uri or "@sha256:" not in args.image_uri:
            raise ValueError("Supply the freshly rebuilt digest-pinned image.")
        state = {
            "image_uri": args.image_uri,
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "data_version": yaml.safe_load((config.REPO_ROOT / "data/raw.dvc").read_text())["outs"][0]["md5"],
            "study_key": "lab2/studies/" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "hourly_thb_upper_bound": 20.0, "budget_thb": 150, "jobs": [],
        }
        state["data_uri"] = adapter.upload(str(cfg.raw_path), state["study_key"] + "/data/sensors.csv")
    elif not state:
        raise ValueError("Run prepare first.")
    elif args.stage in ("submit", "resume"):
        if len(state["jobs"]) >= 6:
            raise ValueError("Six-job safety cap reached. Review total spend before more submissions.")
        train_args = ["--study-key", state["study_key"], "--hourly-thb", "20",
                      "--budget-thb", "100", "--instance", "n1-standard-4", "--spot"]
        train_args += ["--interrupt-after", "3"] if args.stage == "submit" else ["--resume"]
        spec = {"module": "src.tune", "spot": True, "timeout": 900,
                "git_commit": state["git_commit"], "data_version": state["data_version"],
                "data_uri": state["data_uri"], "training_args": train_args,
                "output_key": state["study_key"] + "/vertex"}
        job_id = adapter.submit_training(state["image_uri"], spec)
        state["jobs"].append({"id": job_id, "stage": args.stage,
                              "submitted_at": datetime.now(timezone.utc).isoformat()})
        print("SUBMITTED", job_id)
    elif args.stage == "sync":
        for remote, local in [("checkpoint.json", "lab2-checkpoint.json"), ("mlflow.db", "lab2-mlflow.db")]:
            adapter.download(f"{cfg.blob_uri.rstrip('/')}/{state['study_key']}/{remote}",
                             str(config.REPO_ROOT / "reports" / local))
    elif args.stage == "register":
        selected = json.loads((config.REPO_ROOT / "reports/lab2-selected.json").read_text())
        if state.get("model_ref"):
            raise ValueError("Model already registered in this execution.")
        state["model_ref"] = adapter.register_model(selected["model_uri"], cfg.model_registry_name)
        print("REGISTERED", state["model_ref"])
    elif args.stage == "promote":
        adapter.promote_model(state["model_ref"], "staging")
        state["promotion"] = "staging"
    elif args.stage == "teardown":
        state["cancelled_jobs"] = adapter.teardown(cfg.tags(2))
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
