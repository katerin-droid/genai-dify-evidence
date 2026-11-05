import copy
import socket
import pytest
from fastapi.testclient import TestClient
from service.app.main import create_app

PAYLOAD = {"question": "课程多久？", "answer": "两小时", "evidence": [{"evidence_id": "e1", "text": "课程时长两小时。"}]}

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("VERIFIER_MODE", "mock")
    with TestClient(create_app()) as test_client:
        def no_network(*args, **kwargs):
            raise AssertionError("Network access forbidden in mock tests")
        # Patch after Windows asyncio has created its internal wakeup socket.
        with monkeypatch.context() as guard:
            guard.setattr(socket.socket, "connect", no_network)
            yield test_client

def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "mode": "mock"}

def test_verify_mock(client):
    response = client.post("/verify", json=PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "mock"
    assert body["status"] == "not_evaluated"
    assert body["score"] is None and body["support_label"] is None
    assert body["evidence_count"] == 1
    assert client.post("/verify", json=PAYLOAD).json() == body

@pytest.mark.parametrize("field,value", [("question", " "), ("question", 7), ("answer", ""), ("answer", "x"*20001), ("evidence", []), ("evidence", [{}]), ("evidence", [PAYLOAD["evidence"][0]]*51)])
def test_invalid_input(client, field, value):
    payload = copy.deepcopy(PAYLOAD)
    payload[field] = value
    assert client.post("/verify", json=payload).status_code == 422

def test_missing_answer(client):
    assert client.post("/verify", json={"question": "q"}).status_code == 422

def test_extra_field(client):
    assert client.post("/verify", json={**PAYLOAD, "api_key": "dummy"}).status_code == 422

def test_invalid_evidence(client):
    payload = {**PAYLOAD, "evidence": [{"evidence_id": " ", "text": " "}]}
    assert client.post("/verify", json=payload).status_code == 422

def test_malformed_json(client):
    assert client.post("/verify", content="{", headers={"Content-Type": "application/json"}).status_code == 422

def test_live_mode_rejected(monkeypatch):
    monkeypatch.setenv("VERIFIER_MODE", "live")
    with pytest.raises(ValueError, match="Only mock"):
        create_app()
