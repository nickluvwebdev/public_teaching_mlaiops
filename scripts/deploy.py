"""Deploy the exact registered version through the cloud adapter."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import load
from cloudlayer.factory import get_adapter

p = argparse.ArgumentParser()
p.add_argument("--model-ref", required=True)
p.add_argument("--endpoint", default="itcs355-lab3")
p.add_argument("--instance", default="1cpu-1Gi")
args = p.parse_args()
url = get_adapter(load()).deploy(args.model_ref, args.endpoint, args.instance)
print(json.dumps({"endpoint": args.endpoint, "url": url, "model_ref": args.model_ref}))
