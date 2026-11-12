# Deveil AI 모듈 v1.3.0

백엔드 B가 Gemini를 서버 내부에서 직접 호출할 수 있도록 AI 기능을 모듈화한 버전입니다.

## 1. 주요 변경사항

- 질문 입력 최대 2,000자, 코드 입력 최대 6,000자
- 질문 유형 4개: `CONCEPT`, `DEBUGGING`, `PROBLEM_SOLVING`, `DESIGN` (자유 유형 없음)
- 새 대화 첫 질문으로부터 사이드바용 `chat_title`과 `chat_summary` 생성
- 질문 생성: `choices` 3개 + `guidance` 2세트 + `reference_answer` (서버 전용)
- `guidance` 한 세트는 `look_at`(간결한 관찰 대상)과 `try_this`(구체적인 행동 지침)로 구성
- 비교 분석: `common`, `supplement`, `unique`, `error`, `judgment_hold` 모두 배열이며 모든 항목에 `title`
- 기초 학습: `summary`, `example_code`, `observe`, `change`
- Gemini JSON 모드 + response schema + 서버 측 스키마 검증
- 모델 호출당 15초 제한, **최대 재시도 2회** (최초 호출 포함 최대 총 3회)
- 잘못된 `user_quote` 항목만 제외하고 나머지 정상 결과 유지
- `[REDACTED]`를 민감정보 마스킹 표시로 프롬프트에 명시

## 2. 직접 호출 방식

운영 백엔드는 별도 Render `/api/question`, `/api/compare` 서버를 호출하지 않고 이 모듈을 직접 import해서 사용합니다.

```python
from deveil_ai import AIConfig, DeveilAIService, GeminiProvider

ai_service = DeveilAIService(GeminiProvider(AIConfig()))

# 새 채팅의 첫 질문 처리
prepared = ai_service.prepare_question(
    question="트랜잭션은 언제 필요할까요?",
    code="",
    selected_type="DESIGN",
)

# 사이드바에 저장/표시할 메타데이터
chat_title = prepared["public"]["chat_title"]
chat_summary = prepared["public"]["chat_summary"]

# 프론트에 전달 가능한 공개 데이터
choices = prepared["public"]["choices"]

# 서버 DB에만 저장할 비공개 데이터
reference_answer = prepared["private"]["reference_answer"]
guidance = prepared["private"]["guidance"]

# 사용자가 안내 1을 요청했을 때
step_1 = ai_service.get_guidance(prepared["private"], 1)
# 반환: {"look_at": "...", "try_this": "...", "level": "1"}

# 비교 분석
comparison = ai_service.compare(
    question="트랜잭션은 언제 필요할까요?",
    code="",
    question_type="DESIGN",
    original_thought="사용자가 먼저 작성한 생각 30자 이상...",
    reference_answer=reference_answer,
)
```

### 새 채팅 생성 및 사이드바 반영

- 사용자가 새 질문을 시작하면 백엔드는 새 `chatId`와 `chat` DB 레코드를 생성합니다.
- AI 모듈이 반환한 `chat_title`, `chat_summary`를 새 대화의 제목과 미리보기 문구로 저장합니다.
- 예시 표시:
  - 제목: `트랜잭션은 언제 필요할까요?`
  - 요약: `중간 실패와 동시성 조건을 살펴보기`
- 기존 대화를 이어가는 경우에는 기존 `chatId`를 사용하고, 새 채팅 버튼 또는 새 대화 진입으로 첫 질문을 제출할 때만 새로운 `chatId`를 만듭니다.
- AI 모듈은 DB와 `chatId` 생명주기를 직접 관리하지 않습니다. 운영 백엔드가 관리합니다.

백엔드 B는 API 응답 이후 백그라운드 작업으로 AI 함수를 호출하고, `chat` 및 `analysis_job` DB 저장과 2초 간격 상태 조회를 담당합니다. AI 모듈 자체는 비동기 작업 상태나 DB를 관리하지 않습니다.

## 3. 질문 생성 출력 구조

### AI 내부 JSON

