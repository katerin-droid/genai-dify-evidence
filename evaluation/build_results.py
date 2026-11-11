"""把 evaluation/private 下的真实运行记录汇总成 runs.csv / results.csv。

用法（仓库根目录）：
    python evaluation/build_results.py

数据来源：
- evaluation/private/raw/*.json        本地 /api/chat 批量运行结果（2026-11-11）
- evaluation/private/raw-cloud/*.json  云端 5b1bb0b 补跑结果（原 6 道 verification_failed）

对齐方法：系统陈述与人工金标按同题内字符二元组相似度取最佳匹配，
相似度 < 0.35 记为未对齐（support_label 留空），不计入陈述级准确率分母。
"""

import csv
import difflib
import json
import pathlib
import statistics
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent
PRIVATE = ROOT / "private"
RUN_LOCAL = "run-20261111-improved"
RUN_CLOUD = "run-20261111-improved-cloud"
COMMIT_LOCAL = "0e845fe"
COMMIT_CLOUD = "5b1bb0b4d5ae2b95204a283c6ecd067c1f8708c7"
ALIGN_THRESHOLD = 0.35

QUESTIONS_HEADER = ["run_id", "question_id", "claim_id", "mode", "overall_status",
                    "claim_status", "support_label", "score", "error_code",
                    "latency_ms", "model", "commit", "checked_at", "notes"]
RUNS_HEADER = ["run_id", "mode", "app_name", "app_version", "dify_version",
               "kb_index_mode", "embedding_model", "llm_model", "top_k",
               "score_threshold", "commit", "started_at", "finished_at",
               "operator", "notes"]


def _ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a or "", b or "").ratio()


def load(path: pathlib.Path, run_id: str) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    qid = path.stem.rsplit("-Q", 1)[-1][:2]
    return {"run_id": run_id, "question_id": f"Q{qid}",
            "latency_ms": round(data["latency_ms"]), "response": data["response"]}


def main() -> None:
    questions = {r["question_id"]: r for r in csv.DictReader(
        open(ROOT / "questions.csv", encoding="utf-8-sig"))}
    gold: dict[str, list[dict]] = defaultdict(list)
    for row in csv.DictReader(open(ROOT / "gold_labels.csv", encoding="utf-8-sig")):
        gold[row["question_id"]].append(row)

    records = [load(p, RUN_LOCAL) for p in sorted((PRIVATE / "raw").glob("*.json"))]
    cloud = [load(p, RUN_CLOUD) for p in sorted((PRIVATE / "raw-cloud").glob("*.json"))]
    rerun = {r["question_id"] for r in cloud}
    records = [r for r in records if r["question_id"] not in rerun] + cloud
    records.sort(key=lambda r: r["question_id"])

    rows, metrics = [], []
    for rec in records:
        resp, qid = rec["response"], rec["question_id"]
        claims = resp.get("claims") or []
        candidates = gold[qid]
        for idx, claim in enumerate(claims, start=1):
            best, score = None, 0.0
            for g in candidates:
                ratio = _ratio(claim.get("claim", ""), g["claim_text"])
                if ratio > score:
                    best, score = g, ratio
            aligned = best if score >= ALIGN_THRESHOLD else None
            rows.append({
                "run_id": rec["run_id"], "question_id": qid,
                "claim_id": f"{qid}-S{idx}", "mode": "improved",
                "overall_status": resp.get("overall_status", ""),
                "claim_status": claim.get("status", ""),
                "support_label": aligned["gold_status"] if aligned else "",
                "score": "", "error_code": resp.get("error_code") or "",
                "latency_ms": rec["latency_ms"], "model": "deepseek-chat",
                "commit": COMMIT_CLOUD if rec["run_id"] == RUN_CLOUD else COMMIT_LOCAL,
                "checked_at": "2026-11-11",
                "notes": (f"gold={aligned['claim_id']} sim={score:.2f}" if aligned
                          else f"unaligned sim={score:.2f}"),
            })
            metrics.append((questions[qid]["category"], claim.get("status", ""),
                            aligned["gold_status"] if aligned else None))

    with open(ROOT / "results.csv", "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=QUESTIONS_HEADER)
        writer.writeheader()
        writer.writerows(rows)

    latencies = sorted(r["latency_ms"] for r in records)
    runs = [
        {"run_id": RUN_LOCAL, "mode": "improved", "app_name": "课程问答证据核验",
         "app_version": "3", "dify_version": "1.19.0", "kb_index_mode": "high_quality",
         "embedding_model": "硅基流动 bge-m3", "llm_model": "deepseek-chat", "top_k": "5",
         "score_threshold": "", "commit": COMMIT_LOCAL,
         "started_at": "2026-11-11T17:20:00+08:00", "finished_at": "2026-11-11T17:45:00+08:00",
         "operator": "刘英超",
         "notes": "本地 /api/chat 顺序跑 30 题，每题独立会话；6 题 verification_failed"},
        {"run_id": RUN_CLOUD, "mode": "improved", "app_name": "课程问答证据核验",
         "app_version": "3", "dify_version": "1.19.0", "kb_index_mode": "high_quality",
         "embedding_model": "硅基流动 bge-m3", "llm_model": "deepseek-chat", "top_k": "5",
         "score_threshold": "", "commit": COMMIT_CLOUD,
         "started_at": "2026-11-11T20:10:00+08:00", "finished_at": "2026-11-11T20:12:00+08:00",
         "operator": "刘英超",
         "notes": "云端补跑 6 道失败题（verifier max_tokens=8192 后），全部成功"},
    ]
    with open(ROOT / "runs.csv", "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=RUNS_HEADER)
        writer.writeheader()
        writer.writerows(runs)

    status = Counter(r["response"].get("overall_status", "") for r in records)
    aligned = [m for m in metrics if m[2] is not None]
    agree = sum(1 for _, s, g in aligned if s == g)
    by_cat: dict[str, list] = defaultdict(list)
    for m in metrics:
        by_cat[m[0]].append(m)
    summary = {
        "questions": len(records),
        "overall_status": dict(status),
        "claims": len(metrics),
        "claim_status": dict(Counter(m[1] for m in metrics)),
        "aligned_claims": len(aligned),
        "aligned_agreement": round(agree / len(aligned), 3) if aligned else None,
        "latency_ms": {"avg": round(statistics.mean(latencies)),
                       "p50": latencies[len(latencies) // 2],
                       "p95": latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))],
                       "max": latencies[-1], "min": latencies[0]},
        "by_category": {},
    }
    for cat, items in sorted(by_cat.items()):
        a = [m for m in items if m[2] is not None]
        summary["by_category"][cat] = {
            "claims": len(items), "aligned": len(a),
            "agreement": round(sum(1 for _, s, g in a if s == g) / len(a), 3) if a else None,
            "claim_status": dict(Counter(m[1] for m in items)),
        }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
