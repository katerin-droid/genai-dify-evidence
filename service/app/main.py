from fastapi import FastAPI, HTTPException
from .config import Settings, get_settings, ChatSettings, get_chat_settings
from .schemas import (VerifyRequest, VerifyResponse, EvidenceVerifyRequest, EvidenceVerifyResponse,
                      ChatRequest, ChatResponse, ClaimResult, Status)
from .verifier import verify_mock, verify_evidence
from .deepseek import DeepSeekClient
from .dify import DifyClient, DifyFailure, split_answer
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import get_args

_CHAT_UNSET = object()


def _parse_verification(body: dict) -> tuple[str, list[ClaimResult], int, str, str | None] | None:
    """Validate the verifier JSON embedded in the Dify reply; None means invalid upstream."""
    status = body.get("overall_status")
    if status not in get_args(Status):
        return None
    try:
        claims = [ClaimResult(**c) for c in body.get("claims", [])]
        evidence_count = int(body.get("evidence_count", 0))
    except Exception:
        return None
    message = body.get("message")
    error_code = body.get("error_code")
    return (status, claims, max(evidence_count, 0),
            message if isinstance(message, str) else "",
            error_code if isinstance(error_code, str) else None)


def create_app(settings: Settings | None = None, completion_client: DeepSeekClient | None = None,
               chat_settings: ChatSettings | None | object = _CHAT_UNSET,
               dify_client: DifyClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    if chat_settings is _CHAT_UNSET:
        chat_settings = get_chat_settings()
    app = FastAPI(title="Course Evidence Verifier", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": settings.mode}

    if settings.mode == "mock":
        @app.post("/verify", response_model=VerifyResponse)
        def verify(request: VerifyRequest) -> VerifyResponse:
            return verify_mock(request)
    else:
        client = completion_client or DeepSeekClient(settings)

        @app.post("/verify", response_model=EvidenceVerifyResponse)
        def verify_real(request: EvidenceVerifyRequest) -> EvidenceVerifyResponse:
            return verify_evidence(request, client)

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        if chat_settings is None:
            raise HTTPException(status_code=503,
                                detail="服务尚未连接：未配置 DIFY_API_KEY。")
        client = dify_client or DifyClient(chat_settings)
        try:
            result = client.chat(request.question, request.conversation_id)
        except DifyFailure as exc:
            return ChatResponse(overall_status="verification_failed", error_code=str(exc),
                                message="问答链路暂时不可用，请稍后重试。",
                                conversation_id=request.conversation_id)
        answer, body = split_answer(result["answer"])
        parsed = _parse_verification(body) if body is not None else None
        if parsed is None:
            return ChatResponse(overall_status="verification_failed",
                                error_code="invalid_upstream_response",
                                message="无法解析问答链路返回的核验结果。",
                                answer=answer,
                                conversation_id=result.get("conversation_id"))
        status, claims, evidence_count, message, error_code = parsed
        return ChatResponse(overall_status=status, claims=claims,
                            evidence_count=evidence_count,
                            message=message or "Evaluated against supplied evidence only.",
                            error_code=error_code, answer=answer,
                            conversation_id=result.get("conversation_id"))

    @app.get("/api/ui-status")
    def ui_status():
        if chat_settings is None:
            return {"dify_connected": False, "chat_available": False,
                    "verification_mode": settings.mode,
                    "message": "服务尚未连接：尚未配置 Dify 问答代理。"}
        return {"dify_connected": True, "chat_available": True,
                "verification_mode": settings.mode,
                "message": "已连接课程问答工作流，核验结果来自真实接口。"}

    web = Path(__file__).resolve().parents[2] / "web"
    if web.is_dir():
        app.mount("/static", StaticFiles(directory=web), name="web")

        @app.get("/", include_in_schema=False)
        def homepage():
            return FileResponse(web / "index.html")

    return app

app = create_app()
