"""Exercise real training, durable checkpoint restore, and unchanged-trial skipping offline."""
import json
import shutil
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import config, tune
from scripts.compare_runs import report


def test_interrupted_study_resumes_without_duplicate_trials(tmp_path, monkeypatch):
    cloud = tmp_path / "cloud"
    cloud.mkdir()
    cfg = replace(config.load(strict=False), provider="local",
                  blob_uri=cloud.as_uri(), source_commit="test-code",
                  image_digest="test-image", data_version="test-data")
    monkeypatch.setattr(tune.config, "load", lambda **kwargs: cfg)

    class Storage:
        def upload(self, local, key):
            target = cloud / key
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local, target)
            return target.as_uri()

        def download(self, uri, local):
            Path(local).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(uri.removeprefix("file://"), local)

        def runtime_job_id(self):
            return "offline-test-job"

    monkeypatch.setattr(tune, "get_adapter", lambda cfg: Storage())
    args = SimpleNamespace(trials=12, budget_thb=150, hourly_thb=20,
                           instance="test", spot=True, seed=20260101,
                           experiment="lab2-offline-test", study_key="study",
                           resume=False, interrupt_after=3)
    first = tmp_path / "first"
    first.mkdir()
    assert tune.run(args, first) == 75
    initial = json.loads((cloud / "study/checkpoint.json").read_text())
    assert len(initial["trials"]) == 3
    args.resume = True
    args.interrupt_after = 0
    second = tmp_path / "second"
    second.mkdir()
    assert tune.run(args, second) == 0
    final = json.loads((cloud / "study/checkpoint.json").read_text())
    assert len(final["trials"]) == 14
    assert final["trials"][:3] == initial["trials"]
    assert len({t["run_id"] for t in final["trials"]}) == 14
    assert final["complete"]
    assert any(e["event"] == "resumed" and e["completed"] == 3 for e in final["events"])
    report(final, tmp_path / "comparison.md")
    assert (tmp_path / "comparison.csv").exists()
    assert all(t["lineage"]["split_seed"] == args.seed for t in final["trials"])
    cfg_changed = replace(cfg, source_commit="different-code")
    monkeypatch.setattr(tune.config, "load", lambda **kwargs: cfg_changed)
    third = tmp_path / "third"
    third.mkdir()
    with pytest.raises(ValueError, match="differs"):
        tune.run(args, third)


def test_selection_ignores_test_scores():
    trials = [
        {"index": 0, "metrics": {"val_roc_auc": .90, "test_roc_auc": .99, "duration_s": 9}},
        {"index": 1, "metrics": {"val_roc_auc": .897, "test_roc_auc": .50, "duration_s": 2}},
        {"index": 2, "metrics": {"val_roc_auc": .88, "test_roc_auc": 1, "duration_s": 1}},
    ]
    assert tune.choose(trials)["index"] == 1
