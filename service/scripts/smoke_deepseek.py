"""Explicitly opt-in paid check using synthetic evidence. Not run during development."""
import argparse


def main():
    parser = argparse.ArgumentParser(description="Manual paid DeepSeek smoke check")
    parser.add_argument("--allow-paid", action="store_true", help="Authorize one paid request")
    parser.add_argument("--env-file", default=".env", help="Local ignored configuration file")
    args = parser.parse_args()
    if not args.allow_paid:
        parser.error("Requires --allow-paid; may consume API credits")
    from dotenv import load_dotenv
    from service.app.config import get_settings
    from service.app.deepseek import DeepSeekClient
    from service.app.schemas import EvidenceVerifyRequest
    from service.app.verifier import verify_evidence
    load_dotenv(args.env_file, override=False)
    try:
        settings = get_settings()
    except ValueError:
        parser.exit(2, "Invalid or missing DeepSeek configuration; values withheld.\n")
    if settings.mode != "deepseek":
        parser.error("Set VERIFIER_MODE=deepseek explicitly")
    request = EvidenceVerifyRequest.model_validate({
        "question": "合成课程时长是多少？", "answer": "合成课程持续两小时。",
        "evidence": [{"id": "demo-1", "content": "合成课程持续两小时。"}]})
    result = verify_evidence(request, DeepSeekClient(settings))
    # No prompts, raw model responses, API errors or credentials are printed.
    print({"overall_status": result.overall_status, "claims_count": len(result.claims),
           "error_code": result.error_code})
    return 1 if result.overall_status == "verification_failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
