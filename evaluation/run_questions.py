"""通过 /api/chat 顺序跑评测题并保存原始响应。

用法（仓库根目录，先启动服务或使用云端地址）：
    python evaluation/run_questions.py --base-url http://127.0.0.1:8765
    python evaluation/run_questions.py --base-url http://113.44.227.132 --ids Q06,Q09

原始响应写到 evaluation/private/raw/（默认，已被 .gitignore 忽略），
再由 evaluation/build_results.py 汇总成 results.csv / runs.csv。
每题使用独立会话，不传 conversation_id，避免多轮上下文污染。
"""

import argparse
import json
import pathlib
import time

import httpx

ROOT = pathlib.Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True, help="服务地址，如 http://127.0.0.1:8765")
    parser.add_argument("--ids", default="", help="逗号分隔题号；留空表示全部")
    parser.add_argument("--out", default=str(ROOT / "private" / "raw"), help="输出目录")
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    import csv
    questions = {r["question_id"]: r["question"] for r in csv.DictReader(
        open(ROOT / "questions.csv", encoding="utf-8-sig"))}
    ids = [x.strip() for x in args.ids.split(",") if x.strip()] or sorted(questions)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=args.timeout, trust_env=False) as client:
        for qid in ids:
            started = time.time()
            try:
                resp = client.post(f"{args.base_url.rstrip('/')}/api/chat",
                                   json={"question": questions[qid]})
                body = resp.json()
            except Exception as exc:  # 网络或解析失败也要落盘，便于统计
                print(f"{qid} EXC {type(exc).__name__} {str(exc)[:80]}")
                continue
            latency = (time.time() - started) * 1000
            (out / f"run-{time.strftime('%Y%m%d')}-improved-{qid}.json").write_text(
                json.dumps({"question": questions[qid], "response": body,
                            "latency_ms": latency}, ensure_ascii=False, indent=2),
                encoding="utf-8")
            print(f"{qid} {resp.status_code} {body.get('overall_status')} "
                  f"claims={len(body.get('claims') or [])} "
                  f"{body.get('error_code')} {latency / 1000:.1f}s")


if __name__ == "__main__":
    main()
