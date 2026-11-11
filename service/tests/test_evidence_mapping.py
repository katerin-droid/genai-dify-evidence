import pytest
from pydantic import ValidationError

from service.app.schemas import EvidenceVerifyRequest
from service.scripts.validate_evidence_mapping import (
    build_evidence,
    build_request,
    real_excerpt,
    validate_request,
)


def test_real_excerpt_comes_from_repository_document():
    excerpt = real_excerpt()
    assert "citations" in excerpt
    assert "连续精确子串" in excerpt


def test_mapping_keeps_only_allowed_fields():
    evidence = build_evidence(
        [
            {
                "content": "原始证据正文。",
                "title": "讲义.pdf",
                "score": 0.88,
                "metadata": {"document_id": "doc-1", "page": 3},
            }
        ]
    )

    assert evidence == [
        {
            "id": "E1",
            "content": "原始证据正文。",
            "source": "讲义.pdf",
            "page": 3,
        }
    ]


def test_mapping_omits_page_when_absent_or_invalid():
    evidence = build_evidence(
        [
            {"content": "第一段", "title": "a.pdf", "metadata": {"page": 0}},
            {"content": "第二段", "title": "a.pdf", "metadata": {"page": ""}},
        ]
    )

    assert "page" not in evidence[0]
    assert "page" not in evidence[1]


def test_mapping_deduplicates_identical_content_and_numbers_ids():
    evidence = build_evidence(
        [
            {"content": "重复内容", "title": "a.pdf"},
            {"content": " 重复内容 ", "title": "a.pdf"},
            {"content": "另一段", "title": "a.pdf"},
        ]
    )

    assert [item["id"] for item in evidence] == ["E1", "E2"]
    assert evidence[1]["content"] == "另一段"


def test_request_validates_with_verifier_schema():
    payload = build_request(
        question="citations 是什么？",
        answer="citations 是精确原文片段列表。",
        chunks=[{"content": real_excerpt(), "title": "docs/verify-api.md", "metadata": {"page": 5}}],
    )
    request = validate_request(payload)

    assert isinstance(request, EvidenceVerifyRequest)
    assert request.evidence[0].evidence_id == "E1"
    assert request.evidence[0].page == 5


def test_extra_field_is_rejected():
    payload = build_request(
        question="问题",
        answer="答案",
        chunks=[{"content": "证据", "title": "a.pdf"}],
    )
    payload["evidence"][0]["score"] = 0.9

    with pytest.raises(ValidationError):
        validate_request(payload)
