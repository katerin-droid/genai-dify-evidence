from fastapi import FastAPI
from .config import Settings, get_settings
from .schemas import VerifyRequest, VerifyResponse, EvidenceVerifyRequest, EvidenceVerifyResponse
from .verifier import verify_mock, verify_evidence
from .deepseek import DeepSeekClient
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

def create_app(settings: Settings | None = None, completion_client: DeepSeekClient | None = None) -> FastAPI:
    settings = settings or get_settings()
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

    @app.get("/api/ui-status")
    def ui_status():
        return {"dify_connected": False, "chat_available": False,
                "verification_mode": settings.mode,
                "message": "服务尚未连接：尚未配置 Dify 问答代理与工作流联调。"}

    web = Path(__file__).resolve().parents[2] / "web"
    if web.is_dir():
        app.mount("/static", StaticFiles(directory=web), name="web")

        @app.get("/", include_in_schema=False)
        def homepage():
            return FileResponse(web / "index.html")

    return app

app = create_app()
