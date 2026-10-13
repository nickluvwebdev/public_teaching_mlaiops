"""Executable pipeline stages; inputs/outputs are durable, not shared container paths."""

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import tempfile
from cloudlayer.factory import get_adapter
from src import config
from scripts.evaluation_gate import decision


def run(stage, settings, value="", info=""):
    for key, val in settings["environment"].items():
        os.environ[key] = str(val)
    cfg = config.load()
    adapter = get_adapter(cfg)
    prefix = settings["output_key"]
    if stage == "ingest":
        subprocess.run(["python", "scripts/make_dataset.py", "--seed", "20260101"], check=True)
        return adapter.upload(str(cfg.raw_path), prefix + "/data/sensors.csv"), ""
    if stage == "validate":
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw" / "sensors.csv"
            adapter.download(value, str(raw))
            env = {**os.environ, "DATA_DIR": tmp}
            subprocess.run(["pytest", "-q", "tests/test_data.py"], env=env, check=True)
        return value, ""
    if stage == "train":
        job = adapter.submit_training(
            settings["training_image"],
            {
                "module": "cloudlayer.lab5_worker",
                "data_uri": value,
                "output_key": prefix + "/model",
                "git_commit": settings["source_commit"],
                "data_version": settings["data_version"],
                "spot": True,
                "timeout": 600,
                "lab": 5,
                "run_id": settings["run_id"],
            },
        )
        adapter.wait_training(job)
        return cfg.blob_uri.rstrip("/") + "/" + prefix + "/model", json.dumps({"job": job})
    if stage == "evaluate":
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "metrics.json"
            adapter.download(value + "/metrics.json", str(f))
            metric = json.loads(f.read_text())["val_roc_auc"]
        incumbent = adapter.production_metric("val_roc_auc")
        passed, reason = decision(metric, incumbent)
        result = {"passed": passed, "reason": reason, "candidate": metric, "incumbent": incumbent}
        print(json.dumps(result))
        return "pass" if passed else "fail", json.dumps(result)
    if stage == "register":
        if not json.loads(info).get("passed"):
            raise ValueError("Registration refused: gate did not pass")
        return adapter.register_model(value, cfg.model_registry_name, lab=5), ""
    if stage == "deploy_staging":
        from cloudlayer.lab5_deploy import deploy

        serving = replace(cfg, serving_lab=5)
        return deploy(serving, value, settings["endpoint"], settings["pipeline_identity"]), ""
    raise ValueError("Unknown stage")


def main():
    ap = argparse.ArgumentParser()
    for name in ["stage", "configuration", "input-value", "input-info", "value-out", "info-out"]:
        ap.add_argument("--" + name, required=True)
    a = ap.parse_args()
    value, info = run(a.stage, json.loads(a.configuration), a.input_value, a.input_info)
    for filename, content in [(a.value_out, value), (a.info_out, info)]:
        f = Path(filename)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)


if __name__ == "__main__":
    main()
