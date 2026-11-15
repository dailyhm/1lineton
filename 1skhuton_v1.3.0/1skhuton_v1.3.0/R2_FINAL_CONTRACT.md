# R2 최종 출력 계약 (백엔드 B 2차 요청 기준)

## 1. 질문 생성

LLM 내부 출력은 다음 필드만 포함한다.

- `chat_title`: 문자열, 최대 50자
- `chat_summary`: 문자열, 최대 80자
- `choices`: 비어 있지 않은 문자열 정확히 3개
- `hints`: 문자열 정확히 2개. Figma의 힌트 탭에서 단계별로 별도 제공한다.
- `guidance`: 객체 정확히 2개. 각 객체는 `look_at`, `try_this` 문자열만 포함
- `reference_answer`: 비어 있지 않은 문자열

`question_type`, `example_sentence`는 출력에 포함하지 않는다. `hints`는 `guidance`와 독립된 2개 문자열 배열이다. 질문 유형은 `selected_type` 입력으로 받는다. 공개 응답에는 `chat_title`, `chat_summary`, `choices`만 전달한다. `guidance`와 `reference_answer`는 서버 내부 저장 데이터다.

## 2. 비교 분석

최상위 필드는 배열 5개다: `common`, `supplement`, `unique`, `error`, `judgment_hold`.

| 분류 | 필수 항목 필드 |
|---|---|
| common | `title`, `user_quote`, `ai_view`, `reason` |
| supplement | `title`, `user_quote`, `ai_view`, `reason` |
| unique | `title`, `user_quote`, `reason` |
| error | `title`, `user_quote`, `conflict`, `how_to_check` |
| judgment_hold | `title`, `user_quote`, `reason`, `follow_up_question` |

모든 항목에 `title`이 필요하다. `supplement`와 `judgment_hold`는 실제 인용이 없으면 `user_quote: ""`를 허용한다. 나머지 분류는 원문에 실제 존재하는 연속 문자열을 인용해야 한다. 허위 인용 항목은 제외하며 사용자 생각에 근거가 없는 항목은 생성하지 않는다.

## 3. 기초 학습

기존 `LEARNING_SCHEMA`를 유지한다. 출력 필드는 `summary`, `example_code`, `observe`, `change`다. UI 표시 의미는 각각 **핵심 요약**, **예시 코드**, **먼저 관찰해요**, **그다음 바꿔요**다. 프로젝트에 실제 10개 Figma 화면별 필드 매핑 정의는 없으므로 새 필드를 임의로 추가하지 않았다. 10개 화면에 이 4개 데이터 영역을 어떻게 배치하는지는 프런트엔드/Figma 담당자가 화면 명세와 대조해야 한다.

## 4. 호출 제한과 API 경계

- 모델 호출 timeout: 호출당 15초
- 자동 형식/스키마 재호출: 최초 1회 + 최대 2회 재시도 = 총 3회
- 백엔드 `analysis_job` 사용자 재시도: 동일 작업에서 최초 시도 포함 총 3회 이내로 별도 카운터 관리. AI 모듈의 자동 재시도와 중복 합산하지 않도록 작업 단위 정책을 백엔드 B가 통합해야 한다.
- 기존 테스트 API 경로(`/api/question`, `/api/hint`, `/api/compare`, `/api/basic-learning`)와 요청 필드(snake_case)는 유지했다.
- 테스트 어댑터가 `chat_id`를 생성해 응답의 `chat.chat_id`에 제공한다. 운영 `chatId` 생성·DB 생명주기는 운영 백엔드 소유이며 이 AI 모듈에서 새 DB 계약을 만들지 않는다.
- 공개 질문 응답에서 `hints`, `guidance`, `reference_answer`는 반환하지 않는다. `/api/hint`는 `hint`와 `level`만 반환하며, `/api/guidance`는 `look_at`, `try_this`, `level`을 별도로 반환한다.

## 5. R6/R7 데이터 출처

R7 세 사례는 수작업 데모 fixture이며 실제 LLM 출력이 아니다. R6 파일은 실제 배포 서버에서 수집하기 전 빈 템플릿이다. 실제 모델 출력이나 비공개 필드는 API 공개 응답을 통해 위조/추출하지 않는다. 비공개 원본이 필요한 실측은 백엔드 내부의 인증된 로그/export 경로를 통해 별도로 수집해야 한다.
