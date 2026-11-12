# 백엔드 B 전달 및 통합 확인 — 2차 요청 반영

## AI 담당 측 전달 파일
- `R7_demo_dataset_v1.3.0.json`
- `R6_input_output_samples.json` (실측 전 빈 템플릿)
- `scripts/collect_r6_live_samples.py`
- `schemas/question_schema.json`
- `schemas/comparison_schema.json`
- `schemas/learning_schema.json`
- `prompts/` 내 프롬프트 3종
- `R2_FINAL_DECISIONS.md`, `R6_R7_DATA_SPEC.md`

## 2차 요청에 대한 AI 측 확정 답변

1. **질문 생성 출력 형식:** 새 프롬프트 형식을 최종으로 사용합니다. `chat_title`, `chat_summary`, `choices` 3개, `guidance` 2개(`look_at` + `try_this`), `reference_answer`입니다. 기존 `hints` 문자열 2개 형식은 사용하지 않습니다.
2. **빈 인용:** `supplement`와 `judgment_hold` 모두 실제 사용자 인용이 없으면 `user_quote: ""`를 허용합니다.
3. **재시도:** 회의 결정대로 최초 호출 포함 총 3회입니다. 자동 형식 재호출은 최초 1회 + 재시도 최대 2회이며, 4회 정책은 적용하지 않습니다.

## 백엔드 B 통합 작업
- 위 스키마/프롬프트를 실제 서버의 R2 계약과 일치시킵니다.
- `analysis_job`의 최대 시도 횟수를 최초 호출 포함 3회로 제한합니다.
- `/api/question` 공개 응답에는 기존 보안 경계를 유지하고 `guidance`, `reference_answer`를 노출하지 않습니다.
- R6 전체 질문 생성 원본이 필요하면 테스트 환경 전용 내부 로그/export로 `guidance`와 `reference_answer`를 수집합니다. 공개 API에 추가하지 않습니다.
- R6 수집 스크립트의 요청 필드/세션 연결이 실제 배포 API 계약과 일치하는지 통합 테스트합니다.
- R7 JSON 3개 시나리오를 스키마 검증하고 DB seed 또는 fallback 저장소에 연결합니다.

## R6 상태에 대한 주의
`R6_input_output_samples.json`은 현재 실측 전 템플릿입니다. 이 환경에서는 실제 백엔드 URL/실행 권한/모델 응답에 접근할 수 없으므로 실제 LLM 결과를 임의로 만들어 채우지 않았습니다. 백엔드 배포 후 수집 스크립트로 실측 결과를 채워야 합니다.

## 내부 R6 실측 수집 스크립트
- 공개 응답만 수집할 때는 `scripts/collect_r6_live_samples.py`를 사용합니다.
- `guidance`와 `reference_answer`를 포함한 전체 질문 생성 결과가 필요하면 `GEMINI_API_KEY`가 서버 환경변수로 설정된 신뢰 가능한 백엔드 환경에서 `scripts/collect_r6_internal_samples.py`를 실행합니다.
- 내부 수집 파일에는 비공개 기준 답변과 안내가 포함되므로 접근을 제한하고 공개 API/프론트엔드에 전달하지 않습니다.
