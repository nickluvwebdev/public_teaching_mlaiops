"""Real storage roundtrip and versioned prediction through a second adapter."""

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cloudlayer.factory import get_adapter
from src import config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--second-provider", required=True, choices=["aws", "azure", "gcp"])
    ap.add_argument("--blob-uri", required=True)
    ap.add_argument("--region", required=True)
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--out", type=Path, default=Path("reports/lab5-evidence/second-provider.json"))
    a = ap.parse_args()
    cfg = config.load(strict=False)
    if cfg.provider == a.second_provider:
        raise ValueError("Second provider must differ from primary")
    adapter = get_adapter(
        replace(cfg, provider=a.second_provider, blob_uri=a.blob_uri, region=a.region)
    )
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "probe.json"
        source.write_text(
            json.dumps(
                {
                    "temp_c": 78.4,
                    "vibration_mm_s": 3.1,
                    "pressure_kpa": 315.2,
                    "hours_since_service": 4200,
                    "load_pct": 68,
                    "ambient_humidity": 55,
                }
            )
        )
        uri = adapter.upload(str(source), "portability/probe.json")
        restored = Path(tmp) / "downloaded.json"
        adapter.download(uri, str(restored))
        assert source.read_bytes() == restored.read_bytes(), "storage roundtrip changed bytes"
        response = adapter.invoke(a.endpoint, json.loads(restored.read_text()))
        assert response["model_version"] == a.version
        assert 0 <= float(response["probability"]) <= 1
        result = {
            "primary": cfg.provider,
            "secondary": a.second_provider,
            "uri": uri,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "response": response,
            "proof": "real SDK calls; byte roundtrip and exact model version checked",
        }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2))
    print(a.out)


if __name__ == "__main__":
    main()
