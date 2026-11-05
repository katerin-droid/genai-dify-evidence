from fastapi import FastAPI
from .config import get_settings
from .schemas import VerifyRequest, VerifyResponse
from .verifier import verify_mock

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Course Evidence Verifier", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": settings.mode}

    @app.post("/verify", response_model=VerifyResponse)
    def verify(request: VerifyRequest) -> VerifyResponse:
        return verify_mock(request)

    return app

app = create_app()
