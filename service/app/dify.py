"""Blocking chat-messages call to the Dify application API. No retries, no secret logging."""
import json
import re

import httpx

from .config import ChatSettings

_THINK_BLOCK = re.compile(r"(?is)<think.*?</think[^>]*>|</?think[^>]*>|<!--dify-deepseek-reasoning-->")
_CONTROL_TOKEN = re.compile(r"<\|[^|>]*\|>")


class DifyFailure(Exception):
    """Carries only a fixed safe error code; never upstream exception details."""


def split_answer(raw: str) -> tuple[str, dict | None]:
    """Split the Chatflow reply 'LLM text + verifier JSON' into parts.

    DeepSeek may emit reasoning control tokens and reasoning prose inside the same
    answer string, so control tokens are stripped first and the verifier object is
    located by scanning braces from the end with a real JSON decoder.
    """
    text = _CONTROL_TOKEN.sub("", _THINK_BLOCK.sub("", raw or "")).strip()
    decoder = json.JSONDecoder()
    for start in range(len(text) - 1, -1, -1):
        if text[start] != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[start:])
        except ValueError:
            continue
        if isinstance(parsed, dict) and isinstance(parsed.get("overall_status"), str):
            return text[:start].strip(), parsed
    return text, None


class DifyClient:
    def __init__(self, settings: ChatSettings, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    def chat(self, question: str, conversation_id: str | None) -> dict:
        payload = {
            "inputs": {"question": question},
            "query": question,
            "user": "course-qa-web",
            "response_mode": "blocking",
            "conversation_id": conversation_id or "",
        }
        try:
            with httpx.Client(transport=self.transport, timeout=self.settings.timeout,
                              trust_env=False, follow_redirects=False) as client:
                response = client.post(self.settings.base_url + "/chat-messages",
                                       headers={"Authorization": "Bearer " + self.settings.api_key},
                                       json=payload)
            if response.status_code != 200:
                raise DifyFailure("upstream_http_error")
            data = response.json()
            answer = data["answer"]
            if not isinstance(answer, str):
                raise DifyFailure("invalid_upstream_response")
            return {"answer": answer, "conversation_id": data.get("conversation_id")}
        except httpx.TimeoutException:
            raise DifyFailure("upstream_timeout") from None
        except httpx.HTTPError:
            raise DifyFailure("upstream_unavailable") from None
        except (ValueError, KeyError, TypeError):
            raise DifyFailure("invalid_upstream_response") from None