```json
{
  "chat_title": "트랜잭션은 언제 필요할까요?",
  "chat_summary": "중간 실패와 동시성 조건을 살펴보기",
  "choices": ["실패 처리", "동시성", "일관성"],
  "guidance": [
    {
      "look_at": "중간 실패가 발생하는 시점",
      "try_this": "작업의 두 번째 단계에서 오류가 발생한다고 가정하고, 앞 단계에서 변경한 데이터가 어떤 상태로 남는지 순서대로 적어 보세요."
    },
    {
      "look_at": "동시에 요청이 들어오는 상황",
      "try_this": "두 사용자가 같은 데이터를 거의 동시에 수정한다고 가정하고, 각 요청이 어떤 순서로 처리될 때 문제가 생기는지 간단한 순서도를 그려 보세요."
    }
  ],
  "reference_answer": "기준 답변"
}
```

### `prepared` 반환

- `prepared["public"]`: `chat_title`, `chat_summary`, `choices` 포함. 프론트 전달 가능.
- `prepared["private"]`: `reference_answer`, `guidance` 포함. 서버 내부에만 보관.
- `prepared["security"]`: 민감정보 마스킹 여부.

`guidance`는 기존 힌트와 살펴볼 지점을 따로 전달하지 않고 묶어서 보여줍니다.

| 필드 | 역할 | 작성 형식 |
|---|---|---|
| `look_at` | 무엇을 살펴볼지 안내 | 짧은 키워드/관찰 대상 |
| `try_this` | 무엇을 직접 해볼지 안내 | 구체적인 행동이 포함된 완전한 문장 |

API 키나 기준 답변이 사용자 응답에 포함되지 않도록 공개/비공개 반환 구조를 유지합니다.

## 4. 질문 유형

| 값 | 화면 표시 | 사고 방향 |
|---|---|---|
| `CONCEPT` | 개념 이해 | 정의, 원리, 적용 조건 |
| `DEBUGGING` | 디버깅 | 재현 조건, 원인 가설, 확인 방법, 수정 영향 |
| `PROBLEM_SOLVING` | 문제 해결 접근 | 요구사항, 접근법, 예외, 검증 방법 |
| `DESIGN` | 설계 판단 | 조건, 대안, 장단점, 선택 근거 |

`FREE` 또는 그 외 유형은 거부합니다.

## 5. 비교 분석과 기초 학습

비교 분석은 `common`, `supplement`, `unique`, `error`, `judgment_hold` 다섯 배열을 반환합니다. 각 항목에는 `title`이 있고, `user_quote`는 사용자 원문에 연속해서 실제 존재하는 문자열이어야 합니다. 원문에 없는 인용은 해당 항목만 제외합니다. 사용자의 이해도나 노력을 점수화하지 않습니다.

기초 학습은 `summary`, `example_code`, `observe`, `change` 네 영역을 반환합니다.

## 6. 모델·재시도 설정

기본값:
- 제공사: Google Gemini
- 모델: `gemini-2.5-flash`
- Temperature: `0.2`
- 최대 출력 토큰: 질문 1800 / 비교 2500 / 학습 1500
- 출력: `application/json` + JSON response schema
- 개별 모델 호출 timeout: 15초 (코드에서 고정)
- 재시도: 최초 호출 실패 후 최대 2회 재시도 (최대 총 3회 호출)

환경변수:
- `GEMINI_API_KEY`
- `DEVEIL_MODEL`
- `DEVEIL_TEMPERATURE`
- `DEVEIL_QUESTION_MAX_OUTPUT_TOKENS`
- `DEVEIL_COMPARISON_MAX_OUTPUT_TOKENS`
- `DEVEIL_LEARNING_MAX_OUTPUT_TOKENS`
- `DEVEIL_AI_TIMEOUT_SECONDS`
- `DEVEIL_AI_MAX_RETRIES` (최초 호출 이후 재시도 횟수, 기본 2 / 최대 2)

모든 시도가 순차 실행되면 호출당 15초 제한과 별개로 전체 대기 시간은 길어질 수 있습니다. 재시도는 JSON/스키마 오류와 일시적인 호출 오류에 적용합니다.

