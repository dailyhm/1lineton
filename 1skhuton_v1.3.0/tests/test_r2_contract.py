import json
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

import deveil_ai
import api

class R2ContractTests(unittest.TestCase):
    def test_question_exact_fields_counts_and_private_split(self):
        raw = {
            "chat_title": "제목", "chat_summary": "요약",
            "choices": ["가", "나", "다"],
            "hints": ["첫 번째 힌트입니다.", "두 번째 힌트입니다."],
            "guidance": [
                {"look_at": "관찰 1", "try_this": "구체적인 행동을 첫 번째로 수행해 보세요."},
                {"look_at": "관찰 2", "try_this": "두 번째 값을 바꾸어 결과를 비교해 보세요."},
            ],
            "reference_answer": "기준 답변"
        }
        cleaned = deveil_ai.validate_question_result(raw)
        self.assertEqual(len(cleaned["choices"]), 3)
        self.assertEqual(len(cleaned["guidance"]), 2)
        self.assertEqual(len(cleaned["hints"]), 2)
        for extra in ("question_type", "example_sentence"):
            bad = dict(raw, **{extra: "not allowed"})
            with self.assertRaises(deveil_ai.AIOutputError):
                deveil_ai.validate_question_result(bad)

    def test_empty_quotes_only_allowed_for_supplement_and_hold(self):
        thought = "이 코드는 어떤 조건에서 동작하는지 아직 잘 모르겠습니다."
        result = {
            "common": [], "supplement": [{"title":"보충","user_quote":"","ai_view":"설명","reason":"근거"}],
            "unique": [], "error": [],
            "judgment_hold": [{"title":"보류","user_quote":"","reason":"근거 부족","follow_up_question":"값은 무엇인가요?"}]
        }
        cleaned = deveil_ai.validate_comparison_result(result, thought)
        self.assertEqual(cleaned["supplement"][0]["user_quote"], "")
        self.assertEqual(cleaned["judgment_hold"][0]["user_quote"], "")
        for category in ("common", "unique", "error"):
            row_fields = {
                "common": {"title":"공통","user_quote":"","ai_view":"설명","reason":"근거"},
                "unique": {"title":"독창","user_quote":"","reason":"근거"},
                "error": {"title":"오류","user_quote":"","conflict":"충돌","how_to_check":"확인"}
            }[category]
            invalid = dict(result)
            invalid[category] = [row_fields]
            with self.assertRaises(deveil_ai.AIOutputError):
                deveil_ai.validate_comparison_result(invalid, thought)

    def test_retry_cap_is_three_total_attempts(self):
        class Provider:
            def __init__(self): self.calls = 0
            def generate_json(self, *args, **kwargs):
                self.calls += 1
                return {"invalid": True}
        for configured_retries, expected_calls in ((0,1),(2,3),(99,3),(-5,1)):
            provider = Provider()
            service = deveil_ai.DeveilAIService(provider, deveil_ai.AIConfig(max_retries=configured_retries, retry_delay_seconds=0))
            with self.assertRaises(deveil_ai.AIInvalidJSONError):
                service._call_with_retry("prompt", deveil_ai.validate_question_result, 100, deveil_ai.QUESTION_SCHEMA)
            self.assertEqual(provider.calls, expected_calls)

    def test_learning_schema_four_existing_fields(self):
        sample = {"summary":"요약","example_code":"print(1)","observe":"먼저 관찰","change":"그다음 변경"}
        self.assertEqual(set(deveil_ai.validate_learning_result(sample)), {"summary","example_code","observe","change"})

    def test_api_public_response_withholds_private_fields_and_keeps_chat_id(self):
        service = deveil_ai.DeveilAIService(deveil_ai.FakeProvider())
        api.get_service = lambda: service
        client = TestClient(api.app)
        response = client.post("/api/question", json={
            "question":"리스트 인덱스 오류는 왜 발생하나요?", "code":"", "selected_type":"DEBUGGING"
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["chat"]["chat_id"])
        self.assertEqual(set(body["public"]), {"chat_title","chat_summary","choices"})
        serialized = json.dumps(body, ensure_ascii=False)
        self.assertNotIn('"reference_answer"', serialized)
        self.assertNotIn('"guidance"', serialized)
        self.assertIn("session_id", body)
        hint = client.post("/api/hint", json={"session_id": body["session_id"], "level": 1})
        self.assertEqual(hint.status_code, 200, hint.text)
        self.assertEqual(set(hint.json()), {"hint", "level"})
        self.assertNotIn("reference_answer", json.dumps(hint.json()))
        guidance = client.post("/api/guidance", json={"session_id": body["session_id"], "level": 1})
        self.assertEqual(set(guidance.json()), {"look_at", "try_this", "level"})

    def test_r6_template_is_pending_and_has_no_fabricated_samples(self):
        template = json.loads((Path(__file__).resolve().parents[1] / "R6_input_output_samples.json").read_text(encoding="utf-8"))
        self.assertEqual(template["status"], "PENDING_LIVE_COLLECTION")
        self.assertEqual(template["samples"], [])
        self.assertIn("guidance", template["question_generation_expected_internal_fields"])
        self.assertIn("hints", template["question_generation_expected_internal_fields"])
        self.assertIn("reference_answer", template["question_generation_expected_internal_fields"])

    def test_timeout_is_fixed_to_15_seconds(self):
        config = deveil_ai.AIConfig(timeout_seconds=99)
        self.assertEqual(config.timeout_seconds, 15)
        self.assertEqual(deveil_ai.AIConfig(max_retries=99).max_retries, 2)

if __name__ == "__main__":
    unittest.main()
