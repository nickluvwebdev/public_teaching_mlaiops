"""Push the CI-tested image and deploy/smoke the exact green source commit."""
import json
import os
import subprocess
import sys
from pathlib import Path
from dataclasses import replace
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import load
from cloudlayer.factory import get_adapter

cfg = load()
sha = os.environ["SOURCE_SHA"]
image = get_adapter(cfg).push_image("itcs355-serve:" + sha)
cfg = replace(cfg, serving_image=image, serving_revision="g" + sha[:12], serving_lab=4)
adapter = get_adapter(cfg)
url = adapter.deploy(cfg.model_registry_name + "@1", "itcs355-lab4", "1cpu-1Gi")
env = os.environ.copy()
env["SERVING_IMAGE"] = image
r = subprocess.run([sys.executable, "scripts/smoke.py", "--endpoint", "itcs355-lab4"], env=env, check=True, capture_output=True, text=True)
Path("reports").mkdir(exist_ok=True)
Path("reports/lab4-staging.json").write_text(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), "source_sha": sha, "image": image, "url": url, "smoke": r.stdout}, indent=2))
print("Staging deployed and smoke-tested", sha, image)
