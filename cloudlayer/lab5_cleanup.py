"""Remove only receipt-listed Lab 5 access and secondary resources."""

import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from google.cloud import storage
from src import config


def command(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode and not any(
        x in result.stderr.lower()
        for x in [
            "not found",
            "not_found",
            "does not exist",
            "nosuchentity",
            "resourcenotfoundexception",
            "nosuchbucket",
            "not present",
        ]
    ):
        raise RuntimeError(result.stderr)
    return result


def access(cfg):
    path = config.REPO_ROOT / "reports/lab5-access.json"
    if not path.exists():
        return []
    receipt = json.loads(path.read_text())
    if receipt["project"] != cfg.project_id:
        raise ValueError("Access receipt project mismatch")
    removed = []
    for original in reversed(receipt["grants"]):
        args = list(original)
        args[args.index("add-iam-policy-binding")] = "remove-iam-policy-binding"
        command(["gcloud", *args, "--project=" + cfg.project_id, "--quiet", "--format=none"])
        removed.append(args[:4])
    if receipt.get("created_ci"):
        command(
            [
                "gcloud",
                "iam",
                "service-accounts",
                "delete",
                receipt["ci"],
                "--project=" + cfg.project_id,
                "--quiet",
            ]
        )
    out = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "removed": removed,
        "deleted_lab_ci_identity": receipt.get("created_ci", False),
    }
    (config.REPO_ROOT / "reports/lab5-evidence/access-cleanup.json").write_text(
        json.dumps(out, indent=2)
    )
    return removed


def secondary(cfg):
    path = config.REPO_ROOT / "reports/lab5-aws-resources.json"
    if not path.exists():
        return {}
    receipt = json.loads(path.read_text())
    base = [
        str(Path.home() / ".local/bin/aws"),
        "--profile",
        "lab5-login",
        "--region",
        receipt["region"],
        "--no-cli-pager",
    ]
    who = json.loads(command([*base, "sts", "get-caller-identity"]).stdout)
    if who["Account"] != receipt["account"]:
        raise ValueError("Secondary account mismatch")
    function = receipt["function"]
    role = receipt["role"]
    bucket = receipt["bucket"]
    if not all(x.startswith("itcs355-lab5") for x in [function, role, bucket]):
        raise ValueError("Unexpected cleanup target")
    if receipt.get("created_function"):
        command([*base, "lambda", "delete-function", "--function-name", function])
    command([*base, "logs", "delete-log-group", "--log-group-name", "/aws/lambda/" + function])
    if receipt.get("created_bucket"):
        command([*base, "s3", "rm", "s3://" + bucket, "--recursive"])
        command([*base, "s3api", "delete-bucket", "--bucket", bucket])
    if receipt.get("created_role"):
        command(
            [
                *base,
                "iam",
                "delete-role-policy",
                "--role-name",
                role,
                "--policy-name",
                "exact-model-and-function-logs",
            ]
        )
        command([*base, "iam", "delete-role", "--role-name", role])
    functions = json.loads(command([*base, "lambda", "list-functions"]).stdout)
    assert not any(x["FunctionName"] == function for x in functions["Functions"])
    buckets = json.loads(command([*base, "s3api", "list-buckets"]).stdout)
    assert not any(x["Name"] == bucket for x in buckets["Buckets"])
    result = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "remaining_lab_functions": [],
        "remaining_lab_buckets": [],
        "deleted_role": role,
    }
    (config.REPO_ROOT / "reports/lab5-evidence/secondary-cleanup.json").write_text(
        json.dumps(result, indent=2)
    )
    return result


def pipeline_bucket(cfg):
    path = config.REPO_ROOT / "reports/lab5-access.json"
    if not path.exists():
        return None
    receipt = json.loads(path.read_text())
    name = receipt.get("created_pipeline_bucket")
    if not name:
        return None
    if receipt["project"] != cfg.project_id or not name.startswith("itcs355-lab5-pipeline-"):
        raise ValueError("Unexpected pipeline bucket target")
    client = storage.Client(project=cfg.project_id)
    bucket = client.bucket(name)
    if not bucket.exists():
        return name
    # Pipeline models are in the original course bucket, not this disposable execution bucket.
    for blob in client.list_blobs(name):
        blob.delete()
    bucket.delete()
    return name


def teardown_all(cfg):
    from cloudlayer.lab5_operations import operate

    result = {"primary": operate(cfg, "teardown")}
    result["secondary"] = secondary(cfg)
    result["removed_access"] = access(cfg)
    result["removed_pipeline_bucket"] = pipeline_bucket(cfg)
    return result
