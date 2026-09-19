"""Resumable, budgeted Lab 2 study with durable per-trial evidence."""
from __future__ import annotations

import argparse
import itertools
import json
import sqlite3
import tempfile
import time
from pathlib import Path

import mlflow
import mlflow.sklearn
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

from cloudlayer.factory import get_adapter
from src import config, data, seeds
from src.train import git_commit, prepare_remote_data

SEARCH_SPACE = {"n_estimators": [100, 300], "max_depth": [4, 8, 12],
                "min_samples_leaf": [1, 5]}


def grid(space):
    return [dict(zip(space, values)) for values in itertools.product(*space.values())]


def choose(trials, tolerance=0.005):
    """Predeclared rule: cheapest fit within 0.5 percentage points of best validation AUC."""
    best = max(t["metrics"]["val_roc_auc"] for t in trials)
    eligible = [t for t in trials if t["metrics"]["val_roc_auc"] >= best - tolerance]
    return min(eligible, key=lambda t: (t["metrics"]["duration_s"], t["index"]))


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trials", type=int, default=12)
    p.add_argument("--budget-thb", type=float, default=150)
    p.add_argument("--hourly-thb", type=float, required=True,
                   help="Verified rate or explicitly conservative upper bound.")
    p.add_argument("--instance", default="n1-standard-4")
    p.add_argument("--spot", action="store_true")
    p.add_argument("--seed", type=int, default=seeds.DEFAULT_SEED)
    p.add_argument("--experiment", default="itcs355-lab2")
    p.add_argument("--study-key", required=True)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--interrupt-after", type=int, default=0,
                   help="Controlled failure after durable checkpoint; evidence is labeled simulated.")
    return p.parse_args()


