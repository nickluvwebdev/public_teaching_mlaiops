"""Real container integration: wait for readiness and assert schema and exact version."""
import argparse
import time
import requests

p = argparse.ArgumentParser()
p.add_argument("--url", default="http://localhost:8080")
p.add_argument("--version", required=True)
a = p.parse_args()
for _ in range(90):
    try:
        r = requests.get(a.url + "/ready", timeout=2)
        if r.status_code == 200:
            break
    except requests.RequestException:
        pass
    time.sleep(2)
else:
    raise RuntimeError("Container did not become ready")
row = dict(temp_c=78.4, vibration_mm_s=3.1, pressure_kpa=315.2,
           hours_since_service=4200, load_pct=68, ambient_humidity=55)
r = requests.post(a.url + "/predict", json=row, timeout=10)
r.raise_for_status()
b = r.json()
assert set(b) == {"probability", "model_version"}, b
assert b["model_version"] == a.version, b
assert isinstance(b["probability"], (int, float)) and 0 <= b["probability"] <= 1, b
r = requests.post(a.url + "/predict", json={"temp_c": 70}, timeout=10)
assert r.status_code == 422 and r.json()["model_version"] == a.version
print("Container integration passed: probability, exact version, and 422 contract")
