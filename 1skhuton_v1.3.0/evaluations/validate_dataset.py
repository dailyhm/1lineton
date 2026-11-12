#!/usr/bin/env python3
"""Validate Deveil v1.3.0 evaluation dataset and optional model-output JSON."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "test_cases.json"
TOP_KEYS = {"common", "supplement", "unique", "error", "judgment_hold"}
ITEM_FIELDS = {
    "common": {"title", "user_quote", "ai_view", "reason"},
    "supplement": {"title", "user_quote", "ai_view", "reason"},
    "unique": {"title", "user_quote", "reason"},
    "error": {"title", "user_quote", "conflict", "how_to_check"},
    "judgment_hold": {"title", "user_quote", "reason", "follow_up_question"},
}
ALLOW_EMPTY_QUOTE = {"supplement", "judgment_hold"}


def validate_result(result, thought):
    errors = []
    if not isinstance(result, dict):
        return ["결과 최상위는 JSON 객체여야 합니다."]
    if set(result) != TOP_KEYS:
        return [f"최상위 키 불일치: 기대 {sorted(TOP_KEYS)}, 실제 {sorted(result)}"]
    for category, fields in ITEM_FIELDS.items():
        items = result.get(category)
        if not isinstance(items, list):
            errors.append(f"{category}는 배열이어야 합니다.")
            continue
        if len(items) > 8:
            errors.append(f"{category} 항목은 최대 8개입니다.")
        for idx, item in enumerate(items):
            where = f"{category}[{idx}]"
            if not isinstance(item, dict):
                errors.append(f"{where}는 객체여야 합니다.")
                continue
            if set(item) != fields:
                errors.append(f"{where} 필드 불일치: 기대 {sorted(fields)}, 실제 {sorted(item)}")
                continue
            if not all(isinstance(v, str) for v in item.values()):
                errors.append(f"{where}의 모든 필드는 문자열이어야 합니다.")
                continue
            if not item["title"].strip():
                errors.append(f"{where}.title은 비어 있을 수 없습니다.")
            quote = item["user_quote"]
            if not quote and category not in ALLOW_EMPTY_QUOTE:
                errors.append(f"{where}.user_quote는 비어 있을 수 없습니다.")
            elif quote and quote not in thought:
                errors.append(f"{where}.user_quote가 사용자 원문에 연속해서 존재하지 않습니다.")
            for key in fields - {"title", "user_quote"}:
                if not item[key].strip():
                    errors.append(f"{where}.{key}는 비어 있을 수 없습니다.")
    return errors


def validate_dataset(ds):
    errors = []
    if not isinstance(ds, dict) or not isinstance(ds.get("cases"), list):
        return ["데이터셋에 cases 배열이 없습니다."]
    if len(ds["cases"]) < 5:
        errors.append("테스트 사례가 5개 미만입니다.")
    ids = set()
    for case in ds["cases"]:
        cid = case.get("id", "<no-id>")
        if cid in ids:
            errors.append(f"중복 사례 ID: {cid}")
        ids.add(cid)
        for field in ("question", "code", "reference_answer", "original_thought"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                errors.append(f"{cid}: {field}가 비어 있거나 문자열이 아닙니다.")
        errors.extend(f"{cid}: {e}" for e in validate_result(case.get("expected_result"), case.get("original_thought", "")))
        if not isinstance(case.get("pass_criteria"), list) or not case["pass_criteria"]:
            errors.append(f"{cid}: pass_criteria가 비어 있습니다.")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", help="검사할 사례 ID")
    ap.add_argument("--result", help="모델 결과 JSON 파일 경로")
    args = ap.parse_args()
    try:
        ds = json.loads(DATASET.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[실패] 데이터셋 JSON 읽기 실패: {exc}")
        return 1
    errors = validate_dataset(ds)
    if errors:
        print("[실패] 데이터셋 검증 오류")
        for error in errors:
            print("-", error)
        return 1
    print(f"[통과] v{ds.get('version')} 데이터셋 구조 / 필수 필드 / 원문 인용 검사 ({len(ds['cases'])}개 사례)")
    if args.result:
        if not args.case:
            print("--result를 사용할 때는 --case도 지정해야 합니다.")
            return 2
        case = next((c for c in ds["cases"] if c["id"] == args.case), None)
        if not case:
            print(f"사례를 찾을 수 없습니다: {args.case}")
            return 2
        try:
            result = json.loads(Path(args.result).read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[실패] 결과 JSON 읽기 실패: {exc}")
            return 1
        errors = validate_result(result, case["original_thought"])
        if errors:
            print("[실패] 모델 결과 구조/인용 검사")
            for error in errors:
                print("-", error)
            return 1
        print(f"[통과] {args.case} 모델 결과 구조와 원문 인용 검사")
    print("참고: 분류 의미의 정확성 및 supplement 사실성은 평가 가이드에 따라 별도 검토해야 합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
