"""Validate Dify retrieval-chunk to verifier evidence mapping without network calls.

This script uses a real excerpt from docs/verify-api.md as fixed evidence. It does
not represent retrieval quality and does not call Dify or DeepSeek.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from service.app.schemas import EvidenceVerifyRequest

ROOT = Path(__file__).resolve().parents[2]
VERIFY_API_DOC = ROOT / "docs" / "verify-api.md"


def real_excerpt() -> str:
    """Return a real, unchanged line from the repository's verify-api document."""
    text = VERIFY_API_DOC.read_text(encoding="utf-8")
    marker = "citations：精确原文片段列表"
    for line in text.splitlines():
        candidate = line.strip()
        if candidate.startswith("- "):
            candidate = candidate[2:]
        if candidate.startswith(marker):
            return candidate
    raise RuntimeError(f"Could not find fixed evidence excerpt in {VERIFY_API_DOC}")


def build_evidence(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map Dify-like retrieval chunks to the verifier's strict evidence schema."""
    evidence: list[dict[str, Any]] = []
    seen: set[str] = set()

    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue

        content = chunk.get("content") or chunk.get("text") or ""
        if not isinstance(content, str):
            continue
        content = content.strip()
        if not content or content in seen:
            continue
        seen.add(content)

        metadata = chunk.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        source = (
            chunk.get("title")
            or metadata.get("document_name")
            or metadata.get("source")
            or "unknown"
        )
        source = str(source).strip()[:2000] or "unknown"

        item: dict[str, Any] = {
            "id": f"E{len(evidence) + 1}",
            "content": content[:20000],
            "source": source,
        }

        page = metadata.get("page", chunk.get("page"))
        if isinstance(page, int) and not isinstance(page, bool) and page >= 1:
            item["page"] = page
        elif isinstance(page, str) and page.strip():
            item["page"] = page.strip()[:128]

        evidence.append(item)
        if len(evidence) >= 50:
            break

    return evidence


def build_request(question: str, answer: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "question": question,
        "answer": answer,
        "evidence": build_evidence(chunks),
    }


def validate_request(payload: dict[str, Any]) -> EvidenceVerifyRequest:
    return EvidenceVerifyRequest.model_validate(payload)


def main() -> None:
    excerpt = real_excerpt()

    # Deliberately include fields Dify may return but the verifier forbids.
    chunks = [
        {
            "content": excerpt,
            "title": "docs/verify-api.md",
            "score": 0.91,
            "metadata": {
                "document_id": "doc-verify-api",
                "document_name": "verify-api.md",
                "page": 5,
                "score": 0.91,
            },
        },
        {
            "content": "supported/partially_supported 必须至少引用一个 ID 并提供对应原文。",
            "title": "docs/verify-api.md",
            "metadata": {"document_id": "doc-verify-api"},
        },
    ]

    payload = build_request(
        question="核验接口对 citations 有什么要求？",
        answer="citations 是精确原文片段列表，每项包含 evidence_id 与 quote。",
        chunks=chunks,
    )
    request = validate_request(payload)

    assert set(payload["evidence"][0]) == {"id", "content", "source", "page"}
    assert set(payload["evidence"][1]) == {"id", "content", "source"}
    assert len(request.evidence) == 2
    assert request.evidence[0].evidence_id == "E1"

    bad = json.loads(json.dumps(payload))
    bad["evidence"][0]["score"] = 0.91
    try:
        validate_request(bad)
    except ValidationError:
        pass
    else:
        raise SystemExit("FAIL: verifier accepted an extra evidence field")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("OK: evidence mapping keeps only id/content/source/page; extra fields are rejected.")


if __name__ == "__main__":
    main()
