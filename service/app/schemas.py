from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000, strict=True)]
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128, strict=True)]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Evidence(StrictModel):
    evidence_id: Identifier
    text: Text

class VerifyRequest(StrictModel):
    question: Text
    answer: Text
    evidence: list[Evidence] = Field(min_length=1, max_length=50)

class VerifyResponse(StrictModel):
    mode: Literal["mock"] = "mock"
    status: Literal["not_evaluated"] = "not_evaluated"
    support_label: None = None
    score: None = None
    evidence_count: int = Field(ge=1)
    message: str = "Mock response only; no evidence verification or model call performed."
