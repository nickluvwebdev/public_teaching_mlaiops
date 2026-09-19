"""Task 1 storage round trip and job failure/identity contracts."""
from dataclasses import replace
from unittest.mock import patch

import pytest

from cloudlayer.base import LocalAdapter
from cloudlayer.gcp import GcpAdapter
from src import config
from src.train import prepare_remote_data, publish_artifacts


def test_remote_input_uses_adapter_and_local_input_is_unchanged(tmp_path):
    cfg = replace(config.load(strict=False), provider="local", data_dir=tmp_path)
    assert prepare_remote_data(cfg, tmp_path) == cfg.raw_path
    source = tmp_path / "input.csv"
    source.write_text("a,b\n1,2\n")
    uri = LocalAdapter(cfg).upload(str(source), "raw/input.csv")
    remote = replace(cfg, training_data_uri=uri)
    downloaded = prepare_remote_data(remote, tmp_path / "worker")
    assert downloaded.read_bytes() == source.read_bytes()


def test_artifacts_round_trip(tmp_path):
    from sklearn.dummy import DummyClassifier
    import mlflow.sklearn

    cfg = replace(config.load(strict=False), provider="local",
                  data_dir=tmp_path, training_output_key="lab2/test")
    model = DummyClassifier(strategy="most_frequent").fit([[0], [1]], [0, 1])
    publish_artifacts(cfg, model, {"seed": 7}, tmp_path)
    output = tmp_path / "_local_blob" / "lab2" / "test"
    assert (output / "metrics.json").read_text().strip() == '{\n  "seed": 7\n}'
    restored = mlflow.sklearn.load_model(str(output / "model"))
    assert restored.predict([[2]]).tolist() == model.predict([[2]]).tolist()


def test_submission_uses_runtime_identity_and_returns_id():
    cfg = replace(config.load(strict=False), blob_uri="gs:" + "//test-bucket/prefix",
                  identity_ref="training-service-account", project_id="test-project")
    with patch("google.cloud.aiplatform.CustomJob") as custom_job:
        custom_job.return_value.resource_name = "projects/test/locations/test/customJobs/1"
        job_id = GcpAdapter(cfg).submit_training("image@sha256:" + "a" * 64, {
            "data_uri": cfg.blob_uri + "/raw/input.csv",
            "git_commit": "abc123", "training_args": ["--seed", "7"],
        })
        assert job_id.endswith("/1")
        custom_job.return_value.submit.assert_called_once_with(
            service_account=cfg.identity_ref, timeout=3600)
        pool = custom_job.call_args.kwargs["worker_pool_specs"][0]
        env = {item["name"]: item["value"] for item in pool["container_spec"]["env"]}
        assert env["TRAINING_DATA_URI"].endswith("/raw/input.csv")
        assert env["TRAINING_OUTPUT_KEY"].startswith("lab2/jobs/")
        assert env["SOURCE_COMMIT"] == "abc123"
        assert pool["container_spec"]["args"] == ["--seed", "7"]


def test_wait_propagates_failure():
    cfg = config.load(strict=False)
    with patch("google.cloud.aiplatform.CustomJob") as custom_job:
        custom_job.get.return_value.state.name = "JOB_STATE_FAILED"
        custom_job.get.return_value.error = "training failed"
        with pytest.raises(RuntimeError, match="training failed"):
            GcpAdapter(cfg).wait_training("job-id")


def test_unpinned_image_rejected():
    with pytest.raises(ValueError, match="digest-pinned"):
        GcpAdapter(config.load(strict=False)).submit_training("image:latest", {})


def test_wait_returns_completed_artifact_location():
    with patch("google.cloud.aiplatform.CustomJob") as custom_job:
        job = custom_job.get.return_value
        job.state.name = "JOB_STATE_SUCCEEDED"
        job.resource_name = "job-id"
        job.gca_resource.job_spec.base_output_directory.output_uri_prefix = "artifact-location"
        result = GcpAdapter(config.load(strict=False)).wait_training("job-id")
        assert result == {"job_id": "job-id", "state": "JOB_STATE_SUCCEEDED",
                          "artifact_uri": "artifact-location"}


def test_spot_submission_omits_flex_start_only_options():
    cfg = replace(config.load(strict=False), blob_uri="gs:" + "//test-bucket/lab2",
                  identity_ref="training-service-account")
    with patch("google.cloud.aiplatform.CustomJob") as custom_job:
        GcpAdapter(cfg).submit_training("image@sha256:" + "a" * 64, {
            "data_uri": cfg.blob_uri + "/input.csv", "git_commit": "abc123",
            "spot": True, "timeout": 900,
        })
        options = custom_job.return_value.submit.call_args.kwargs
        assert options["scheduling_strategy"].name == "SPOT"
        assert options["timeout"] == 900
        assert "max_wait_duration" not in options


def test_registry_requires_exact_version():
    with pytest.raises(ValueError, match="numeric version"):
        GcpAdapter(config.load(strict=False)).download_registered_model("model", "staging", "/tmp/unused")


def test_registration_preserves_all_lineage_fields():
    import json

    lineage = {
        "git_commit": "a" * 40, "data_version": "data-hash.dir",
        "mlflow_run_id": "b" * 32, "training_job_id": "job-123",
        "image_digest": "image@sha256:" + "c" * 64,
        "seed": 20260101, "metric_val": .91, "metric_test": .90,
    }
    adapter = GcpAdapter(config.load(strict=False))

    def download(uri, local):
        from pathlib import Path
        Path(local).write_text(json.dumps(lineage))

    with patch.object(adapter, "download", side_effect=download), patch(
        "google.cloud.aiplatform.Model"
    ) as model:
        model.list.return_value = []
        model.upload.return_value.resource_name = "model-resource"
        model.upload.return_value.version_id = "1"
        assert adapter.register_model("artifact-uri", "test-model") == "model-resource@1"
        options = model.upload.call_args.kwargs
        assert json.loads(options["version_description"]) == lineage
        assert options["version_aliases"] == ["candidate"]
        assert options["serving_container_image_uri"] == lineage["image_digest"]
