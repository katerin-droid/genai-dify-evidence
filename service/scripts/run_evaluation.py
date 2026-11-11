"""Run the 30-question evaluation through the local /api/chat proxy.

Reads evaluation/questions.csv (status=ready), calls the real Dify Chatflow via the
local FastAPI proxy (one independent session per question), stores raw responses in
evaluation/private/raw/ and fills evaluation/results.csv + evaluation/runs.csv.

Usage:
    python service/scripts/run_evaluation.py --run-id run-20261111-improved --endpoint http://127.0.0.1:8765/api/chat
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "evaluation"
RAW_DIR = EVAL / "private" / "raw"


def post_chat(endpoint: str, question: str, timeout: float) -> tuple[dict, float]:
    payload = json.dumps({"question": question}).encode("utf-8")
    req = urlrequest.Request(endpoint, data=payload,
                             headers={"Content-Type": "application/json"}, method="POST")
    start = time.perf_counter()
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        data = {"overall_status": "verification_failed", "error_code": f"proxy_http_{exc.code}",
                "claims": [], "answer": "", "evidence_count": 0, "message": str(exc)}
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        data = {"overall_status": "verification_failed", "error_code": "proxy_unavailable",
                "claims": [], "answer": "", "evidence_count": 0, "message": str(exc)}
    latency_ms = (time.perf_counter() - start) * 1000
    return data, latency_ms


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8765/api/chat")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--app-name", default="课程问答证据核验")
    parser.add_argument("--app-version", default="#3")
    parser.add_argument("--dify-version", default="1.19.0")
    parser.add_argument("--kb-index-mode", default="high_quality")
    parser.add_argument("--embedding-model", default="BAAI/bge-m3")
    parser.add_argument("--llm-model", default="deepseek-flash")
    parser.add_argument("--top-k", default="5")
    parser.add_argument("--score-threshold", default="")
    parser.add_argument("--operator", default="刘英超")
    args = parser.parse_args()

    questions_path = EVAL / "questions.csv"
    with questions_path.open(encoding="utf-8-sig", newline="") as fh:
        questions = [row for row in csv.DictReader(fh) if row.get("status") == "ready"]
    if not questions:
        print("no ready questions found", file=sys.stderr)
        return 1

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    commit = git_commit()
    started_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    results_path = EVAL / "results.csv"
    fieldnames = ["run_id", "question_id", "claim_id", "mode", "overall_status",
                  "claim_status", "support_label", "score", "error_code", "latency_ms",
                  "model", "commit", "checked_at", "notes"]
    write_header = not results_path.exists() or results_path.stat().st_size == 0
    rows = []
    for index, q in enumerate(questions, 1):
        qid = q["question_id"]
        data, latency_ms = post_chat(args.endpoint, q["question"], args.timeout)
        checked_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        (RAW_DIR / f"{args.run_id}-{qid}.json").write_text(
            json.dumps({"question": q["question"], "response": data, "latency_ms": latency_ms},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        claims = data.get("claims") or []
        if not claims:
            rows.append({"run_id": args.run_id, "question_id": qid, "claim_id": f"{qid}-S0",
                         "mode": "improved", "overall_status": data.get("overall_status", ""),
                         "claim_status": "", "support_label": "", "score": "",
                         "error_code": data.get("error_code") or "",
                         "latency_ms": f"{latency_ms:.0f}", "model": args.llm_model,
                         "commit": commit, "checked_at": checked_at,
                         "notes": (data.get("message") or "")[:200]})
        for i, claim in enumerate(claims, 1):
            rows.append({"run_id": args.run_id, "question_id": qid, "claim_id": f"{qid}-S{i}",
                         "mode": "improved", "overall_status": data.get("overall_status", ""),
                         "claim_status": claim.get("status", ""), "support_label": "",
                         "score": "", "error_code": data.get("error_code") or "",
                         "latency_ms": f"{latency_ms:.0f}", "model": args.llm_model,
                         "commit": commit, "checked_at": checked_at,
                         "notes": (claim.get("claim") or "")[:200]})
        print(f"[{index}/{len(questions)}] {qid} {data.get('overall_status')} "
              f"claims={len(claims)} {latency_ms/1000:.1f}s", flush=True)

    with results_path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)

    finished_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    runs_path = EVAL / "runs.csv"
    runs_fields = ["run_id", "mode", "app_name", "app_version", "dify_version",
                   "kb_index_mode", "embedding_model", "llm_model", "top_k",
                   "score_threshold", "commit", "started_at", "finished_at",
                   "operator", "notes"]
    runs_header = not runs_path.exists() or runs_path.stat().st_size == 0
    with runs_path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=runs_fields)
        if runs_header:
            writer.writeheader()
        writer.writerow({"run_id": args.run_id, "mode": "improved",
                         "app_name": args.app_name, "app_version": args.app_version,
                         "dify_version": args.dify_version, "kb_index_mode": args.kb_index_mode,
                         "embedding_model": args.embedding_model, "llm_model": args.llm_model,
                         "top_k": args.top_k, "score_threshold": args.score_threshold,
                         "commit": commit, "started_at": started_at,
                         "finished_at": finished_at, "operator": args.operator,
                         "notes": "Dify Chatflow 含 /verify 核验节点；每题独立会话。"})
    print(f"done: {len(rows)} rows -> {results_path.name}, run -> {runs_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
