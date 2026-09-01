import json
import pathlib

import pytest

MALFORMED = sorted(pathlib.Path("payloads/malformed").glob("*.json"))


@pytest.mark.integration
def test_predict_contract(client_factory, sample_txn):
    client = client_factory(probability=0.93)
    r = client.post("/v1/predict", json=json.loads(sample_txn.model_dump_json()))
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "block"
    assert 0 <= body["fraud_probability"] <= 1
    assert r.headers["X-Trace-Id"]


@pytest.mark.integration
@pytest.mark.parametrize("payload_file", MALFORMED, ids=lambda p: p.stem)
def test_malformed_corpus_rejected(client_factory, payload_file):
    client = client_factory()
    r = client.post("/v1/predict", content=payload_file.read_bytes(),
                    headers={"content-type": "application/json"})
    assert 400 <= r.status_code < 500, payload_file.name


@pytest.mark.integration
def test_ready_503_before_startup(client_factory):
    from fastapi.testclient import TestClient

    from fraud_service.api.app import create_app
    client = TestClient(create_app(), raise_server_exceptions=False)
    r = client.get("/v1/ready")
    assert r.status_code == 503


@pytest.mark.integration
def test_health_and_lifespan(real_model, monkeypatch):
    from fastapi.testclient import TestClient

    from fraud_service.api import app as app_module
    monkeypatch.setattr(app_module.SklearnModel, "load",
                        classmethod(lambda cls, *a, **k: real_model))

    with TestClient(app_module.create_app()) as client:
        assert client.get("/v1/health").json()["status"] == "ok"
        assert client.get("/v1/ready").status_code == 200
        assert client.get("/v1/health").headers["X-Trace-Id"]