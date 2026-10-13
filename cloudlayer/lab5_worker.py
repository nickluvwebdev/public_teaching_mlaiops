"""Bounded managed training worker; checkpoint artifacts and immutable lineage."""

import hashlib
import json
from pathlib import Path
import tempfile
import mlflow
import mlflow.sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from cloudlayer.factory import get_adapter
from src import config, data


def main():
    cfg = config.load(strict=False)
    adapter = get_adapter(cfg)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        raw = root / "sensors.csv"
        adapter.download(cfg.training_data_uri, str(raw))
        train, val, test = data.split(data.load_raw(raw), seed=20260101)
        model = make_pipeline(
            StandardScaler(), LogisticRegression(C=1.0, max_iter=1000, random_state=20260101)
        )
        model.fit(train[data.FEATURES], train[data.TARGET])
        metrics = {
            name + "_roc_auc": float(
                roc_auc_score(part[data.TARGET], model.predict_proba(part[data.FEATURES])[:, 1])
            )
            for name, part in [("val", val), ("test", test)]
        }
        mlflow.set_tracking_uri("sqlite:///" + str(root / "tracking.db"))
        mlflow.set_experiment("itcs355-lab5")
        with mlflow.start_run() as tracking:
            mlflow.log_params(
                {
                    "model_type": "standardized_logistic_regression",
                    "C": 1.0,
                    "max_iter": 1000,
                    "seed": 20260101,
                }
            )
            mlflow.log_metrics(metrics)
            mlflow.set_tags({"git_commit": cfg.source_commit, "data_version": cfg.data_version})
            run_id = tracking.info.run_id
        artifact = root / "model"
        mlflow.sklearn.save_model(model, str(artifact))
        lineage = {
            "git_commit": cfg.source_commit,
            "data_version": cfg.data_version,
            "mlflow_run_id": run_id,
            "training_job_id": adapter.runtime_job_id(),
            "image_digest": cfg.image_digest,
            "seed": 20260101,
            "split_seed": 20260101,
            "data_fingerprint": data.data_fingerprint(raw),
            "metric_val": metrics["val_roc_auc"],
            "metric_test": metrics["test_roc_auc"],
        }
        (artifact / "lineage.json").write_text(json.dumps(lineage, indent=2))
        (artifact / "metrics.json").write_text(json.dumps(metrics))
        scaler, classifier = model.steps[0][1], model.steps[1][1]
        (artifact / "portable-weights.json").write_text(json.dumps({
            "features": data.FEATURES, "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(),
            "coefficients": classifier.coef_[0].tolist(), "intercept": float(classifier.intercept_[0])}))
        manifest = {
            f.relative_to(artifact).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in artifact.rglob("*")
            if f.is_file()
        }
        (artifact / "artifact-manifest.json").write_text(json.dumps(manifest))
        for f in artifact.rglob("*"):
            if f.is_file():
                adapter.upload(
                    str(f), cfg.training_output_key + "/" + f.relative_to(artifact).as_posix()
                )
        adapter.upload(str(root / "tracking.db"), cfg.training_output_key + "/tracking.db")
        print(json.dumps({"event": "checkpoint_complete", "lineage": lineage}))


if __name__ == "__main__":
    main()
