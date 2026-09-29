"""Readiness and versioned error behavior beyond the ordinary happy path."""

import threading
import time
from fastapi.testclient import TestClient
from service import app as service


def test_loading_is_live_but_not_ready_and_loads_once(monkeypatch):
    release = threading.Event()
    calls = []

    class Model:
        def predict_proba(self, frame):
            import numpy as np

            return np.array([[0.8, 0.2]] * len(frame))

    def load():
        calls.append(1)
        assert release.wait(5)
        return Model()

    monkeypatch.setattr(service, "_load_model", load)
    monkeypatch.setenv("MODEL_VERSION", "17")
    with TestClient(service.app) as client:
        assert client.get("/health").json() == {"status": "alive", "model_version": "17"}
        assert client.get("/ready").status_code == 503
        assert client.post("/predict", json=service.PROBE).status_code == 503
        release.set()
        for _ in range(100):
            if client.get("/ready").status_code == 200:
                break
            time.sleep(0.02)
        assert client.post("/predict", json=service.PROBE).status_code == 200
        assert client.post("/predict", json=service.PROBE).status_code == 200
        assert calls == [1]
        for response in [
            client.post("/predict", json={}),
            client.get("/missing"),
            client.post("/predict/batch", json={"rows": []}),
        ]:
            assert response.json()["model_version"] == "17"


def test_loaded_but_broken_model_is_not_ready(monkeypatch):
    class Broken:
        def predict_proba(self, frame):
            raise ValueError("cannot score")

    monkeypatch.setattr(service, "_load_model", lambda: Broken())
    with TestClient(service.app) as client:
        time.sleep(0.1)
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
