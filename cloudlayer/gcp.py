"""GCP adapter. Implement upload/download/push_image for Lab 1.

SDK:  pip install google-cloud-storage google-cloud-aiplatform
Docs: storage.Client for GCS; Artifact Registry push goes through `docker push` after
      `gcloud auth configure-docker <region>-docker.pkg.dev`.

Hints for Lab 1:
  * BLOB_URI looks like gs://bucket/prefix — parse it here, never in src/.
  * Artifact Registry paths are region-scoped:
        <region>-docker.pkg.dev/<project>/<repo>/<image>
    A common first failure is pushing to gcr.io out of habit; it is a different service.
  * push_image must return the digest reference, not the tag.
  * GCP calls them labels, not tags, and they must be lowercase with no spaces.
    cfg.tags(1) already satisfies that constraint — do not "improve" the values.
"""
from __future__ import annotations

from typing import Any

from cloudlayer.base import CloudAdapter


class GcpAdapter(CloudAdapter):
    def upload(self, local_path: str, key: str) -> str:
        from google.cloud import storage
        from urllib.parse import urlparse

        parsed = urlparse(self.cfg.blob_uri)
        bucket_name = parsed.netloc
        prefix = parsed.path.lstrip("/").rstrip("/")
        object_name = f"{prefix}/{key}" if prefix else key

        client = storage.Client(project=self.cfg.project_id)
        blob = client.bucket(bucket_name).blob(object_name)

        blob.upload_from_filename(local_path)

        return f"gs://{bucket_name}/{object_name}"

    def download(self, uri: str, local_path: str) -> None:
        from google.cloud import storage
        from pathlib import Path
        from urllib.parse import urlparse

        parsed = urlparse(uri)
        bucket_name = parsed.netloc
        object_name = parsed.path.lstrip("/")

        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        client = storage.Client(project=self.cfg.project_id)
        blob = client.bucket(bucket_name).blob(object_name)
        blob.download_to_filename(local_path)

    def push_image(self, local_tag: str) -> str:
        import subprocess

        registry = self.cfg.container_registry.rstrip("/")

        subprocess.run(
            [
                "gcloud",
                "auth",
                "configure-docker",
                f"{self.cfg.region}-docker.pkg.dev",
                "--quiet",
            ],
            check=True,
        )

        remote_tag = f"{registry}/{local_tag}"

        subprocess.run(
            ["docker", "tag", local_tag, remote_tag],
            check=True,
        )

        subprocess.run(
            ["docker", "push", remote_tag],
            check=True,
        )

        result = subprocess.run(
            ["docker", "inspect", "--format={{index .RepoDigests 0}}", remote_tag],
            check=True,
            capture_output=True,
            text=True,
        )

        return result.stdout.strip()

    def submit_training(self, image_uri: str, args: dict[str, Any]) -> str:
        from google.cloud import aiplatform
        from uuid import uuid4

        if "@sha256:" not in image_uri:
            raise ValueError("Training image must be digest-pinned.")
        if not self.cfg.identity_ref or not self.cfg.blob_uri.startswith("gs://"):
            raise ValueError("Set IDENTITY_REF and a GCS BLOB_URI before submission.")
        output_key = args.get("output_key", f"lab2/jobs/{uuid4().hex}")
        env = {
            "CLOUD_PROVIDER": "gcp", "PROJECT_ID": self.cfg.project_id,
            "REGION": self.cfg.region, "BLOB_URI": self.cfg.blob_uri,
            "TRAINING_DATA_URI": args["data_uri"],
            "TRAINING_OUTPUT_KEY": output_key,
            "SOURCE_COMMIT": args["git_commit"],
            "DATA_VERSION": args.get("data_version", ""),
            "IMAGE_DIGEST": image_uri,
            "MLFLOW_TRACKING_URI": args.get("tracking_uri", "sqlite:////tmp/mlflow.db"),
        }
        job = aiplatform.CustomJob(
            display_name="itcs355-lab2",
            project=self.cfg.project_id, location=self.cfg.region,
            staging_bucket=self.cfg.blob_uri,
            base_output_dir=f"{self.cfg.blob_uri.rstrip('/')}/{output_key}",
            labels=self.cfg.tags(2),
            worker_pool_specs=[{
                "machine_spec": {"machine_type": args.get("machine_type", "n1-standard-4")},
                "replica_count": 1,
                "container_spec": {
                    "image_uri": image_uri,
                    "command": ["python", "-m", args.get("module", "src.train")],
                    "args": args.get("training_args", []),
                    "env": [{"name": k, "value": v} for k, v in env.items()],
                },
            }],
        )
        options = {}
        if args.get("spot"):
            from google.cloud.aiplatform_v1.types import Scheduling
            options["scheduling_strategy"] = Scheduling.Strategy.SPOT
            options["max_wait_duration"] = 1800
        job.submit(service_account=self.cfg.identity_ref,
                   timeout=args.get("timeout", 3600), **options)
        return job.resource_name

    def wait_training(self, job_id: str) -> dict[str, Any]:
        from google.cloud import aiplatform

        job = aiplatform.CustomJob.get(
            job_id, project=self.cfg.project_id, location=self.cfg.region,
        )
        import time

        while True:
            state = job.state.name
            if state == "JOB_STATE_SUCCEEDED":
                break
            if state in {"JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}:
                raise RuntimeError(f"Training job {job_id} ended in {state}: {job.error}")
            time.sleep(15)
        return {
            "job_id": job.resource_name,
            "state": state,
            "artifact_uri": job.gca_resource.job_spec.base_output_directory.output_uri_prefix,
        }

    def runtime_job_id(self) -> str:
        job_id = self.cfg.native_job_id
        if not job_id:
            return "local"
        if job_id.startswith("projects/"):
            return job_id
        return f"projects/{self.cfg.project_id}/locations/{self.cfg.region}/customJobs/{job_id}"

    def download_directory(self, uri: str, local_path: str) -> None:
        from pathlib import Path
        from urllib.parse import urlparse
        from google.cloud import storage

        parsed = urlparse(uri)
        prefix = parsed.path.lstrip("/").rstrip("/") + "/"
        root = Path(local_path).resolve()
        count = 0
        client = storage.Client(project=self.cfg.project_id)
        for blob in client.list_blobs(parsed.netloc, prefix=prefix):
            if blob.name.endswith("/"):
                continue
            path = (root / blob.name[len(prefix):]).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Unsafe artifact object name")
            path.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(path))
            count += 1
        if not count:
            raise FileNotFoundError(uri)

    def register_model(self, model_uri: str, name: str) -> str:
        import json
        import tempfile
        from pathlib import Path
        from google.cloud import aiplatform

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lineage.json"
            self.download(model_uri.rstrip("/") + "/lineage.json", str(path))
            lineage = json.loads(path.read_text())
        required = {"git_commit", "data_version", "mlflow_run_id", "training_job_id",
                    "image_digest", "seed", "metric_val", "metric_test"}
        if required - lineage.keys() or any(lineage[k] in ("", None, "local") for k in required):
            raise ValueError("Registry import requires complete managed-training lineage.")
        existing = aiplatform.Model.list(
            filter=f'display_name="{name}"', project=self.cfg.project_id, location=self.cfg.region)
        if len(existing) > 1:
            raise ValueError("Multiple registry models share this display name.")
        model = aiplatform.Model.upload(
            display_name=name, artifact_uri=model_uri,
            serving_container_image_uri=lineage["image_digest"],
            serving_container_command=["python", "-m", "scripts.registry_server"],
            serving_container_environment_variables={
                "CLOUD_PROVIDER": "gcp", "PROJECT_ID": self.cfg.project_id,
                "REGION": self.cfg.region,
            },
            serving_container_ports=[8080],
            serving_container_predict_route="/predict", serving_container_health_route="/health",
            project=self.cfg.project_id, location=self.cfg.region,
            parent_model=existing[0].resource_name if existing else None,
            labels={**self.cfg.tags(2), "git_commit": lineage["git_commit"],
                    "mlflow_run_id": lineage["mlflow_run_id"]},
            version_description=json.dumps(lineage, sort_keys=True),
            version_aliases=["candidate"], sync=True,
        )
        return f"{model.resource_name}@{model.version_id}"

    def promote_model(self, model_ref: str, alias: str = "staging") -> None:
        from google.cloud import aiplatform

        name, version = model_ref.rsplit("@", 1)
        registry = aiplatform.models.ModelRegistry(
            model=name, project=self.cfg.project_id, location=self.cfg.region)
        registry.add_version_aliases([alias], version=version)

    def download_registered_model(self, name: str, version: str, local_path: str) -> dict:
        import json
        from google.cloud import aiplatform

        if not version.isdigit():
            raise ValueError("Reload requires an exact numeric version, not a mutable alias.")
        if not name.startswith("projects/"):
            matches = aiplatform.Model.list(
                filter=f'display_name="{name}"', project=self.cfg.project_id, location=self.cfg.region)
            if len(matches) != 1:
                raise ValueError("Registered model name must resolve to exactly one model.")
            name = matches[0].resource_name
        model = aiplatform.Model(name, version=version,
                                 project=self.cfg.project_id, location=self.cfg.region)
        self.download_directory(model.uri, local_path)
        from pathlib import Path
        lineage = json.loads((Path(local_path) / "lineage.json").read_text())
        if lineage != json.loads(model.version_description):
            raise ValueError("Artifact lineage differs from registry version properties.")
        return {"model_ref": f"{model.resource_name}@{model.version_id}",
                "artifact_uri": model.uri, "version_aliases": list(model.version_aliases)}

    def teardown(self, tags: dict[str, str]) -> list[str]:
        """Cancel active matching training jobs; preserve registry, artifacts and evidence."""
        from google.cloud import aiplatform

        if tags != self.cfg.tags(2):
            raise ValueError("This teardown is scoped strictly to this student's Lab 2 jobs.")
        query = " AND ".join(f'labels.{key}="{value}"' for key, value in tags.items())
        jobs = aiplatform.CustomJob.list(
            filter=query, project=self.cfg.project_id, location=self.cfg.region)
        cancelled = []
        terminal = {"JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}
        for job in jobs:
            if job.state.name not in terminal:
                job.cancel()
                cancelled.append(job.resource_name)
        return cancelled

    # deploy / invoke                   -> Lab 3 (Vertex Endpoint)
    # emit_metric                       -> Lab 4 (Cloud Monitoring time series)
    # generate                          -> Lab 5 (managed LLM endpoint; read usageMetadata for tokens)
