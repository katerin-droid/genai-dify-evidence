"""Environment configuration. Never prints credentials or loads dotenv files."""
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit

@dataclass(frozen=True)
class Settings:
    mode: str = "mock"
    api_key: str = field(default="", repr=False)
    base_url: str = "https://api.deepseek.com"
    model: str = ""
    timeout: float = 30.0
    max_tokens: int = 8192

    def __post_init__(self):
        if self.mode not in {"mock", "deepseek"}:
            raise ValueError("Only mock or deepseek modes are supported")
        if self.mode == "deepseek":
            url = urlsplit(self.base_url)
            if (url.scheme != "https" or not url.hostname or url.username or url.password
                    or url.query or url.fragment):
                raise ValueError("DEEPSEEK_BASE_URL must be an HTTPS URL without credentials/query/fragment")
            if not self.api_key.strip() or not self.model.strip():
                raise ValueError("DeepSeek mode requires API key and explicit model configuration")
            if not 0 < self.timeout <= 300:
                raise ValueError("DeepSeek timeout must be between 0 and 300 seconds")
            if not 256 <= self.max_tokens <= 65536:
                raise ValueError("DeepSeek max_tokens must be between 256 and 65536")

def get_settings() -> Settings:
    mode = os.getenv("VERIFIER_MODE", "mock")
    if mode != "deepseek":
        return Settings(mode=mode)
    return Settings(mode=mode, api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
                    model=os.getenv("DEEPSEEK_MODEL", ""),
                    timeout=float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "30")),
                    max_tokens=int(os.getenv("DEEPSEEK_MAX_TOKENS", "8192")))


@dataclass(frozen=True)
class ChatSettings:
    """Dify application API settings for the /api/chat proxy. Never prints credentials."""
    base_url: str
    api_key: str = field(default="", repr=False)
    timeout: float = 120.0

    def __post_init__(self):
        url = urlsplit(self.base_url)
        if (url.scheme not in {"http", "https"} or not url.hostname or url.username
                or url.password or url.query or url.fragment):
            raise ValueError("DIFY_API_BASE_URL must be an HTTP(S) URL without credentials/query/fragment")
        if not self.api_key.strip():
            raise ValueError("Chat proxy requires a Dify application API key")
        if not 0 < self.timeout <= 300:
            raise ValueError("Dify timeout must be between 0 and 300 seconds")


def get_chat_settings() -> ChatSettings | None:
    """Returns None when the Dify proxy is not configured; the endpoint reports 503."""
    key = os.getenv("DIFY_API_KEY", "")
    if not key.strip():
        return None
    return ChatSettings(
        base_url=os.getenv("DIFY_API_BASE_URL", "http://127.0.0.1:8081/v1").rstrip("/"),
        api_key=key,
        timeout=float(os.getenv("DIFY_TIMEOUT_SECONDS", "120")))
