"""Blocking chat-messages call to the Dify application API. No retries, no secret logging."""
import json
import re

import httpx

from .config import ChatSettings

_THINK_BLOCK = re.compile(r"(?is)<think.*?</think[^>]*>|</?think[^>]*>|<!--dify-deepseek-reasoning-->")


class DifyFailure(Exception):
    """Carries only a fixed safe error code; never upstream exception details."""


def split_answer(raw: str) -> tuple[str, dict | None]:
    """Split the Chatflow reply 'LLM text + blank line + verifier JSON' into parts.

    The verifier body is compact JSON without raw newlines, so the JSON object always
    starts after the last blank line that precedes valid JSON containing overall_status.
    """
    tail = (raw or "").rstrip()
    while True:
        cut = tail.rfind("\n\n")
        candidate = tail[cut + 2:].strip() if cut >= 0 else tail.strip()
        try:
            parsed = json.loads(candidate)
        except ValueError:
            parsed = None
        if isinstance(parsed, dict) and isinstance(parsed.get("overall_status"), str):
            head = tail[:cut] if cut >= 0 else ""
            head = _THINK_BLOCK.sub("", head).strip()
            return head, parsed
        if cut < 0:
            return tail, None
        tail = tail[:cut]


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
