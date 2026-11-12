from typing import Annotated, Literal, Any
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000, strict=True)]
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128, strict=True)]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Evidence(StrictModel):
    evidence_id: Identifier = Field(validation_alias=AliasChoices("id", "evidence_id"))
    text: Text = Field(validation_alias=AliasChoices("content", "text"))
    source: Annotated[str, StringConstraints(max_length=2000, strict=True)] | None = None
    page: Annotated[int, Field(strict=True, ge=1)] | Identifier | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class VerifyRequest(StrictModel):
    question: Text
    answer: Text
    evidence: list[Evidence] = Field(min_length=1, max_length=50)

class VerifyResponse(StrictModel):
    mode: Literal["mock"] = "mock"
    overall_status: Literal["not_evaluated"] = "not_evaluated"
    support_label: None = None
    score: None = None
    evidence_count: int = Field(ge=1)
    message: str = "Mock response only; no evidence verification or model call performed."


class EvidenceVerifyRequest(VerifyRequest):
    evidence: list[Evidence] = Field(max_length=50)

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [e.evidence_id for e in self.evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("Evidence IDs must be unique")
        return self


Status = Literal["supported", "partially_supported", "unsupported", "verification_failed"]


SourceStr = Annotated[str, StringConstraints(max_length=2000, strict=True)]
# page may come from Dify as "" (no page in markdown chunks) or a real 1-based int; allow both.
PageNum = Annotated[int, Field(strict=True, ge=1)] | Identifier | Literal[""]


class Citation(StrictModel):
    evidence_id: Identifier
    quote: Text
    # Optional enrichment merged in downstream: may come from Dify workflow (结果补全)
    # or from the verifier itself. Empty string / None are both valid.
    source: SourceStr | None = None
    page: PageNum | None = None


class ClaimResult(StrictModel):
    claim: Text
    status: Status
    evidence_ids: list[Identifier] = Field(max_length=50)
    reason: Text
    citations: list[Citation] = Field(default_factory=list, max_length=50)


class ModelResult(StrictModel):
    claims: list[ClaimResult] = Field(max_length=5)


class EvidenceVerifyResponse(StrictModel):
    mode: Literal["deepseek"] = "deepseek"
    overall_status: Status
    claims: list[ClaimResult] = Field(default_factory=list, max_length=5)
    evidence_count: int = Field(ge=0)
    message: str
    error_code: str | None = None


Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000, strict=True)]


class ChatRequest(StrictModel):
    question: Question
    conversation_id: Identifier | None = None


class ChatResponse(StrictModel):
    """Unified /api/chat payload; upstream failures stay HTTP 200 with verification_failed."""
    mode: Literal["dify"] = "dify"
    answer: str = ""
    overall_status: Status
    claims: list[ClaimResult] = Field(default_factory=list, max_length=5)
    evidence_count: int = Field(default=0, ge=0)
    message: str
    error_code: str | None = None
    conversation_id: str | None = None
