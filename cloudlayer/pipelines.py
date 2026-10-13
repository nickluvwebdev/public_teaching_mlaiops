"""Translate the neutral Lab 5 DAG to a real conditional KFP specification."""

import os
import re
from pathlib import Path
import yaml

SPEC = Path(__file__).resolve().parents[1] / "pipeline/pipeline.yaml"


def load_spec(path=SPEC):
    raw = os.path.expandvars(path.read_text())
    unresolved = re.findall(r"\$\{[^}]+\}", raw)
    if unresolved:
        raise ValueError("Unresolved pipeline settings: " + ", ".join(unresolved))
    spec = yaml.safe_load(raw)
    names = [s["name"] for s in spec["steps"]]
    if names != ["ingest", "validate", "train", "evaluate", "register", "deploy_staging"]:
        raise ValueError("Unexpected Lab 5 DAG")
    if spec["steps"][4].get("condition") != "gate_decision == 'pass'":
        raise ValueError("Registration must be conditional on gate pass")
    return spec


def compile_gcp(spec):
    from kfp import compiler, dsl

    image = spec["steps"][0]["image"]
    if "@sha256:" not in image:
        raise ValueError("Pipeline image must be digest pinned")

    @dsl.container_component
    def stage(
        name: str,
        configuration: str,
        input_value: str,
        input_info: str,
        value: dsl.OutputPath(str),
        info: dsl.OutputPath(str),
    ):
        return dsl.ContainerSpec(
            image=image,
            command=spec["steps"][0]["command"],
            args=[
                "--stage",
                name,
                "--configuration",
                configuration,
                "--input-value",
                input_value,
                "--input-info",
                input_info,
                "--value-out",
                value,
                "--info-out",
                info,
            ],
        )

    @dsl.pipeline(name=spec["name"])
    def pipeline(configuration: str):
        ingest = stage(name="ingest", configuration=configuration, input_value="", input_info="")
        validate = stage(
            name="validate",
            configuration=configuration,
            input_value=ingest.outputs["value"],
            input_info="",
        )
        train = stage(
            name="train",
            configuration=configuration,
            input_value=validate.outputs["value"],
            input_info="",
        )
        evaluate = stage(
            name="evaluate",
            configuration=configuration,
            input_value=train.outputs["value"],
            input_info=train.outputs["info"],
        )
        with dsl.If(evaluate.outputs["value"] == "pass", name="gate-passed"):
            register = stage(
                name="register",
                configuration=configuration,
                input_value=train.outputs["value"],
                input_info=evaluate.outputs["info"],
            )
            deploy = stage(
                name="deploy_staging",
                configuration=configuration,
                input_value=register.outputs["value"],
                input_info="",
            )
            deploy.set_caching_options(False)
        for task in (ingest, validate, train, evaluate, register):
            task.set_caching_options(False).set_cpu_limit("1").set_memory_limit("1Gi")

    out = SPEC.parent / "compiled.json"
    compiler.Compiler().compile(pipeline, str(out))
    return str(out)


def compile_for(provider, spec=None):
    if provider != "gcp":
        raise NotImplementedError("Only the primary provider's managed pipeline is implemented")
    return compile_gcp(spec or load_spec())
