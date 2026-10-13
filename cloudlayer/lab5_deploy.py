"""Managed staging deployment using ADC REST, without a CLI inside the image."""

import time
import requests
from cloudlayer.gcp_monitoring import session


def deploy(cfg, model_ref, endpoint, invoker_identity):
    name, version = model_ref.rsplit("@", 1)
    if not version.isdigit() or "@sha256:" not in cfg.serving_image or not cfg.serving_identity:
        raise ValueError("Exact model, immutable image and serving identity required")
    base = f"https://run.googleapis.com/v2/projects/{cfg.project_id}/locations/{cfg.region}"
    s = session()
    env = {
        "CLOUD_PROVIDER": "gcp",
        "PROJECT_ID": cfg.project_id,
        "REGION": cfg.region,
        "MODEL_REGISTRY_NAME": name,
        "MODEL_VERSION": version,
    }
    body = {
        "labels": cfg.tags(5),
        "template": {
            "serviceAccount": cfg.serving_identity,
            "scaling": {"minInstanceCount": 0, "maxInstanceCount": 1},
            "timeout": "60s",
            "containers": [
                {
                    "image": cfg.serving_image,
                    "ports": [{"containerPort": 8080}],
                    "resources": {"limits": {"cpu": "1", "memory": "1Gi"}},
                    "env": [{"name": k, "value": v} for k, v in env.items()],
                    "startupProbe": {
                        "httpGet": {"path": "/ready", "port": 8080},
                        "periodSeconds": 2,
                        "timeoutSeconds": 1,
                        "failureThreshold": 120,
                    },
                }
            ],
        },
    }
    r = s.post(base + "/services", params={"serviceId": endpoint}, json=body, timeout=30)
    if r.status_code == 409:
        body["name"] = base.replace("https://run.googleapis.com/v2/", "") + "/services/" + endpoint
        r = s.patch(
            base + "/services/" + endpoint,
            params={"updateMask": "template,labels"},
            json=body,
            timeout=30,
        )
    r.raise_for_status()
    operation = r.json()["name"]
    for _ in range(80):
        x = s.get("https://run.googleapis.com/v2/" + operation, timeout=30)
        x.raise_for_status()
        status = x.json()
        if status.get("done"):
            if status.get("error"):
                raise RuntimeError(status["error"])
            break
        time.sleep(5)
    else:
        raise TimeoutError("Staging deploy did not finish")
    r = s.get(base + "/services/" + endpoint, timeout=30)
    r.raise_for_status()
    url = r.json()["uri"]
    token_response = s.post(
        "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
        + invoker_identity
        + ":generateIdToken",
        json={"audience": url, "includeEmail": True},
        timeout=30,
    )
    token_response.raise_for_status()
    token = token_response.json()["token"]
    smoke = requests.post(
        url + "/predict",
        headers={"Authorization": "Bearer " + token},
        json={
            "temp_c": 78.4,
            "vibration_mm_s": 3.1,
            "pressure_kpa": 315.2,
            "hours_since_service": 4200,
            "load_pct": 68,
            "ambient_humidity": 55,
        },
        timeout=90,
    )
    smoke.raise_for_status()
    assert smoke.json()["model_version"] == version
    return url
