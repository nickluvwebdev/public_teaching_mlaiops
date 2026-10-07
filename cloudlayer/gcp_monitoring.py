"""Lab 4 Monitoring REST transport, using ADC and no stored service-account keys."""
from datetime import datetime, timezone
import google.auth
from google.auth.transport.requests import AuthorizedSession


def session():
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return AuthorizedSession(credentials)


def emit(cfg, name, value, unit="1"):
    metric_type = "custom.googleapis.com/itcs355/" + name.replace(".", "/")
    body = {"timeSeries": [{
        "metric": {"type": metric_type},
        "resource": {"type": "global", "labels": {"project_id": cfg.project_id}},
        "metricKind": "GAUGE", "valueType": "DOUBLE", "unit": unit if unit != "None" else "1",
        "points": [{"interval": {"endTime": datetime.now(timezone.utc).isoformat()},
                    "value": {"doubleValue": float(value)}}],
    }]}
    r = session().post(f"https://monitoring.googleapis.com/v3/projects/{cfg.project_id}/timeSeries", json=body, timeout=30)
    r.raise_for_status()