def run(args, work: Path):
    cfg = config.load(strict=False)
    adapter = get_adapter(cfg)
    raw = prepare_remote_data(cfg, work)
    fingerprint = data.data_fingerprint(raw)
    commit = cfg.source_commit or git_commit()
    identity = {"git_commit": commit, "data_fingerprint": fingerprint,
                "data_version": cfg.data_version, "image_digest": cfg.image_digest,
                "seed": args.seed, "grid": SEARCH_SPACE, "trials": args.trials,
                "hourly_thb": args.hourly_thb, "instance": args.instance, "spot": args.spot}
    db = work / "mlflow.db"
    state = {"identity": identity, "trials": [], "spent_thb": 0.0, "events": []}
    if args.resume:
        adapter.download(f"{cfg.blob_uri.rstrip('/')}/{args.study_key}/checkpoint.json",
                         str(work / "checkpoint.json"))
        state = json.loads((work / "checkpoint.json").read_text())
        if state["identity"] != identity:
            raise ValueError("Checkpoint code/data/image/search/rate differs; use a new study key.")
        adapter.download(f"{cfg.blob_uri.rstrip('/')}/{args.study_key}/mlflow.db", str(db))
        state["events"].append({"event": "resumed", "completed": len(state["trials"])})
        print(f"RESUMED: {len(state['trials'])} completed trials will be skipped", flush=True)
    mlflow.set_tracking_uri(f"sqlite:///{db}")
    experiment = mlflow.get_experiment_by_name(args.experiment)
    if experiment is None:
        experiment_id = mlflow.create_experiment(
            args.experiment,
            artifact_location=f"{cfg.blob_uri.rstrip('/')}/{args.study_key}/mlflow-artifacts",
        )
    else:
        experiment_id = experiment.experiment_id
    mlflow.set_experiment(experiment_id=experiment_id)
    train_df, val_df, test_df = data.split(data.load_raw(raw), seed=args.seed)
    job_id = adapter.runtime_job_id()
    session_start = time.monotonic()
    prior_spend = state["spent_thb"]

    def checkpoint():
        state["spent_thb"] = prior_spend + (time.monotonic() - session_start) / 3600 * args.hourly_thb
        with sqlite3.connect(db) as source, sqlite3.connect(work / "snapshot.db") as dest:
            source.backup(dest)
        adapter.upload(str(work / "snapshot.db"), f"{args.study_key}/mlflow.db")
        (work / "checkpoint.json").write_text(json.dumps(state, indent=2))
        adapter.upload(str(work / "checkpoint.json"), f"{args.study_key}/checkpoint.json")

    if args.trials != 12:
        raise ValueError("This study requires all 12 grid configurations.")
    candidates = [(p, args.seed, "search") for p in grid(SEARCH_SPACE)]
    index = 0
    while index < 14:
        if index == 12:
            selected = choose(state["trials"][:12])
            candidates.extend((selected["params"], args.seed + offset, "seed-check")
                              for offset in (1, 2))
            state["selected_index"] = selected["index"]
        if index < len(state["trials"]):
            index += 1
            continue
        # Reserve ten minutes at the conservative rate for the next trial and uploads.
        projected = prior_spend + (time.monotonic() - session_start) / 3600 * args.hourly_thb
        if projected + args.hourly_thb / 6 > args.budget_thb:
            checkpoint()
            raise RuntimeError("Budget reserve reached before the study completed.")
        params, seed, phase = candidates[index]
        seeds.set_all(seed)
        started = time.monotonic()
        with mlflow.start_run(run_name=f"trial-{index:02d}") as active:
            model = RandomForestClassifier(random_state=seed, n_jobs=-1, **params)
            model.fit(train_df[data.FEATURES], train_df[data.TARGET])
            metrics = {}
            for split, part in (("val", val_df), ("test", test_df)):
                proba = model.predict_proba(part[data.FEATURES])[:, 1]
                metrics[f"{split}_roc_auc"] = float(roc_auc_score(part[data.TARGET], proba))
                metrics[f"{split}_pr_auc"] = float(average_precision_score(part[data.TARGET], proba))
            metrics["duration_s"] = time.monotonic() - started
            metrics["cost_thb"] = metrics["duration_s"] / 3600 * args.hourly_thb
            lineage = {"git_commit": commit, "data_version": cfg.data_version,
                       "data_fingerprint": fingerprint, "mlflow_run_id": active.info.run_id,
                       "training_job_id": job_id, "image_digest": cfg.image_digest,
                       "seed": seed, "split_seed": args.seed,
                       "metric_val": metrics["val_roc_auc"], "metric_test": metrics["test_roc_auc"]}
            mlflow.log_params({**params, "seed": seed, "split_seed": args.seed,
                               "instance": args.instance, "spot": args.spot,
                               "hourly_thb": args.hourly_thb})
            mlflow.log_metrics(metrics)
            mlflow.set_tags({**lineage, "lab": "2", "phase": phase, "study_key": args.study_key})
            info = mlflow.sklearn.log_model(
                model, name="model", input_example=train_df[data.FEATURES].head(2),
                pip_requirements=[f"scikit-learn=={sklearn.__version__}"],
            )
            # Standalone MLflow format for provider registry import and exact-version reload.
            model_dir = work / f"model-{index:02d}"
            mlflow.sklearn.save_model(model, str(model_dir),
                                     pip_requirements=[f"scikit-learn=={sklearn.__version__}"])
            (model_dir / "lineage.json").write_text(json.dumps(lineage, indent=2))
            model_key = f"{args.study_key}/models/trial-{index:02d}"
            for path in sorted(model_dir.rglob("*")):
                if path.is_file():
                    adapter.upload(str(path), f"{model_key}/{path.relative_to(model_dir).as_posix()}")
            result = {"index": index, "phase": phase, "params": params, "seed": seed,
                      "run_id": active.info.run_id, "metrics": metrics, "lineage": lineage,
                      "model_uri": f"{cfg.blob_uri.rstrip('/')}/{model_key}",
                      "mlflow_model_uri": info.model_uri}
        state["trials"].append(result)
        state["events"].append({"event": "trial_completed", "index": index, "job_id": job_id})
        checkpoint()
        print(json.dumps(result), flush=True)
        if args.interrupt_after and len(state["trials"]) == args.interrupt_after:
            state["events"].append({"event": "controlled_interruption", "completed": len(state["trials"])})
            checkpoint()
            print("CONTROLLED INTERRUPTION: exiting 75 after durable checkpoint", flush=True)
            return 75
        index += 1
    state["complete"] = True
    checkpoint()
    print(f"STUDY COMPLETE: {len(state['trials'])} trials; selected {state['selected_index']}", flush=True)
    return 0


def main():
    args = parse_args()
    if args.hourly_thb <= 0 or not 0 < args.budget_thb <= 150:
        raise ValueError("Supply a positive hourly estimate and a budget no larger than 150 THB.")
    with tempfile.TemporaryDirectory(prefix="itcs355-study-") as directory:
        return run(args, Path(directory))


if __name__ == "__main__":
    raise SystemExit(main())
