# Deveil AI 비교 분석 평가 가이드 v1.1.0

## 목적
사용자의 생각과 AI 기준 답변을 비교한다. 이해도나 노력을 점수화하지 않는다.

## 평가 사례
- TC01: 정확한 설명
- TC02: 부분 이해 및 경계 조건
- TC03: 명확한 오개념
- TC04: 독창적이고 타당한 대안
- TC05: 맥락 부족에 따른 판단 보류
- TC06: 원문 인용 무결성

## 새 출력 구조
최상위 다섯 필드는 모두 배열이다.
- `common`: `title`, `user_quote`, `ai_view`, `reason`
- `supplement`: `title`, `user_quote`, `ai_view`, `reason`
- `unique`: `title`, `user_quote`, `reason`
- `error`: `title`, `user_quote`, `conflict`, `how_to_check`
- `judgment_hold`: `title`, `user_quote`, `reason`, `follow_up_question`

각 항목은 `title`을 포함한다. 해당 분류가 없으면 빈 배열이다.
`supplement`와 `judgment_hold`는 직접 인용할 사용자 발언이 없을 때 `user_quote`를 빈 문자열로 둘 수 있다. 그 외 분류는 실제 원문을 인용해야 한다.

## 실행
```bash
python evaluations/validate_dataset.py
python evaluations/validate_dataset.py --case TC01 --result path/to/result.json
```

자동 검증은 JSON 구조, 필수 필드, 문자열 자료형, 제목, 원문 인용을 검사한다. 런타임에서 잘못된 인용이 발견된 항목은 R5 정책에 따라 해당 항목만 제외한다.

## 의미 평가 기준
- `common`: 실제로 의미가 일치하는 핵심만 분류한다.
- `supplement`: 기준 답변에 근거한 사실적으로 정확한 추가 정보만 제공한다.
- `unique`: 기준 답변과 달라도 질문 조건에 맞는 타당한 관점은 보존한다.
- `error`: 명확하게 사실과 충돌하는 주장만 분류한다.
- `judgment_hold`: 근거가 부족하거나 질문이 모호하면 오류로 단정하지 않고 추가 질문을 제시한다.
- 기준 답변 자체가 불완전하거나 잘못되었을 가능성도 고려한다.
- 사용자의 실력, 노력, 이해도를 점수화하지 않는다.

자동 스크립트는 구조와 인용만 검사하며 의미적 정확성 및 보충 정보의 사실성은 평가자가 `pass_criteria`를 바탕으로 별도 확인해야 한다.
