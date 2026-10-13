import pytest
from cloudlayer import lab5_stage
from cloudlayer.pipelines import load_spec


def test_rejected_gate_never_calls_registration(monkeypatch):
    class Adapter:
        def register_model(self, *args, **kwargs):
            pytest.fail("registration reached despite rejected gate")

    monkeypatch.setattr(lab5_stage.config, "load", lambda: None)
    monkeypatch.setattr(lab5_stage, "get_adapter", lambda _: Adapter())
    with pytest.raises(ValueError, match="gate did not pass"):
        lab5_stage.run(
            "register", {"environment": {}, "output_key": "lab5/run"}, "model", '{"passed":false}'
        )


def test_compiler_rejects_unconditional_registration(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_IMAGE", "test@sha256:" + "0" * 64)
    monkeypatch.setenv("PROJECT_ID", "test")
    from cloudlayer.pipelines import SPEC

    spec = SPEC.read_text().replace("gate_decision == 'pass'", "true")
    path = tmp_path / "bad.yaml"
    path.write_text(spec)
    with pytest.raises(ValueError, match="conditional"):
        load_spec(path)
