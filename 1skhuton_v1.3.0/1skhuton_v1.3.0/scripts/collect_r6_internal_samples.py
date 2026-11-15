#!/usr/bin/env python3
"""
Server-side R6 live collection.

Run only in a trusted backend environment where GEMINI_API_KEY is configured.
Unlike the public-API collector, this script captures prepare_question()['private']
for internal QA. Never expose its output through a public endpoint or frontend.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deveil_ai import AIConfig, DeveilAIService, GeminiProvider  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", default=str(ROOT / "R6_collection_inputs.json"))
    parser.add_argument("--output", default=str(ROOT / "R6_internal_live_samples.json"))
    parser.add_argument("--delay", type=float, default=13.0)
    args = parser.parse_args()

    if not os.getenv("GEMINI_API_KEY", "").strip():
        parser.error("GEMINI_API_KEY는 신뢰할 수 있는 서버 환경변수로 설정해야 합니다.")
    config = AIConfig()
    service = DeveilAIService(GeminiProvider(config), config)
    inputs = json.loads(Path(args.inputs).read_text(encoding="utf-8"))
    samples = []
    last_call = 0.0

    def pace():
        nonlocal last_call
        wait = args.delay - (time.monotonic() - last_call)
        if last_call and wait > 0:
            time.sleep(wait)
        last_call = time.monotonic()

    for scenario in inputs["scenarios"]:
        group = scenario["sample_group"]
        question = scenario["question"]
        code = scenario.get("code", "")
        question_type = scenario["question_type"]

        try:
            pace()
            prepared = service.prepare_question(question, code, question_type)
            samples.append({
                "sample_id": group + "-QUESTION-INTERNAL",
                "task": "question_generation",
                "request": {
                    "question": question, "code": code,
                    "selected_type": question_type
                },
                "response": {
                    "public": prepared["public"],
                    "private": prepared["private"],
                    "security": prepared["security"]
                },
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "is_live_model_output": True,
                "contains_private_server_data": True
            })
            for level in (1, 2):
                samples.append({
                    "sample_id": group + f"-GUIDANCE-{level}",
                    "task": "guidance_retrieval",
                    "request": {"level": level},
                    "response": service.get_guidance(prepared["private"], level),
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "is_live_model_output": False,
                    "contains_private_server_data": True,
                    "note": "서버 내부 private 데이터에서 추출한 단일 단계 안내"
                })

            pace()
            comparison = service.compare(
                question, code, question_type, scenario["original_thought"],
                prepared["private"]["reference_answer"]
            )
            samples.append({
                "sample_id": group + "-COMPARE",
                "task": "comparison",
                "request": {
                    "question": question, "code": code,
                    "question_type": question_type,
                    "original_thought": scenario["original_thought"]
                },
                "response": comparison,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "is_live_model_output": True,
                "contains_private_server_data": False
            })

            pace()
            learning = service.basic_learning(question, code, question_type)
            samples.append({
                "sample_id": group + "-LEARNING",
                "task": "basic_learning",
                "request": {
                    "question": question, "code": code,
                    "question_type": question_type
                },
                "response": learning,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "is_live_model_output": True,
                "contains_private_server_data": False
            })
            print(f"[완료] {group}: question/comparison/learning collected")
        except Exception as exc:
            samples.append({
                "sample_id": group + "-ERROR",
                "task": "collection_error",
                "error": str(exc),
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "is_live_model_output": False
            })
            print(f"[실패] {group}: {exc}", file=sys.stderr)

    counts = {}
    for sample in samples:
        if sample.get("is_live_model_output"):
            task = sample["task"]
            counts[task] = counts.get(task, 0) + 1
    result = {
        "dataset_name": "Deveil R6 Internal Live Samples",
        "version": "1.0.0",
        "status": "LIVE_COLLECTION_COMPLETE" if all(
            counts.get(task, 0) >= 2
            for task in ("question_generation", "comparison", "basic_learning")
        ) else "PARTIAL_OR_FAILED_COLLECTION",
        "source": "Direct DeveilAIService invocation on trusted backend environment",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "successful_live_sample_counts": counts,
        "contains_private_server_data": True,
        "storage_warning": "RESTRICTED_INTERNAL_QA_ONLY_NEVER_RETURN_TO_PUBLIC_API",
        "samples": samples
    }
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    print("저장:", args.output)
    print("실제 모델 출력 건수:", counts)
    print("주의: 이 파일에는 reference_answer/guidance가 포함됩니다. 서버 내부 QA 용도로만 보관하세요.")
    return 0 if result["status"] == "LIVE_COLLECTION_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
