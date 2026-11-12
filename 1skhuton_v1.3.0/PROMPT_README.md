# Deveil AI 프롬프트 구조 v1.3.0

## 파일
- `question_v1.2.0.txt`: 첫 질문의 사이드바용 제목·요약, 선택지, 관찰 지점과 행동 힌트, 서버 전용 기준 답변 생성
- `comparison_v1.1.0.txt`: 사용자 생각과 기준 답변의 관점 비교
- `learning_v1.1.0.txt`: 초보자용 기초 학습 설명

## 질문 생성 출력
- `chat_title`: 첫 질문을 대화방 제목처럼 요약(최대 50자)
- `chat_summary`: 질문의 핵심 확인 대상을 자연스러운 짧은 구절로 요약(최대 80자)
- `choices`: 사고 방향 선택지 3개
- `guidance`: 두 단계. 각 항목은 `look_at`(간단한 관찰 대상) + `try_this`(구체적인 행동 지침)
- `reference_answer`: 서버 내부 비교 분석용 기준 답변

`guidance`는 한 묶음으로 사용자에게 표시합니다. `look_at`은 어디를 볼지, `try_this`는 그 위치에서 무엇을 직접 해볼지 안내합니다. 두 요소를 별도 기능이나 별도 목록처럼 분리하지 않습니다.

## 코드에서 치환하는 토큰
`{{{{SECURITY_RULE}}}}`, `{{{{SELECTED_TYPE}}}}`, `{{{{QUESTION}}}}`, `{{{{CODE}}}}`, `{{{{QUESTION_SCHEMA}}}}`, `{{{{QUESTION_TYPE}}}}`, `{{{{ORIGINAL_THOUGHT}}}}`, `{{{{REFERENCE_ANSWER}}}}`, `{{{{COMPARISON_SCHEMA}}}}`, `{{{{LEARNING_SCHEMA}}}}`를 임의로 이름 변경하거나 삭제하지 마세요.

## 입력 제한 및 보안
- 질문: 최대 2,000자
- 코드: 최대 6,000자
- 질문 유형: `CONCEPT`, `DEBUGGING`, `PROBLEM_SOLVING`, `DESIGN`
- `[REDACTED]`는 민감정보가 마스킹된 표시이며 원래 값을 추측하거나 복원하지 않습니다.
- 기준 답변과 `guidance`는 프론트에 일괄 전달하지 않고 서버에서 보관합니다.

## R2 2차 요청 확인
- 질문 생성은 `chat_title`, `chat_summary`, `choices` 3개, `guidance` 2개, `reference_answer`만 생성합니다. `hints`, `question_type`, `example_sentence`는 출력하지 않습니다.
- 공개 필드는 제목·요약·선택지이며 `guidance`와 `reference_answer`는 서버 내부 데이터입니다.
- 비교 분석의 `supplement`와 `judgment_hold`는 인용할 사용자 문장이 없으면 `user_quote`를 빈 문자열로 둘 수 있습니다.
- 기초 학습은 기존 네 필드(`summary`, `example_code`, `observe`, `change`)를 유지합니다.
