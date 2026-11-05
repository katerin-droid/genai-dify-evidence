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

def get_settings() -> Settings:
    mode = os.getenv("VERIFIER_MODE", "mock")
    if mode != "deepseek":
        return Settings(mode=mode)
    return Settings(mode=mode, api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
                    model=os.getenv("DEEPSEEK_MODEL", ""),
                    timeout=float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "30")))
