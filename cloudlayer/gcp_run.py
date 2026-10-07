"""Authenticated Cloud Run implementation. Provider CLI details stay in cloudlayer."""

from __future__ import annotations
import json
import os
import subprocess
from urllib.request import Request, urlopen


def command(cfg, *args):
    result = subprocess.run(
        [
            "gcloud",
            *args,
            "--project",
            cfg.project_id,
            "--region",
            cfg.region,
            "--format=json",
            "--quiet",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-4000:])
    return json.loads(result.stdout) if result.stdout.strip() else {}


def describe(cfg, endpoint):
    return command(cfg, "run", "services", "describe", endpoint)


def deploy(cfg, model_ref, endpoint, instance):
    name, version = model_ref.rsplit("@", 1)
    if not version.isdigit() or not name.startswith("projects/"):
        raise ValueError("Use a full registry resource and exact numeric version")
    if "@sha256:" not in cfg.serving_image or not cfg.serving_identity:
        raise ValueError("Set SERVING_IMAGE to a digest and SERVING_IDENTITY_REF")
    if instance not in {"1cpu-1Gi", "2cpu-1Gi"}:
        raise ValueError("Supported sizes: 1cpu-1Gi, 2cpu-1Gi")
    env = {
        "CLOUD_PROVIDER": "gcp",
        "PROJECT_ID": cfg.project_id,
        "REGION": cfg.region,
        "MODEL_REGISTRY_NAME": name,
        "MODEL_VERSION": version,
    }
    options = []
    if cfg.serving_revision:
        options += ["--revision-suffix", cfg.serving_revision]
    if cfg.serving_no_traffic:
        options += ["--no-traffic", "--tag", "candidate"]
    command(
        cfg,
        "run",
        "deploy",
        endpoint,
        "--image",
        cfg.serving_image,
        "--service-account",
        cfg.serving_identity,
        "--no-allow-unauthenticated",
        "--cpu",
        instance[0],
        "--memory",
        "1Gi",
        "--min-instances",
        "0",
        "--max-instances",
        "1",
        "--concurrency",
        "80",
        "--timeout",
        "60",
        "--no-cpu-boost",
        "--no-deploy-health-check",
        "--startup-probe",
        "httpGet.path=/ready,httpGet.port=8080,periodSeconds=2,timeoutSeconds=1,failureThreshold=120",
        "--set-env-vars",
        ",".join(f"{k}={v}" for k, v in env.items()),
        "--labels",
        ",".join(f"{k}={v}" for k, v in cfg.tags(cfg.serving_lab).items()),
        *options,
    )
    return describe(cfg, endpoint)["status"]["url"]


def identity_token():
    if os.environ.get("SERVING_ID_TOKEN"):
        return os.environ["SERVING_ID_TOKEN"]
    return subprocess.run(
        ["gcloud", "auth", "print-identity-token"], check=True, capture_output=True, text=True
    ).stdout.strip()


def invoke(cfg, endpoint, payload):
    url = endpoint if endpoint.startswith("https://") else describe(cfg, endpoint)["status"]["url"]
    path = "/predict/batch" if "rows" in payload else "/predict"
    request = Request(
        url + path,
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + identity_token(), "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=90) as response:
        return json.load(response)


def traffic(cfg, endpoint, weights):
    if sum(weights.values()) != 100 or any(v < 0 for v in weights.values()):
        raise ValueError("Traffic weights must be nonnegative and sum to 100")
    command(
        cfg,
        "run",
        "services",
        "update-traffic",
        endpoint,
        "--to-revisions",
        ",".join(f"{k}={v}" for k, v in weights.items()),
    )
    return describe(cfg, endpoint)


def teardown(cfg, tags):
    if tags != cfg.tags(3):
        raise ValueError("Only this student's Lab 3 services can be removed")
    services = command(cfg, "run", "services", "list")
    names = [
        s["metadata"]["name"]
        for s in services
        if all(s["metadata"].get("labels", {}).get(k) == v for k, v in tags.items())
    ]
    for name in names:
        command(cfg, "run", "services", "delete", name)
    remaining = command(cfg, "run", "services", "list")
    if any(s["metadata"]["name"] in names for s in remaining):
        raise RuntimeError("Teardown not confirmed")
    return names
