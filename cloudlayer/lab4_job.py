"""Scheduled job: real accepted input logs -> rolling drift and feature metrics."""
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd
from cloudlayer.gcp_monitoring import session
from cloudlayer.factory import get_adapter
from src.config import load
from src.data import FEATURES
from monitoring.drift import compare


def main():
    cfg = load(strict=False)
    adapter = get_adapter(cfg)
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=15)
    query = (f'resource.type="cloud_run_revision" AND resource.labels.service_name="itcs355-lab4" '
             f'AND timestamp>="{start.isoformat()}" AND timestamp<="{end.isoformat()}" '
             'AND jsonPayload.status=200 AND jsonPayload.features:*')
    rows = []
    versions = []
    page = None
    while len(rows) < 500:
        body = {"resourceNames": [f"projects/{cfg.project_id}"], "filter": query,
                "orderBy": "timestamp desc", "pageSize": 100}
        if page:
            body["pageToken"] = page
        r = session().post("https://logging.googleapis.com/v2/entries:list", json=body, timeout=30)
        r.raise_for_status()
        result = r.json()
        for entry in result.get("entries", []):
            payload = entry["jsonPayload"]
            rows.extend(reversed(payload.get("features", [])))
            versions.append(payload.get("model_version", "unknown"))
        page = result.get("nextPageToken")
        if not page:
            break
    rows = rows[:500]
    if len(rows) < 500:
        print(json.dumps({"event": "drift_insufficient_data", "rows": len(rows), "utc": end.isoformat()}), flush=True)
        return
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "reference.csv"
        adapter.download(os.environ["REFERENCE_URI"], str(path))
        reference = pd.read_csv(path)
    current = pd.DataFrame(rows)
    results = compare(reference, current, FEATURES)
    for item in results:
        adapter.emit_metric("lab4.drift.psi." + item.feature, item.psi)
        adapter.emit_metric("lab4.feature.mean." + item.feature, item.cur_mean)
    adapter.emit_metric("lab4.window.rows", len(rows))
    for version in set(versions):
        if version.isdigit():
            adapter.emit_metric("lab4.model.version", int(version))
    print(json.dumps({"event": "drift_window", "utc": end.isoformat(), "window_start": start.isoformat(),
                      "rows": len(rows), "results": [vars(r) for r in results],
                      "temperature_alert": next(r.psi for r in results if r.feature == "temp_c") >= .40}), flush=True)


if __name__ == "__main__":
    main()
