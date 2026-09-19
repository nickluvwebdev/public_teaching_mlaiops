"""Minimal inference container entry point for the registered MLflow model."""
import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import mlflow.sklearn
import pandas as pd

from cloudlayer.factory import get_adapter
from src import config, data


def main():
    cfg = config.load(strict=False)
    with tempfile.TemporaryDirectory() as directory:
        get_adapter(cfg).download_directory(os.environ["AIP_STORAGE_URI"], directory)
        model = mlflow.sklearn.load_model(Path(directory))

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"healthy")

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                frame = pd.DataFrame(payload["instances"], columns=data.FEATURES)
                result = {"predictions": model.predict_proba(frame).tolist()}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())

        HTTPServer(("0.0.0.0", int(os.environ.get("AIP_HTTP_PORT", "8080"))), Handler).serve_forever()


if __name__ == "__main__":
    main()
