from .schemas import VerifyRequest, VerifyResponse

def verify_mock(request: VerifyRequest) -> VerifyResponse:
    """Return a contract placeholder, never a semantic verdict."""
    return VerifyResponse(evidence_count=len(request.evidence))
