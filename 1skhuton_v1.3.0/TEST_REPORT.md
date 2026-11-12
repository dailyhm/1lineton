# TEST_REPORT — Deveil AI v1.3.0 / R2

실행일: 2026-11-12 (실행 환경 기준)

## 실행 결과

| 항목 | 결과 | 근거 |
|---|---|---|
| Python 문법 검사 | PASS | `py_compile` 대상 7개 Python 파일 |
| 내장 FakeProvider 자체 테스트 | PASS | `python deveil_ai.py --self-test` |
| R2/API 단위 테스트 | PASS | `python -m unittest discover -s tests -v` — 7 tests |
| 기존 비교 평가 데이터 | PASS | `evaluations/validate_dataset.py` — 6 cases |
| R7 데모 데이터 | PASS | `evaluations/validate_r7_dataset.py` — 3 cases |
| JSON 파싱 | PASS | 프로젝트 JSON 7개 모두 파싱 성공 |
| question choices/guidance 개수 | PASS | 정확히 3개 / 2개 검사 |
| 빈 user_quote 허용 | PASS | supplement, judgment_hold만 빈 문자열 허용 |
| 자동 재시도 총 횟수 | PASS | retry 설정 0, 2, 99, -5를 검사해 실제 호출 1, 3, 3, 1회 확인 |
| 공개 응답 비공개 경계 | PASS | FastAPI TestClient + FakeProvider로 question/hint 응답 확인 |
| learning 기존 필드 | PASS | summary/example_code/observe/change 네 필드 검증 |
| R6/R7 JSON 호환성 | PARTIAL | R7 전체 스키마 검증 PASS. R6 템플릿 구조/상태 확인, 실제 응답 미수집 |

## 자동화 테스트에서 확인한 세부 사항

- 질문 생성 출력에 `hints`, `question_type`, `example_sentence`가 섞이면 검증 실패.
- `choices` 3개, `guidance` 2개 및 각 guidance의 `look_at`, `try_this`를 검사.
- 공개 `/api/question` 응답에는 `guidance` 배열과 `reference_answer`가 포함되지 않음.
- 기존 `/api/hint`는 API 호환성을 유지하며 요청된 한 단계만 `look_at`, `try_this`, `level`로 반환. 전체 guidance 배열과 기준 답변은 반환하지 않음.
- 비교 분석에서 `supplement`, `judgment_hold`는 빈 인용 허용. 나머지 세 분류는 비어 있거나 원문에 없는 인용이면 항목 검증에서 실패/제외.
- 재시도 횟수는 어떤 설정값에서도 총 3회 초과하지 않음.
- 기존 `chat.chat_id` 및 임시 `session_id` 응답 흐름을 TestClient로 확인.

## 미실행 / 외부 의존 테스트

1. **실제 Gemini LLM 호출:** 미실행. 배포 서버와 `GEMINI_API_KEY` 접근 권한이 제공되지 않았으므로 모델 응답 품질/실제 지연을 검증하지 않음.
2. **R6 실측 수집:** 미실행. `R6_input_output_samples.json`은 `PENDING_LIVE_COLLECTION` 상태의 빈 템플릿이다. 실측 결과를 임의 생성하지 않음.
3. **R6 내부 수집 스크립트 실행:** 미실행. 스크립트 문법 검사만 수행했으며 실제 Gemini API 키/서버 환경에서 private 포함 수집은 수행하지 않음.
4. **운영 DB 및 `analysis_job` 통합:** 미실행. 원본 프로젝트는 DB/운영 job 저장소를 포함하지 않는 AI 모듈 및 Render 테스트 어댑터임.
5. **운영 사용자 재시도 버튼:** 미실행. 원본 프로젝트에 `analysis_job` 사용자 재시도 API/버튼 구현이 없음. 백엔드 B가 job 단위 최초 시도 포함 3회 제한을 구현해야 함.
6. **Figma 10개 화면 시각 검수:** 미실행. 원본 프로젝트에 Figma 파일/화면별 매핑 명세가 포함되어 있지 않음. 기존 `LEARNING_SCHEMA` 4개 데이터 필드는 보존하고 화면 의미를 프롬프트에 명시함.

## 실행 환경 참고

일부 Python 프로세스 시작 시 호스트 환경의 spreadsheet warmup 모듈이 stderr에 별도 경고를 출력했으나, 위 명령은 모두 exit code 0으로 종료했다. 해당 경고는 프로젝트 테스트 코드의 실패가 아니다.

## 결론

로컬 정적 검사, R2 계약 단위 검사, 기존 평가 데이터 및 R7 fixture 검증은 통과했다. 실제 Gemini 호출, R6 실측, 운영 DB/job 재시도 통합 및 Figma 10개 화면 검수는 백엔드/디자인 환경이 필요하므로 미완료다.