## 7. 로컬 설치 및 테스트

Python 3.10 이상 권장.

```bash
pip install -r requirements.txt
python -m py_compile deveil_ai.py api.py evaluations/validate_dataset.py evaluations/validate_r7_dataset.py scripts/collect_r6_live_samples.py tests/test_r2_contract.py
python deveil_ai.py --self-test
python -m unittest discover -s tests -v
python evaluations/validate_dataset.py
python evaluations/validate_r7_dataset.py
```


## 8. Render 테스트 서버

Render용 FastAPI와 브라우저 테스트 화면은 독립 테스트 어댑터로 유지합니다. 운영 백엔드는 위의 직접 import 방식으로 연결합니다.

- Build: `pip install -r requirements.txt`
- Start: `uvicorn api:app --host 0.0.0.0 --port $PORT`
- Health: `/health`
- Swagger: `/docs`
- Playground: `/`

Render 테스트 어댑터는 `/api/question` 호출마다 새 `chat_id`와 임시 `session_id`를 발급합니다. 세션은 메모리 기반이므로 Render 재시작/인스턴스 변경 시 사라질 수 있으며 운영 DB를 대체하지 않습니다.

운영 백엔드가 `chatId`와 DB 레코드 생명주기를 관리합니다. 이 테스트 어댑터는 요청에서 `chatId`를 받지 않고 `chat.chat_id`를 생성해 반환합니다. 기존 API 요청 필드와 엔드포인트는 유지합니다.


## 9. 데모 접근 및 JSON 스키마

- `DEVEIL_DEMO_TOKEN` 인증은 제거했습니다. 공개 테스트 화면에서 별도 토큰 없이 API를 호출합니다.
- 공개 배포 시 제3자가 Gemini API 사용량을 소모할 수 있으므로 요청 속도 제한, 일일 사용량 한도, CAPTCHA 또는 접근 가능한 IP 제한을 별도로 적용하세요.
- JSON 응답 스키마는 `question_schema.json`, `comparison_schema.json`, `learning_schema.json`으로 분리했습니다. 현재 Python 코드는 호환성을 위해 스키마를 내부 상수로도 유지합니다.

## 10. R2 2차 요청 / R6 / R7

- 최종 필드와 공개·비공개 경계: `R2_FINAL_CONTRACT.md`
- 변경 이력: `CHANGELOG_R2.md`
- 테스트 실행 결과와 미실행 항목: `TEST_REPORT.md`
- R7 수작업 데모: `R7_demo_dataset_v1.3.0.json` (실제 모델 출력이 아님)
- R6 실측 템플릿 및 입력: `R6_input_output_samples.json`, `R6_collection_inputs.json`
- 실제 배포 API 공개 샘플 수집: `python scripts/collect_r6_live_samples.py --base-url https://YOUR_BACKEND`
- 신뢰할 수 있는 서버 내부에서 private 포함 실측 수집: `python scripts/collect_r6_internal_samples.py`
- R7 검증: `python evaluations/validate_r7_dataset.py`

R6 수집 스크립트는 공개 API에서 공개 응답과 비교/학습 결과를 수집합니다. 질문 생성의 비공개 `guidance`와 `reference_answer`는 공개 API 응답에 넣지 않습니다. 해당 내부 출력의 실측 보관은 `scripts/collect_r6_internal_samples.py`를 신뢰할 수 있는 서버 환경에서 실행해 별도 제한 파일로 수집할 수 있습니다. 이 스크립트 출력은 private 데이터를 포함하므로 공개 API나 프론트엔드에 전달하지 마세요. API 키는 수집 클라이언트에 전달하지 않고 배포 서버 환경변수에만 둡니다.

사용자 재시도 버튼은 운영 `analysis_job` 단위에서 최초 실행 포함 최대 3회로 제한해야 합니다. 이 AI 모듈의 JSON 자동 재시도는 호출 1회당 최대 2회 추가이며, 작업 단위 재시도와 중복해서 무제한 실행하지 않도록 백엔드가 단일 attempt 카운터를 적용해야 합니다.
