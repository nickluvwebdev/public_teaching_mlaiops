"""Export the native dashboard's actual Cloud Monitoring series for lab evidence."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import load
from cloudlayer.gcp_monitoring import session

cfg = load()
root = Path(__file__).resolve().parents[1]
end = datetime.now(timezone.utc).isoformat()
start = "2026-10-07T17:50:00Z"
base = f"https://monitoring.googleapis.com/v3/projects/{cfg.project_id}/timeSeries"
s = session()
queries = {
    "temperature_psi": ('metric.type="custom.googleapis.com/itcs355/lab4/drift/psi/temp_c" AND resource.type="global"', "ALIGN_MEAN"),
    "temperature_mean": ('metric.type="custom.googleapis.com/itcs355/lab4/feature/mean/temp_c" AND resource.type="global"', "ALIGN_MEAN"),
    "model_version": ('metric.type="custom.googleapis.com/itcs355/lab4/model/version" AND resource.type="global"', "ALIGN_MEAN"),
    "requests": ('metric.type="run.googleapis.com/request_count" AND resource.labels.service_name="itcs355-lab4"', "ALIGN_RATE"),
}
for percentile in (50, 95, 99):
    queries["p" + str(percentile)] = ('metric.type="run.googleapis.com/request_latencies" AND resource.labels.service_name="itcs355-lab4"', "ALIGN_PERCENTILE_" + str(percentile))
result = {"captured_at": end, "start": start, "series": {}}
for name, (query, aligner) in queries.items():
    r = s.get(base, params={"filter": query, "interval.startTime": start,
        "interval.endTime": end, "view": "FULL", "aggregation.alignmentPeriod": "60s",
        "aggregation.perSeriesAligner": aligner}, timeout=30)
    r.raise_for_status()
    result["series"][name] = r.json()
path = root / "reports/lab4-evidence/dashboard-series.json"
path.write_text(json.dumps(result, indent=2))
print(path)
