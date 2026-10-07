"""Create Lab 4 monitoring resources after administrator identity setup.

No IAM grants are changed here. Run only for the explicitly authorized lab exercise.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import load
from cloudlayer.gcp_monitoring import session

p = argparse.ArgumentParser()
p.add_argument("--email", required=True)
a = p.parse_args()
cfg = load()
root = Path(__file__).resolve().parents[1]
receipt = root / "reports/lab4-resources.json"
resources = json.loads(receipt.read_text())
project = "projects/" + cfg.project_id
api = "https://monitoring.googleapis.com"
def save():
    receipt.write_text(json.dumps(resources, indent=2))
def create(path, body):
    response = session().post(api + path, json=body, timeout=30)
    response.raise_for_status()
    return response.json()
# Create descriptors without inventing observations, so alert validation can resolve them.
from src.data import FEATURES
for metric_name in (["lab4/drift/psi/" + f for f in FEATURES]
                    + ["lab4/feature/mean/" + f for f in FEATURES]
                    + ["lab4/window/rows", "lab4/model/version"]):
    create("/v3/" + project + "/metricDescriptors", {
        "type": "custom.googleapis.com/itcs355/" + metric_name,
        "metricKind": "GAUGE", "valueType": "DOUBLE", "unit": "1",
        "description": "Lab 4 real rolling prediction-input observations"})
if not resources.get("notification_channel"):
    channel = create("/v3/" + project + "/notificationChannels", {
        "type": "email", "displayName": "ITCS355 Lab 4 authorized test email",
        "labels": {"email_address": a.email}, "enabled": True})
    resources["notification_channel"] = channel["name"]
    save()
if not resources.get("alert_policy"):
    policy = create("/v3/" + project + "/alertPolicies", {
        "displayName": "ITCS355 Lab 4 temperature PSI above calibrated 0.40",
        "combiner": "OR", "enabled": True,
        "notificationChannels": [resources["notification_channel"]],
        "documentation": {"mimeType": "text/markdown", "content": "Authorized Lab 4 fault-injection exercise. Temperature PSI exceeds 0.40. Check the upstream producer before retraining; injected sensor corruption should be fixed upstream, not learned by the model."},
        "conditions": [{"displayName": "500-row temperature PSI exceeds 0.40",
            "conditionThreshold": {
                "filter": 'metric.type="custom.googleapis.com/itcs355/lab4/drift/psi/temp_c" AND resource.type="global"',
                "comparison": "COMPARISON_GT", "thresholdValue": .40, "duration": "0s",
                "aggregations": [{"alignmentPeriod": "60s", "perSeriesAligner": "ALIGN_MAX"}],
                "trigger": {"count": 1}}}],
        "alertStrategy": {"autoClose": "1800s"}})
    resources["alert_policy"] = policy["name"]
    save()
if not resources.get("dashboard"):
    dashboard = create("/v1/" + project + "/dashboards", json.loads((root / "monitoring/dashboard.json").read_text()))
    resources["dashboard"] = dashboard["name"]
    save()
image = json.loads((root / "reports/lab4-staging.json").read_text())["image"]
def command(*args):
    subprocess.run(["gcloud", *args, "--project", cfg.project_id, "--quiet"], check=True)
command("run", "jobs", "deploy", "itcs355-lab4-drift", "--region", cfg.region,
        "--image", image, "--service-account", resources["job_sa"], "--cpu", "1", "--memory", "1Gi",
        "--max-retries", "0", "--task-timeout", "120s", "--tasks", "1", "--parallelism", "1",
        "--command", "python", "--args=-m,cloudlayer.lab4_job",
        "--set-env-vars", f"CLOUD_PROVIDER=gcp,PROJECT_ID={cfg.project_id},REGION={cfg.region},REFERENCE_URI={resources['reference_uri']}",
        "--labels", f"course=itcs355,student={cfg.project_id},lab=4")
print("Monitoring created. Administrator must authorize this exact job's invoker before creating the scheduler.")
