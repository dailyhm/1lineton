# Prompt changelog

## v1.2.0 — 2026-11-09
- 첫 질문에서 사이드바에 사용할 `chat_title`과 `chat_summary` 생성 추가.
- 질문 생성 힌트 구조를 `hints`에서 `guidance`로 통합.
- `guidance` 한 항목에 `look_at`(짧은 관찰 지점)과 `try_this`(구체적인 행동 안내)를 함께 포함.
- 공개 데이터는 제목·요약·선택지만 포함하고, 안내와 기준 답변은 서버 내부에 보관.
- 질문 유형 4개(CONCEPT / DEBUGGING / PROBLEM_SOLVING / DESIGN)만 허용.
- 재시도 정책을 최초 호출 포함 최대 3회에서 최초 호출 후 최대 2회 재시도(총 3회)로 변경.
- 질문 최대 2,000자, 코드 최대 6,000자 제한 유지.

## v1.1.0 — 2026-11-09
- 비교 분석의 모든 항목에 title 추가.
- judgment_hold를 단일 객체에서 배열로 변경.
- 기초 학습 출력 4개 필드(summary, example_code, observe, change)로 변경.
- [REDACTED] 의미를 보안 규칙에 명시.
- Gemini JSON mode 및 response schema 적용.
- 호출당 15초 제한, 잘못된 user_quote 항목만 제외하도록 변경.

## R2 2차 요청 정합성 — 2026-11-12
- 질문 생성 스키마에서 choices 3개, guidance 2개를 명시하고 hints 출력 금지 및 비공개 경계를 강화.
- 비교 프롬프트에서 supplement와 judgment_hold의 빈 user_quote 허용을 명시.
- 기초 학습의 기존 네 필드와 네 가지 화면 표시 의미를 보강. 10개 화면별 새 키는 추가하지 않음.
