"""Safety and repeatability at the deployment/teardown boundary."""

from dataclasses import replace
import pytest
from cloudlayer import gcp_run
from src.config import load


def test_deploy_requires_immutable_image_and_version(monkeypatch):
    cfg = replace(load(strict=False), serving_image="example:latest", serving_identity="identity")
    with pytest.raises(ValueError, match="digest"):
        gcp_run.deploy(
            cfg, "projects/example/locations/region/models/model@1", "endpoint", "1cpu-1Gi"
        )
    with pytest.raises(ValueError, match="numeric"):
        gcp_run.deploy(
            cfg, "projects/example/locations/region/models/model@latest", "endpoint", "1cpu-1Gi"
        )


def test_teardown_filters_student_and_lab_and_checks_completion(monkeypatch):
    cfg = replace(load(strict=False), project_id="student-a")
    calls = []
    own = {"metadata": {"name": "own", "labels": cfg.tags(3)}}
    other = {"metadata": {"name": "other", "labels": {**cfg.tags(3), "student": "student-b"}}}
    older = {"metadata": {"name": "lab2", "labels": cfg.tags(2)}}
    remaining = [own, other, older]

    def command(config, *args):
        calls.append(args)
        if args[:3] == ("run", "services", "delete"):
            remaining[:] = [s for s in remaining if s["metadata"]["name"] != args[3]]
            return {}
        return remaining.copy()

    monkeypatch.setattr(gcp_run, "command", command)
    assert gcp_run.teardown(cfg, cfg.tags(3)) == ["own"]
    assert [s["metadata"]["name"] for s in remaining] == ["other", "lab2"]
    assert calls[-1] == ("run", "services", "list")


def test_invalid_traffic_never_reaches_provider(monkeypatch):
    monkeypatch.setattr(gcp_run, "command", lambda *args: pytest.fail("invalid traffic sent"))
    with pytest.raises(ValueError):
        gcp_run.traffic(load(strict=False), "endpoint", {"a": 90, "b": 20})
