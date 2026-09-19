"""Reload an exact provider-registry version and score held-out rows."""
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mlflow.sklearn

from cloudlayer.factory import get_adapter
from src import config, data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--rows", type=int, default=5)
    p.add_argument("--out", type=Path, default=Path("reports/lab2-reload.json"))
    args = p.parse_args()
    cfg = config.load()
    adapter = get_adapter(cfg)
    with tempfile.TemporaryDirectory(prefix="registry-reload-") as directory:
        info = adapter.download_registered_model(args.name, args.version, directory)
        lineage = json.loads((Path(directory) / "lineage.json").read_text())
        if data.data_fingerprint(cfg.raw_path) != lineage["data_fingerprint"]:
            raise ValueError("Local held-out data differs from the registered model's data.")
        model = mlflow.sklearn.load_model(directory)
        _, _, test = data.split(data.load_raw(cfg.raw_path), seed=int(lineage["split_seed"]))
        sample = test.head(args.rows)
        probabilities = model.predict_proba(sample[data.FEATURES])[:, 1]
        result = {**info, "lineage": lineage, "predictions": [
            {"reading_id": int(rid), "probability": float(prob)}
            for rid, prob in zip(sample[data.ID], probabilities)
        ]}
        if len(result["predictions"]) != args.rows:
            raise ValueError("Insufficient held-out rows.")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        print("PASS: exact registry version downloaded into an empty directory and scored held-out rows")


if __name__ == "__main__":
    main()
