"""Submit and wait for one Lab 2 training job; requires a rebuilt, pinned image."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cloudlayer.factory import get_adapter
from src import config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-uri", required=True)
    parser.add_argument("--data-uri", required=True)
    parser.add_argument("--machine-type", default="n1-standard-4")
    parser.add_argument("--dry-run", action="store_true")
    args, training_args = parser.parse_known_args()
    cfg = config.load()
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=config.REPO_ROOT, text=True,
    ).strip()
    spec = {
        "data_uri": args.data_uri, "machine_type": args.machine_type,
        "git_commit": commit, "training_args": training_args,
    }
    if args.dry_run:
        print(json.dumps({"image_uri": args.image_uri, **spec}, indent=2))
        return
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=config.REPO_ROOT, text=True,
    ).strip()
    if dirty:
        parser.error("Commit the reviewed changes and rebuild/push the image before submitting.")
    adapter = get_adapter(cfg)
    job_id = adapter.submit_training(args.image_uri, spec)
    print(json.dumps({"job_id": job_id}), flush=True)
    print(json.dumps(adapter.wait_training(job_id), indent=2))


if __name__ == "__main__":
    main()
