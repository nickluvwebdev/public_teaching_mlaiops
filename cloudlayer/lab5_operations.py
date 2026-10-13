"""Lab 5 managed operations scoped by project/student/lab labels."""

import json
from pathlib import Path
from google.cloud import aiplatform
from cloudlayer.gcp_monitoring import session


def inventory(cfg):
    query = " AND ".join(f'labels.{key}="{val}"' for key, val in cfg.tags(5).items())
    jobs = aiplatform.PipelineJob.list(filter=query, project=cfg.project_id, location=cfg.region)
    training = aiplatform.CustomJob.list(filter=query, project=cfg.project_id, location=cfg.region)
    schedules = aiplatform.PipelineJobSchedule.list(project=cfg.project_id, location=cfg.region)
    schedules = [x for x in schedules if x.display_name == "itcs355-lab5-" + cfg.project_id]
    url = f"https://run.googleapis.com/v2/projects/{cfg.project_id}/locations/{cfg.region}/services"
    r = session().get(url, timeout=30)
    r.raise_for_status()
    services = [
        x
        for x in r.json().get("services", [])
        if all(x.get("labels", {}).get(k) == v for k, v in cfg.tags(5).items())
    ]
    return jobs, training, schedules, services


def operate(cfg, stage, settings=None):
    if stage in {"submit", "schedule"}:
        if not settings or settings.get("budget_ceiling_thb") != 50:
            raise ValueError("Reviewed 50 THB ceiling and configuration required")
        for key in [
            "training_image",
            "source_commit",
            "data_version",
            "run_id",
            "output_key",
            "endpoint",
            "environment",
        ]:
            if not settings.get(key):
                raise ValueError("Missing configuration: " + key)
        if "@sha256:" not in settings["training_image"]:
            raise ValueError("Build/upload the current code and supply the immutable digest")
        job = aiplatform.PipelineJob(
            display_name="itcs355-lab5-" + cfg.project_id,
            template_path=str(Path(__file__).resolve().parents[1] / "pipeline/compiled.json"),
            pipeline_root=cfg.blob_uri.rstrip("/") + "/lab5/pipeline",
            parameter_values={"configuration": json.dumps(settings)},
            enable_caching=False,
            project=cfg.project_id,
            location=cfg.region,
            labels=cfg.tags(5),
        )
        identity = settings.get("pipeline_identity")
        if not identity or identity == cfg.identity_ref or identity == cfg.serving_identity:
            raise ValueError("A separate orchestrator/CI identity must run the pipeline")
        if stage == "submit":
            job.submit(service_account=identity)
            return {
                "pipeline_job": job.resource_name,
                "note": "Wait, capture evidence, and tear down immediately",
            }
        schedule = job.create_schedule(
            cron="TZ=Asia/Bangkok 0 2 * * 0",
            display_name="itcs355-lab5-" + cfg.project_id,
            max_concurrent_run_count=1,
            max_run_count=1,
            service_account=identity,
        )
        schedule.pause()
        return {"schedule": schedule.resource_name, "state": "PAUSED", "max_runs": 1}
    jobs, training, schedules, services = inventory(cfg)
    if stage == "teardown":
        for schedule in schedules:
            schedule.delete()
        for job in jobs:
            if job.state.name not in {
                "PIPELINE_STATE_SUCCEEDED",
                "PIPELINE_STATE_FAILED",
                "PIPELINE_STATE_CANCELLED",
            }:
                job.cancel()
            else:
                job.delete()
        for job in training:
            if job.state.name not in {
                "JOB_STATE_SUCCEEDED",
                "JOB_STATE_FAILED",
                "JOB_STATE_CANCELLED",
                "JOB_STATE_EXPIRED",
            }:
                job.cancel()
        for service in services:
            r = session().delete("https://run.googleapis.com/v2/" + service["name"], timeout=30)
            r.raise_for_status()
        return {
            "requested_removal": True,
            "note": "Deletion can be asynchronous; verify separately and after 24 hours",
        }
    active = [
        j.resource_name
        for j in jobs
        if j.state.name
        not in {"PIPELINE_STATE_SUCCEEDED", "PIPELINE_STATE_FAILED", "PIPELINE_STATE_CANCELLED"}
    ]
    active_train = [
        j.resource_name
        for j in training
        if j.state.name
        not in {
            "JOB_STATE_SUCCEEDED",
            "JOB_STATE_FAILED",
            "JOB_STATE_CANCELLED",
            "JOB_STATE_EXPIRED",
        }
    ]
    result = {
        "active_pipelines": active,
        "active_training": active_train,
        "schedules": [x.resource_name for x in schedules],
        "services": [x["name"] for x in services],
    }
    if any(result.values()):
        raise RuntimeError("Teardown not verified: " + json.dumps(result))
    return result
