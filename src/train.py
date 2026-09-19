"""Training entry point.

Run locally:      python -m src.train --n-estimators 200 --max-depth 8
Run in Docker:    make reproduce

Every run logs: all hyperparameters, the seed, validation AND test metrics separately,
the data fingerprint, and the Git commit. A metric that cannot be traced to code and
data is not evidence of anything.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

from src import config, data, seeds

def prepare_remote_data(cfg, directory: Path) -> Path:
    """Resolve input through the provider-neutral storage adapter."""
    if not cfg.training_data_uri:
        return cfg.raw_path
    from cloudlayer.factory import get_adapter

    local_path = directory / "sensors.csv"
    get_adapter(cfg).download(cfg.training_data_uri, str(local_path))
    return local_path


def publish_artifacts(cfg, model, result: dict, directory: Path) -> None:
    """Persist a reloadable model and its provenance outside managed compute."""
    if not cfg.training_output_key:
        return
    from cloudlayer.factory import get_adapter

    output = directory / "artifacts"
    output.mkdir()
    mlflow.sklearn.save_model(model, str(output / "model"))
    (output / "metrics.json").write_text(json.dumps(result, indent=2))
    adapter = get_adapter(cfg)
    for path in sorted(output.rglob("*")):
        if path.is_file():
            key = f"{cfg.training_output_key.rstrip('/')}/{path.relative_to(output).as_posix()}"
            adapter.upload(str(path), key)


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, cwd=config.REPO_ROOT,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ITCS355 Lab 1 — reproducible training")
    p.add_argument("--n-estimators", type=int, default=200)
    p.add_argument("--max-depth", type=int, default=8)
    p.add_argument("--min-samples-leaf", type=int, default=5)
    p.add_argument("--seed", type=int, default=seeds.DEFAULT_SEED)
    p.add_argument("--experiment", default="itcs355-lab1")
    p.add_argument("--run-name", default=None)
    p.add_argument("--metrics-out", type=Path, default=None,
                   help="Write final metrics as JSON. Used by `make verify`.")
    return p.parse_args()


def train(args, directory: Path) -> None:
    cfg = config.load(strict=False)
    seed = seeds.set_all(args.seed)

    raw_path = prepare_remote_data(cfg, directory)
    df = data.load_raw(raw_path)
    fingerprint = data.data_fingerprint(raw_path)
    train_df, val_df, test_df = data.split(df, seed=seed)

    mlflow.set_tracking_uri(cfg.mlflow_tracking_uri)
    mlflow.set_experiment(args.experiment)

    with mlflow.start_run(run_name=args.run_name):
        mlflow.log_params({
            "n_estimators": args.n_estimators,
            "max_depth": args.max_depth,
            "min_samples_leaf": args.min_samples_leaf,
            "seed": seed,
            "n_features": len(data.FEATURES),
        })
        # Provenance. This is what makes the metric traceable.
        mlflow.set_tags({
            "git_commit": cfg.source_commit or git_commit(),
            "data_fingerprint": fingerprint,
            "split_strategy": "group_by_machine_id",
            "n_train_rows": len(train_df),
            "n_val_rows": len(val_df),
            "n_test_rows": len(test_df),
        })

        model = RandomForestClassifier(
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            min_samples_leaf=args.min_samples_leaf,
            random_state=seed,
            n_jobs=-1,
        )
        model.fit(train_df[data.FEATURES], train_df[data.TARGET])

        metrics: dict[str, float] = {}
        for name, part in (("val", val_df), ("test", test_df)):
            proba = model.predict_proba(part[data.FEATURES])[:, 1]
            metrics[f"{name}_roc_auc"] = float(roc_auc_score(part[data.TARGET], proba))
            metrics[f"{name}_pr_auc"] = float(average_precision_score(part[data.TARGET], proba))
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(model, name="model")

        result = {
            "seed": seed, "data_fingerprint": fingerprint, **metrics,
            "git_commit": cfg.source_commit or git_commit(),
            "mlflow_run_id": mlflow.active_run().info.run_id,
            "params": vars(args) | {"metrics_out": str(args.metrics_out) if args.metrics_out else None},
        }
        publish_artifacts(cfg, model, result, directory)
        print(json.dumps(result, indent=2))
        if args.metrics_out:
            args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
            args.metrics_out.write_text(json.dumps(
                {"seed": seed, "data_fingerprint": fingerprint, **metrics}, indent=2))


def main() -> None:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="itcs355-training-") as directory:
        train(args, Path(directory))


if __name__ == "__main__":
    main()
