"""Remove only explicitly named Lab 4 compute, schedule and alert resources."""
import json
import subprocess
from pathlib import Path
from cloudlayer.gcp_monitoring import session


def teardown(cfg):
    receipt = Path(__file__).resolve().parents[1] / "reports/lab4-resources.json"
    if not receipt.exists():
        raise ValueError("Lab 4 resource receipt required for scoped teardown")
    resources = json.loads(receipt.read_text())
    if resources["project_id"] != cfg.project_id:
        raise ValueError("Project mismatch")
    deleted = []
    commands = [
        ["scheduler", "jobs", "delete", "itcs355-lab4-drift", "--location", cfg.region],
        ["run", "jobs", "delete", "itcs355-lab4-drift", "--region", cfg.region],
        ["run", "services", "delete", "itcs355-lab4", "--region", cfg.region],
    ]
    for args in commands:
        result = subprocess.run(["gcloud", *args, "--project", cfg.project_id, "--quiet"], capture_output=True, text=True)
        if result.returncode and not any(s in result.stderr.lower() for s in ["not found", "not_found", "does not exist"]):
            raise RuntimeError(result.stderr)
        deleted.append(" ".join(args[:4]))
    for key in ["alert_policy", "notification_channel"]:
        name = resources.get(key)
        if name:
            r = session().delete("https://monitoring.googleapis.com/v3/" + name, timeout=30)
            if r.status_code not in (200, 204, 404):
                r.raise_for_status()
            deleted.append(name)
    # Prove scheduler and compute removal, rather than trusting delete output.
    for args in [["scheduler", "jobs", "list", "--location", cfg.region],
                 ["run", "jobs", "list", "--region", cfg.region],
                 ["run", "services", "list", "--region", cfg.region]]:
        output = subprocess.check_output(["gcloud", *args, "--project", cfg.project_id, "--format=json"], text=True)
        if "itcs355-lab4" in output:
            raise RuntimeError("Lab 4 resource still present")
    return deleted
