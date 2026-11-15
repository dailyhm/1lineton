# R6 실측 수집 빠른 실행 안내

## 준비
- Python 3.10 이상 권장
- Render 서비스가 Live이고 Gemini API 키가 Render 환경변수에 설정되어 있어야 합니다.
- API 키를 이 스크립트, JSON, GitHub에 넣지 마세요. 스크립트는 Render API만 호출합니다.

## Windows PowerShell
프로젝트 루트( `api.py` 와 `R6_collection_inputs.json` 이 있는 폴더)에서 실행:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/collect_r6_live_samples.py --base-url https://YOUR-SERVICE.onrender.com --inputs R6_collection_inputs.json --output R6_input_output_samples_LIVE.json --delay 13 --timeout 30
```

PowerShell 실행 정책으로 활성화가 막히면 활성화 단계만 건너뛰고 `python ...` 명령을 실행해도 됩니다.

## 수집 항목
- 질문 생성 2건, 비교 분석 2건, 기초 학습 2건 (실제 Gemini가 처리하는 작업)
- 힌트 1/2·2/2는 `/api/hint` 에서 조회
- 살펴볼 지점/직접 해보기 1/2·2/2는 `/api/guidance` 에서 조회
- hint/guidance 조회는 저장된 결과를 읽는 작업이므로 별도 Gemini 호출 건수로 세지 않습니다.

## 완료 확인
출력 JSON에서 `status` 가 `LIVE_COLLECTION_COMPLETE`인지 확인하고, 각 HTTP 상태가 200인지 검토하세요. 401/403/404/422/5xx 또는 `collector_error`가 있으면 해당 오류를 먼저 해결하세요. 수집 결과에는 사용자 입력 예시와 모델 응답이 포함될 수 있으므로 공개 저장소에 올리지 말고 내부 검수용으로 보관하세요.

`--timeout 30`은 수집기 클라이언트 대기시간입니다. 서버의 AI 처리 제한시간을 변경하지 않습니다.
