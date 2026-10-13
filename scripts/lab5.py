"""Compile/submit explicitly, install a paused schedule, and remove scoped resources."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["compile", "submit", "schedule", "teardown", "verify"])
    ap.add_argument("--configuration", type=Path)
    a = ap.parse_args()
    cfg = config.load()
    if a.stage == "compile":
        from cloudlayer.pipelines import compile_for

        print(compile_for(cfg.provider))
        return
    from cloudlayer.lab5_operations import operate

    settings = json.loads(a.configuration.read_text()) if a.configuration else None
    print(json.dumps(operate(cfg, a.stage, settings), indent=2))


if __name__ == "__main__":
    main()
