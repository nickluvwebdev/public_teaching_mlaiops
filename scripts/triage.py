"""Advisory LLM explanation of an exact-version classifier prediction; no tool calls."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config
from cloudlayer.factory import get_adapter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--machine", required=True)
    ap.add_argument("--out", type=Path, default=Path("reports/lab5-evidence/triage-live.json"))
    args = ap.parse_args()
    cfg = config.load()
    adapter = get_adapter(cfg)
    payload = json.loads(args.input.read_text())
    prediction = adapter.invoke(args.endpoint, payload)
    prompt = f"machine_id={args.machine} failure_probability={prediction['probability']}. Decide."
    result = adapter.generate(prompt, {"max_output_tokens": 96, "concise": True})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"classifier": prediction, "advisory": result}, indent=2))
    if result.get("control_error"):
        raise ValueError("Advisory control rejected output; no action is executed")
    print(result["response"])


if __name__ == "__main__":
    main()
