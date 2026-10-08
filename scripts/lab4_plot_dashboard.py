"""Render a dashboard evidence snapshot from exported Cloud Monitoring data."""
import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

root = Path(__file__).resolve().parents[1]
e = root / "reports/lab4-evidence"
d = json.loads((e / "dashboard-series.json").read_text())
series = d["series"]
fig, axes = plt.subplots(3, 2, figsize=(13, 10), constrained_layout=True)
def points(s):
    return sorted((datetime.fromisoformat(p["interval"]["endTime"].replace("Z", "+00:00")),
                   float(p["value"].get("doubleValue", p["value"].get("int64Value", 0))))
                  for p in s.get("points", []))
def line(ax, name, label=None, **kw):
    for s in series[name].get("timeSeries", []):
        v = points(s)
        if v:
            ax.plot(*zip(*v), linestyle="none", marker="o", markersize=3, label=label, **kw)
rate = defaultdict(float)
classes = defaultdict(lambda: defaultdict(float))
for s in series["requests"].get("timeSeries", []):
    cls = s["metric"]["labels"]["response_code_class"]
    for t, v in points(s):
        rate[t] += v
        classes[cls][t] += v
if rate:
    x = sorted(rate)
    axes[0, 0].plot(x, [rate[t] for t in x], marker="o")
    for cls, color in [("4xx", "#d18b00"), ("5xx", "#b52d36")]:
        axes[0, 1].plot(x, [classes[cls][t] / rate[t] if rate[t] else float("nan") for t in x], marker="o", label=cls, color=color)
axes[0, 0].set(title="Request rate", ylabel="requests / second")
axes[0, 1].set(title="Error fractions (4xx vs 5xx)", ylabel="fraction of requests")
axes[0, 1].legend()
for name, color in [("p50", "#167d9a"), ("p95", "#cc7722"), ("p99", "#b52d36")]:
    for s in series[name].get("timeSeries", []):
        if s["metric"].get("labels", {}).get("response_code_class") == "2xx":
            values = points(s)
            if values:
                axes[1, 0].plot(*zip(*values), marker="o", label=name, color=color)
axes[1, 0].set(title="Endpoint latency, successful requests", ylabel="milliseconds")
axes[1, 0].legend()
line(axes[1, 1], "temperature_mean", color="#167d9a")
axes[1, 1].set(title="Temperature: latest 500 rows / 15 min", ylabel="degrees Celsius")
line(axes[2, 0], "temperature_psi", color="#b52d36")
axes[2, 0].axhline(.40, linestyle="--", color="#555555", label="alert threshold 0.40")
axes[2, 0].set(title="Temperature distribution drift", ylabel="PSI")
axes[2, 0].legend()
line(axes[2, 1], "model_version", color="#167d9a")
axes[2, 1].set(title="Serving model version", ylabel="numeric registry version", ylim=(0, 2))
for ax in axes.flat:
    ax.grid(alpha=.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d\n%H:%M", tz=timezone.utc))
    ax.set_xlabel("UTC (month-day / hour:minute)")
fig.suptitle("Lab 4 — actual Cloud Monitoring dashboard data", fontsize=17, weight="bold")
fig.savefig(e / "dashboard-snapshot.png", dpi=160)
print(e / "dashboard-snapshot.png")
