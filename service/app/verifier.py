from .schemas import VerifyRequest, VerifyResponse
from .schemas import EvidenceVerifyRequest, EvidenceVerifyResponse, ModelResult
from .deepseek import CompletionFailure, DeepSeekClient
from pydantic import ValidationError

def verify_mock(request: VerifyRequest) -> VerifyResponse:
    """Return a contract placeholder, never a semantic verdict."""
    return VerifyResponse(evidence_count=len(request.evidence))


def verify_evidence(request: EvidenceVerifyRequest, client: DeepSeekClient) -> EvidenceVerifyResponse:
    def failed(code: str) -> EvidenceVerifyResponse:
        return EvidenceVerifyResponse(overall_status="verification_failed", evidence_count=len(request.evidence),
                                      error_code=code, message="Verification could not be completed: " + code)

    if not request.evidence:
        return EvidenceVerifyResponse(overall_status="unsupported", evidence_count=0, error_code="no_evidence",
                                      message="No evidence supplied; model was not called. This is evidence insufficiency, not a claim-level judgment.")
    try:
        content = client.complete(request)
        result = ModelResult.model_validate_json(content)
        if not result.claims:
            return failed("no_verifiable_claims")
        evidence = {e.evidence_id: e.text for e in request.evidence}
        for claim in result.claims:
            ids = set(claim.evidence_ids)
            if not ids <= evidence.keys():
                return failed("unknown_evidence_id")
            if len(ids) != len(claim.evidence_ids):
                return failed("invalid_citations")
            pairs = [(c.evidence_id, c.quote) for c in claim.citations]
            if len(pairs) != len(set(pairs)):
                return failed("invalid_citations")
            for citation in claim.citations:
                if citation.evidence_id not in evidence:
                    return failed("unknown_evidence_id")
                if citation.evidence_id not in ids or citation.quote not in evidence[citation.evidence_id]:
                    return failed("invalid_citations")
            cited = {c.evidence_id for c in claim.citations}
            if cited != ids or (claim.status in {"supported", "partially_supported"} and not ids):
                return failed("missing_citations")
        statuses = {c.status for c in result.claims}
        if "verification_failed" in statuses:
            return failed("claim_verification_failed")
        overall = next(iter(statuses)) if len(statuses) == 1 else "partially_supported"
        return EvidenceVerifyResponse(overall_status=overall, claims=result.claims,
                                      evidence_count=len(request.evidence), message="Evaluated against supplied evidence only.")
    except CompletionFailure as exc:
        return failed(str(exc))
    except ValidationError:
        return failed("invalid_model_output")
    except Exception:
        # Never echo provider errors, raw model output, prompts or credentials.
        return failed("internal_error")
