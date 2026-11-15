# Deveil AI R6/R7 전달 패키지 명세 — 2차 요청 반영본

## 패키지 구성과 용도

| 파일 | 용도 / 상태 |
|---|---|
| `R7_demo_dataset_v1.3.0.json` | 시연용 데모 데이터 3건. AI 담당자가 작성한 fixture이며 실제 모델 출력이 아님 |
| `R6_input_output_samples.json` | 실측 결과를 담을 JSON 템플릿. 현재 `PENDING_LIVE_COLLECTION` |
| `scripts/collect_r6_live_samples.py` | 배포된 백엔드 API를 호출해 공개 응답을 수집하는 스크립트 |
| `scripts/collect_r6_internal_samples.py` | 신뢰할 수 있는 서버 환경에서 내부 private 데이터까지 별도 수집하는 스크립트 |
| `inputs/R6_collection_inputs.json` | R6 수집용 입력 시나리오 2건 |
| `schemas/` | 질문 생성·비교 분석·기초 학습 출력 스키마 |
| `prompts/` | 질문 생성·비교 분석·기초 학습 프롬프트 |
| `R2_FINAL_DECISIONS.md` | 2차 요청에 따른 출력/빈 인용/재시도 최종 결정 |
| `BACKEND_ACTION_REQUIRED.md` | 백엔드 B 통합 시 확인할 사항 |

## R2 최종 결정

1. 질문 생성의 LLM 내부 출력: `chat_title`, `chat_summary`, `choices`, `guidance`, `reference_answer`.
2. `guidance`는 정확히 2개이며 각 객체에 `look_at`, `try_this`를 포함합니다. `hints` 문자열 배열은 사용하지 않습니다.
3. `supplement`와 `judgment_hold`의 `user_quote`는 실제 인용이 없으면 `""` 허용입니다.
4. 자동 형식 재호출 및 사용자 재시도는 최초 호출 포함 최대 3회입니다. 즉 최초 1회 + 재시도 최대 2회입니다.

자세한 계약은 `R2_FINAL_DECISIONS.md`를 기준으로 합니다.

## R6 실제 샘플 수집

1. 백엔드 B가 서비스를 실행/배포하고 LLM 제공자 키를 서버 환경변수로 설정합니다. API 키를 수집 스크립트나 JSON에 넣지 않습니다.
2. `inputs/R6_collection_inputs.json`의 DEBUGGING/CONCEPT 시나리오를 사용합니다.
3. 아래처럼 실행합니다.

```bash
python scripts/collect_r6_live_samples.py \
  --base-url https://<백엔드-주소> \
  --inputs inputs/R6_collection_inputs.json \
  --output R6_input_output_samples.json \
  --delay 13 \
  --timeout 15
```

4. 기본 13초 간격은 무료 등급 분당 5회 제한을 고려한 값입니다. 실제 호출 제한 정책은 사용 중인 제공자/키 등급에서 다시 확인합니다.
5. 스크립트는 `/api/question`, `/api/compare`, `/api/basic-learning` 결과와 `/api/hint` 1·2단계 조회 결과를 수집합니다. 힌트 조회는 저장된 guidance 조회이며 별도 LLM 호출이 아닙니다.
6. 성공 샘플 목표는 질문 생성 2건, 비교 분석 2건, 기초 학습 2건입니다. 실패 응답도 HTTP 상태와 함께 기록해 원인 분석에 활용합니다.

### R6 질문 생성의 비공개 필드 제한

현재 `/api/question`은 공개 필드만 반환하고 `guidance`, `reference_answer`를 제외합니다. 따라서 이 스크립트만으로 LLM이 생성한 전체 원본 JSON을 확보할 수 없습니다. R6에서 전체 모델 출력이 필요하면 신뢰할 수 있는 서버 환경에서 `scripts/collect_r6_internal_samples.py`를 실행합니다. 이 스크립트는 `prepare_question()`의 private 결과를 별도 내부 QA 파일에 저장합니다. 해당 파일은 제한 저장소에 보관하고 `guidance`와 `reference_answer`를 공개 API에 노출해서는 안 됩니다.

## R7 데모 데이터

`R7_demo_dataset_v1.3.0.json`에는 DEBUGGING, CONCEPT, PROBLEM_SOLVING 세 사례가 있습니다. 각 사례는 입력, 질문 생성 공개/비공개 데이터, 힌트, 사용자 최초 생각, 비교 분석, 기초 학습 결과를 포함합니다.

- 백엔드는 R7 데이터를 DB seed 또는 데모 fallback 저장소로 적재할 수 있습니다.
- `private.guidance`와 `private.reference_answer`는 프론트에 공개하지 않습니다.
- 본 데이터는 수기 fixture이므로 백엔드가 스키마와 화면 연결을 검수한 뒤 시연 데이터로 승인해야 합니다.

## 재시도 정책

`analysis_job`당 최초 호출을 포함해 최대 3회입니다. 4회(최초 1회 + 재시도 3회)로 구현하지 않습니다. 사용자 재시도 버튼도 동일한 총 3회 제한을 넘지 않도록 서버에서 통제합니다.

## 보안 및 검수

- API 키/토큰은 서버 환경변수에만 보관합니다.
- `[REDACTED]`는 마스킹 자리표시자이며 원래 값을 추측하지 않습니다.
- R6/R7 JSON의 파싱 및 JSON Schema 검증을 수행합니다.
- 사용자 식별자, 세션 쿠키, 비밀값을 샘플에 저장하지 않습니다.
- R6 실측본과 R7 수기 fixture를 명확히 구분합니다.
