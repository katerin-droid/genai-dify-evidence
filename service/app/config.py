"""Mock-only configuration; never loads dotenv or API keys."""
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    mode: str = "mock"

def get_settings() -> Settings:
    mode = os.getenv("VERIFIER_MODE", "mock")
    if mode != "mock":
        raise ValueError("Only mock mode is supported in phase one")
    return Settings(mode=mode)
