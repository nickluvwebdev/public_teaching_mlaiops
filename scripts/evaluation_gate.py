"""Fail-closed validation gate. Test scores never select a model."""

from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
MIN_ABSOLUTE = 0.80
MIN_IMPROVEMENT = 0.005


def decision(candidate: float, incumbent: float | None, first: bool = False) -> tuple[bool, str]:
    if not math.isfinite(candidate) or not 0 <= candidate <= 1:
        return False, "candidate metric is not a finite probability"
    if candidate < MIN_ABSOLUTE:
        return False, f"below absolute floor {MIN_ABSOLUTE}"
    if incumbent is None:
        return (True, "explicit first registration") if first else (False, "incumbent is required")
    if not math.isfinite(incumbent) or not 0 <= incumbent <= 1:
        return False, "incumbent metric is invalid"
    if candidate - incumbent < MIN_IMPROVEMENT - 1e-12:
        return False, f"improvement {candidate - incumbent:+.6f} below {MIN_IMPROVEMENT}"
    return True, f"validation improvement {candidate - incumbent:+.6f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", type=Path, required=True)
    ap.add_argument("--metric", default="val_roc_auc")
    ap.add_argument("--incumbent", type=float)
    ap.add_argument("--allow-first-registration", action="store_true")
    ap.add_argument("--decision-out", type=Path)
    args = ap.parse_args()
    try:
        payload = json.loads(args.metrics.read_text())
        incumbent = args.incumbent
        if incumbent is None and not args.allow_first_registration:
            from src import config
            from cloudlayer.factory import get_adapter

            incumbent = get_adapter(config.load()).production_metric(args.metric)
        passed, reason = decision(
            float(payload[args.metric]), incumbent, args.allow_first_registration
        )
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        passed, reason = False, str(exc)
    result = {"passed": passed, "metric": args.metric, "reason": reason}
    if args.decision_out:
        args.decision_out.parent.mkdir(parents=True, exist_ok=True)
        args.decision_out.write_text(json.dumps(result, indent=2))
    print("GATE " + ("PASS" if passed else "FAIL") + " — " + reason)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
