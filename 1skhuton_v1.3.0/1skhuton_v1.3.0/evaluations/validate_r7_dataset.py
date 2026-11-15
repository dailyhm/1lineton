#!/usr/bin/env python3
"""Validate R7 hand-authored demo fixtures against the R2 contract."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IDS = {"EXAMPLE_DEBUGGING", "EXAMPLE_CONCEPT", "EXAMPLE_PROBLEM_SOLVING"}
CATEGORIES = {"common", "supplement", "unique", "error", "judgment_hold"}
FIELDS = {
    "common": {"title", "user_quote", "ai_view", "reason"},
    "supplement": {"title", "user_quote", "ai_view", "reason"},
    "unique": {"title", "user_quote", "reason"},
    "error": {"title", "user_quote", "conflict", "how_to_check"},
    "judgment_hold": {"title", "user_quote", "reason", "follow_up_question"},
}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def main():
    ds = json.loads((ROOT / "R7_demo_dataset_v1.3.0.json").read_text(encoding="utf-8"))
    cases = ds.get("cases")
    require(isinstance(cases, list), "cases must be an array")
    require({c.get("case_id") for c in cases} == EXPECTED_IDS, "R7 case IDs mismatch")
    for case in cases:
        cid = case["case_id"]
        qg = case["question_generation"]
        public, private = qg["public"], qg["private"]
        require(set(public) == {"chat_title", "chat_summary", "choices"}, f"{cid}: public fields")
        require(len(public["choices"]) == 3, f"{cid}: choices must contain 3")
        require(set(private) == {"guidance", "reference_answer"}, f"{cid}: private fields")
        require(len(private["guidance"]) == 2, f"{cid}: guidance must contain 2")
        for g in private["guidance"]:
            require(set(g) == {"look_at", "try_this"}, f"{cid}: guidance fields")
        comparison = case["comparison"]
        require(set(comparison) == CATEGORIES, f"{cid}: comparison categories")
        thought = case["user_thought"]
        for category, items in comparison.items():
            require(isinstance(items, list), f"{cid}: {category} must be list")
            for item in items:
                require(set(item) == FIELDS[category], f"{cid}: {category} item fields")
                require(bool(item["title"].strip()), f"{cid}: title required")
                quote = item["user_quote"]
                if category in {"supplement", "judgment_hold"} and quote == "":
                    pass
                else:
                    require(bool(quote) and quote in thought, f"{cid}: invalid quote in {category}")
        learning = case["basic_learning"]
        require(set(learning) == {"summary", "example_code", "observe", "change"}, f"{cid}: learning fields")
        require(case.get("data_origin") == "MANUALLY_AUTHORED_DEMO_FIXTURE_NOT_LIVE_MODEL_OUTPUT",
                f"{cid}: must be marked manually authored")
    print(f"[PASS] R7 {len(cases)} hand-authored cases conform to R2 question/comparison/learning contracts")

if __name__ == "__main__":
    main()
