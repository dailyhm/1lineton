# CHANGELOG_R2

## 백엔드 B 2차 요청 반영

### 수정 및 추가 파일
- `question_schema.json`: R2 질문 출력 필드와 choices 3개, guidance 2개 제약 반영.
- `comparison_schema.json`: 5개 분류 및 필드 구조 유지, supplement/judgment_hold의 빈 인용 허용을 스키마에 명시.
- `learning_schema.json`: 기존 summary/example_code/observe/change 필드 유지.
- `prompts/question_v1.2.0.txt`: hints 금지, guidance 정확히 2개, 비공개 필드 경계 명확화.
- `prompts/comparison_v1.1.0.txt`: 빈 인용 허용 두 분류를 명시.
- `prompts/learning_v1.1.0.txt`: 기존 네 필드의 UI 의미를 명시하고 임의의 화면별 키 추가 금지.
- `deveil_ai.py`: 재시도 최소값 3회 강제 버그 제거. 재시도 0~2회, 총 호출 최대 3회로 제한. 모델 timeout 15초 고정.
- `render.yaml`: `DEVEIL_AI_MAX_RETRIES`를 3에서 2로 변경.
- `R6_input_output_samples.json`, `R6_collection_inputs.json`, `scripts/collect_r6_live_samples.py`: 백엔드 B 전달 패키지의 R6 템플릿과 수집 스크립트 편입.
- `R7_demo_dataset_v1.3.0.json`: R7 3개 수작업 fixture 편입.
- `evaluations/validate_r7_dataset.py`: R7 데이터 계약 검증기 추가.
- `R2_FINAL_CONTRACT.md`: 최종 계약 문서 추가.
- `TEST_REPORT.md`: 실제 실행 테스트 결과 기록.

### 기존 구조/계약 보존
- FastAPI 엔드포인트 및 snake_case 요청 필드 유지.
- 테스트 API의 `chat_id` 발급/응답 구조 유지.
- 운영 DB의 `chatId` 생명주기는 AI 모듈이 소유하지 않는 기존 경계 유지.
- 질문 생성 공개/비공개 데이터 분리 유지.
- 기존 기초 학습 JSON 필드와 비교 분석 필드 유지.

### 확인된 문제
- `deveil_ai.py`의 `MIN_RETRIES = 3` 및 `max(MIN_RETRIES, config.max_retries)` 조합은 설정값이 0~2여도 최소 3회 재시도를 강제하여 총 4회 호출될 수 있었다. 최소값을 0으로 바꾸고 실제 루프에서 재시도 횟수를 0~2로 재제한했다.
- `render.yaml`은 `DEVEIL_AI_MAX_RETRIES=3`으로 설정되어 문서/요청과 불일치했다. 2로 수정했다.
- R6 템플릿은 실제 실측 데이터가 아닌 빈 템플릿이었다. 실측값을 임의 생성하지 않고 상태를 그대로 보존했다.
- R6 공개 API 수집 스크립트는 question API의 공개 필드만 저장한다. 비공개 `guidance`/`reference_answer`는 공개 API에서 수집할 수 없으며 백엔드 내부 인증 export 연동이 추가로 필요하다.

### 변경하지 않은 핵심 파일
- `api.py`: 기존 네 엔드포인트와 snake_case 요청 계약, `chat.chat_id`/`session_id` 응답 구조, 공개/비공개 분리 동작이 이미 현재 계약과 부합하여 코드 변경하지 않음.
- `learning_schema.json`: 기존 네 필드 구조가 R2 요구사항과 이미 일치하여 파일 내용 변경하지 않음.
