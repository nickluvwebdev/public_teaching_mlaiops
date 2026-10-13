"""Lab 5 second-provider seam: S3 storage and authenticated model invocation."""

from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlparse
from cloudlayer.base import CloudAdapter


def location(uri):
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError("Second-provider storage requires an s3:// bucket URI")
    return parsed.netloc, parsed.path.lstrip("/")


class AwsAdapter(CloudAdapter):
    def client(self, service):
        import boto3

        return boto3.client(service, region_name=self.cfg.region)

    def upload(self, local_path: str, key: str) -> str:
        bucket, prefix = location(self.cfg.blob_uri)
        object_key = "/".join(x.strip("/") for x in (prefix, key) if x)
        if any(x == ".." for x in object_key.split("/")):
            raise ValueError("Unsafe object key")
        self.client("s3").upload_file(local_path, bucket, object_key)
        return f"s3://{bucket}/{object_key}"

    def download(self, uri: str, local_path: str) -> None:
        bucket, key = location(uri)
        path = Path(local_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.client("s3").download_file(bucket, key, str(path))

    def invoke(self, endpoint: str, payload: dict) -> dict:
        if endpoint.startswith("lambda:"):
            response = self.client("lambda").invoke(
                FunctionName=endpoint.removeprefix("lambda:"),
                InvocationType="RequestResponse",
                Payload=json.dumps(payload).encode(),
            )
            result = json.loads(response["Payload"].read())
            if response.get("FunctionError"):
                raise RuntimeError("Second-provider function failed: " + json.dumps(result))
        else:
            response = self.client("sagemaker-runtime").invoke_endpoint(
                EndpointName=endpoint,
                ContentType="application/json",
                Accept="application/json",
                Body=json.dumps(payload).encode(),
            )
            result = json.loads(response["Body"].read())
        if not isinstance(result, dict) or "model_version" not in result:
            raise ValueError("Second-provider response violates the versioned service contract")
        return result

    def push_image(self, local_tag: str) -> str:
        raise NotImplementedError(
            "Only upload, download and invoke are implemented for the second provider"
        )
