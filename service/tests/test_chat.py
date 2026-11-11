"""Offline /api/chat proxy tests; Dify is replaced by MockTransport, no real HTTP."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from service.app.config import Settings, ChatSettings
from service.app.dify import DifyClient, DifyFailure, split_answer
from service.app.main import create_app

VERIFY_BODY = {
    "mode": "deepseek",
    "overall_status": "supported",
    "claims": [{
        "claim": "本课程共12周。",
        "status": "supported",
        "evidence_ids": ["E1"],
        "reason": "E1明确给出课程周数。",
        "citations": [{"evidence_id": "E1", "quote": "本课程共12周。"}],
    }],
    "evidence_count": 2,
    "message": "Evaluated against supplied evidence only.",
    "error_code": None,
}

ANSWER_TEXT = "课程共12周，期末只有笔试（E1）（E2）。"


def dify_payload(answer_text: str = ANSWER_TEXT, body: dict | None = None,
                 conversation_id: str = "conv-1") -> dict:
    raw = answer_text + "\n\n" + json.dumps(body if body is not None else VERIFY_BODY,
                                            ensure_ascii=False)
    return {"answer": raw, "conversation_id": conversation_id}


def make_transport(payload: dict | None = None, status: int = 200,
                   capture: dict | None = None) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture["url"] = str(request.url)
            capture["authorization"] = request.headers.get("authorization")
            capture["json"] = json.loads(request.content.decode("utf-8"))
        if payload is None:
            return httpx.Response(status, text="upstream error")
        return httpx.Response(status, json=payload)
    return httpx.MockTransport(handler)


_DEFAULT = object()


def make_client(payload: dict | None | object = _DEFAULT, status: int = 200,
                chat_settings: ChatSettings | None = None,
                capture: dict | None = None) -> TestClient:
    if payload is _DEFAULT:
        payload = dify_payload()
    settings = chat_settings if chat_settings is not None else ChatSettings(
        base_url="http://dify.internal/v1", api_key="app-test-key")
    dify_client = DifyClient(settings, transport=make_transport(payload, status, capture))
    app = create_app(settings=Settings(mode="mock"),
                     chat_settings=settings, dify_client=dify_client)
    return TestClient(app)


def test_chat_success_maps_fields_and_passthrough_conversation():
    capture: dict = {}
    client = make_client(capture=capture)
    response = client.post("/api/chat", json={"question": "课程多久？",
                                              "conversation_id": "conv-0"})
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "dify"
    assert data["answer"] == ANSWER_TEXT
    assert data["overall_status"] == "supported"
    assert len(data["claims"]) == 1
    assert data["claims"][0]["citations"][0]["quote"] == "本课程共12周。"
    assert data["evidence_count"] == 2
    assert data["error_code"] is None
    assert data["conversation_id"] == "conv-1"
    assert capture["url"] == "http://dify.internal/v1/chat-messages"
    assert capture["authorization"] == "Bearer app-test-key"
    assert capture["json"]["inputs"] == {"question": "课程多久？"}
    assert capture["json"]["query"] == "课程多久？"
    assert capture["json"]["conversation_id"] == "conv-0"
    assert capture["json"]["response_mode"] == "blocking"


def test_chat_first_round_sends_empty_conversation_id():
    capture: dict = {}
    client = make_client(capture=capture)
    response = client.post("/api/chat", json={"question": "课程多久？"})
    assert response.status_code == 200
    assert capture["json"]["conversation_id"] == ""


def test_chat_not_configured_returns_503():
    app = create_app(settings=Settings(mode="mock"), chat_settings=None)
    client = TestClient(app)
    response = client.post("/api/chat", json={"question": "课程多久？"})
    assert response.status_code == 503
    status = client.get("/api/ui-status").json()
    assert status["chat_available"] is False
    assert status["dify_connected"] is False


def test_chat_configured_reports_ui_status_available():
    client = make_client()
    status = client.get("/api/ui-status").json()
    assert status["chat_available"] is True
    assert status["dify_connected"] is True


def test_chat_upstream_http_error_becomes_verification_failed():
    client = make_client(payload=None, status=502)
    data = client.post("/api/chat", json={"question": "课程多久？"}).json()
    assert data["overall_status"] == "verification_failed"
    assert data["error_code"] == "upstream_http_error"
    assert data["claims"] == []


def test_chat_upstream_timeout_becomes_verification_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow upstream", request=request)
    settings = ChatSettings(base_url="http://dify.internal/v1", api_key="app-test-key")
    dify_client = DifyClient(settings, transport=httpx.MockTransport(handler))
    app = create_app(settings=Settings(mode="mock"),
                     chat_settings=settings, dify_client=dify_client)
    data = TestClient(app).post("/api/chat", json={"question": "课程多久？"}).json()
    assert data["overall_status"] == "verification_failed"
    assert data["error_code"] == "upstream_timeout"


def test_chat_malformed_answer_body_keeps_text_and_flags_invalid():
    payload = {"answer": "只有答案文本，没有核验 JSON。", "conversation_id": "conv-2"}
    client = make_client(payload=payload)
    data = client.post("/api/chat", json={"question": "课程多久？"}).json()
    assert data["overall_status"] == "verification_failed"
    assert data["error_code"] == "invalid_upstream_response"
    assert data["answer"] == "只有答案文本，没有核验 JSON。"
    assert data["conversation_id"] == "conv-2"


def test_chat_body_without_overall_status_is_invalid():
    payload = {"answer": "答案。\n\n" + json.dumps({"claims": []}), "conversation_id": "c"}
    client = make_client(payload=payload)
    data = client.post("/api/chat", json={"question": "课程多久？"}).json()
    assert data["error_code"] == "invalid_upstream_response"


def test_chat_question_validation():
    client = make_client()
    assert client.post("/api/chat", json={"question": ""}).status_code == 422
    assert client.post("/api/chat", json={"question": "好" * 2001}).status_code == 422
    assert client.post("/api/chat", json={"question": "课程多久？", "extra": 1}).status_code == 422


def test_split_answer_handles_blank_lines_in_llm_text():
    raw = "第一段。\n\n第二段（E1）。\n\n" + json.dumps(VERIFY_BODY, ensure_ascii=False)
    answer, body = split_answer(raw)
    assert answer == "第一段。\n\n第二段（E1）。"
    assert body["overall_status"] == "supported"


def test_split_answer_pure_json_reply():
    raw = json.dumps(VERIFY_BODY, ensure_ascii=False)
    answer, body = split_answer(raw)
    assert answer == ""
    assert body["overall_status"] == "supported"


def test_split_answer_without_json_returns_none():
    answer, body = split_answer("没有任何 JSON 的回答。")
    assert answer == "没有任何 JSON 的回答。"
    assert body is None


def test_dify_failure_carries_only_safe_code():
    assert str(DifyFailure("upstream_timeout")) == "upstream_timeout"
