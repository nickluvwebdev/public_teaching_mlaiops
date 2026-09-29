"""Provider-neutral inference service; load one exact registry version at startup."""

from __future__ import annotations
import asyncio
import json
import logging
import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from service.schemas import BatchRequest, BatchResponse, PredictRequest, PredictResponse

log = logging.getLogger("service")
log.setLevel(logging.INFO)
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
log.propagate = False
STATE: dict[str, Any] = {"model": None, "version": "unknown", "ready": False}
INSTANCE_ID = uuid.uuid4().hex
PROBE = {
    "temp_c": 78.4,
    "vibration_mm_s": 3.1,
    "pressure_kpa": 315.2,
    "hours_since_service": 4200.0,
    "load_pct": 68.0,
    "ambient_humidity": 55.0,
}


def _load_model():
    name = os.environ.get("MODEL_REGISTRY_NAME")
    version = os.environ.get("MODEL_VERSION")
    if name and version:
        import mlflow.sklearn
        from src.config import load
        from cloudlayer.factory import get_adapter

        with tempfile.TemporaryDirectory() as directory:
            get_adapter(load(strict=False)).download_registered_model(name, version, directory)
            model = mlflow.sklearn.load_model(directory)
    else:
        import joblib

        model = joblib.load(os.environ.get("MODEL_PATH", "reports/model.joblib"))
    if hasattr(model, "n_jobs"):
        model.n_jobs = 1
    return model


def _score(rows: list[dict]) -> list[float]:
    if STATE["model"] is None:
        raise HTTPException(503, "model not loaded")
    import pandas as pd
    from src.data import FEATURES

    return [float(p) for p in STATE["model"].predict_proba(pd.DataFrame(rows)[FEATURES])[:, 1]]


def _initialise():
    started = time.perf_counter()
    try:
        STATE["model"] = _load_model()
        scores = _score([PROBE])
        if len(scores) != 1 or not 0 <= scores[0] <= 1:
            raise ValueError("startup scoring check failed")
        STATE["ready"] = True
        log.info(
            json.dumps(
                {
                    "event": "model_loaded",
                    "model_version": STATE["version"],
                    "instance_id": INSTANCE_ID,
                    "load_ms": (time.perf_counter() - started) * 1000,
                }
            )
        )
    except Exception as exc:
        STATE["model"] = None
        log.error(
            json.dumps(
                {"event": "model_load_failed", "error": str(exc), "model_version": STATE["version"]}
            )
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    STATE.update(model=None, ready=False, version=os.environ.get("MODEL_VERSION", "unknown"))
    task = asyncio.create_task(asyncio.to_thread(_initialise))
    yield
    await task
    STATE.update(model=None, ready=False)


app = FastAPI(
    title="ITCS355 inference", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None
)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Exclude input/context: they can contain non-JSON floats or large user payloads.
    errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(
        status_code=422, content={"detail": errors, "model_version": STATE["version"]}
    )


@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "model_version": STATE["version"]},
    )


@app.middleware("http")
async def context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))[:128]
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("Unhandled request failure")
        response = JSONResponse(
            status_code=500, content={"detail": "internal error", "model_version": STATE["version"]}
        )
    elapsed = (time.perf_counter() - started) * 1000
    scoring = getattr(request.state, "scoring_ms", 0.0)
    response.headers.update(
        {
            "x-request-id": request_id,
            "x-model-version": str(STATE["version"]),
            "x-server-latency-ms": f"{elapsed:.3f}",
            "x-scoring-ms": f"{scoring:.3f}",
            "x-instance-id": INSTANCE_ID,
        }
    )
    log.info(
        json.dumps(
            {
                "request_id": request_id,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": round(elapsed, 3),
                "scoring_ms": round(scoring, 3),
                "model_version": STATE["version"],
                "instance_id": INSTANCE_ID,
            }
        )
    )
    return response


@app.get("/health")
def health():
    return {"status": "alive", "model_version": STATE["version"]}


@app.get("/ready")
def ready():
    if not STATE["ready"]:
        return JSONResponse(
            status_code=503, content={"status": "not_ready", "model_version": STATE["version"]}
        )
    try:
        _score([PROBE])
    except Exception:
        return JSONResponse(
            status_code=503, content={"status": "not_ready", "model_version": STATE["version"]}
        )
    return {"status": "ready", "model_version": STATE["version"]}


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest, request: Request):
    if not STATE["ready"]:
        raise HTTPException(503, "model not ready")
    started = time.perf_counter()
    score = _score([payload.model_dump(exclude={"padding"})])[0]
    request.state.scoring_ms = (time.perf_counter() - started) * 1000
    return PredictResponse(probability=score, model_version=str(STATE["version"]))


@app.post("/predict/batch", response_model=BatchResponse)
def batch(payload: BatchRequest, request: Request):
    if not STATE["ready"]:
        raise HTTPException(503, "model not ready")
    started = time.perf_counter()
    scores = _score([r.model_dump(exclude={"padding"}) for r in payload.rows])
    request.state.scoring_ms = (time.perf_counter() - started) * 1000
    return BatchResponse(probabilities=scores, model_version=str(STATE["version"]))
