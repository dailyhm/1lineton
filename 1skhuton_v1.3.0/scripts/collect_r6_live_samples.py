#!/usr/bin/env python3
"""
Collect REAL R6 request/response samples by calling the Deveil v1.3.0 backend.

It uses the existing endpoints:
  POST /api/question
  POST /api/hint (levels 1 and 2; deterministic server-side retrieval)
  POST /api/compare
  POST /api/basic-learning

No Gemini key is read or sent by this script. Configure the provider key only
on the backend server. Calls are paced to reduce rate-limit pressure.
"""
from __future__ import annotations
import argparse, json, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

def post_json(base_url: str, path: str, payload: dict, timeout: int = 15):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=data,
        headers={"Content-Type":"application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try: body = json.loads(raw)
        except Exception: body = {"raw":raw}
        return e.code, body
    except Exception as e:
        return 0, {"collector_error":str(e)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True, help="예: https://your-service.onrender.com")
    ap.add_argument("--inputs", default="inputs/R6_collection_inputs.json")
    ap.add_argument("--output", default="R6_input_output_samples.json")
    ap.add_argument("--delay", type=float, default=13.0, help="LLM endpoint 사이 대기 초. 무료 분당 한도 고려")
    ap.add_argument("--timeout", type=int, default=15)
    args = ap.parse_args()

    cfg = json.loads(Path(args.inputs).read_text(encoding="utf-8"))
    samples = []
    last_llm_call = 0.0

    def paced_post(path, payload, is_llm=True):
        nonlocal last_llm_call
        if is_llm:
            wait = args.delay - (time.monotonic() - last_llm_call)
            if last_llm_call and wait > 0:
                time.sleep(wait)
        status, body = post_json(args.base_url, path, payload, args.timeout)
        if is_llm:
            last_llm_call = time.monotonic()
        return status, body

    for sc in cfg["scenarios"]:
        group = sc["sample_group"]
        question_payload = {
            "question":sc["question"],
            "code":sc.get("code",""),
            "selected_type":sc["question_type"]
        }
        q_status, q_body = paced_post("/api/question", question_payload, True)
        samples.append({
            "sample_id":group+"-QUESTION",
            "task":"question_generation",
            "request":question_payload,
            "http_status":q_status,
            "response":q_body,
            "collected_at":datetime.now(timezone.utc).isoformat(),
            "is_live_model_output": q_status == 200
        })
        if q_status != 200 or not isinstance(q_body,dict) or "session_id" not in q_body:
            print(f"[실패] {group} 질문 생성: HTTP {q_status}; 비교 분석은 건너뜁니다.")
        else:
            session_id = q_body["session_id"]
            for level in (1,2):
                hint_payload={"session_id":session_id,"level":level}
                h_status,h_body=post_json(args.base_url,"/api/hint",hint_payload,args.timeout)
                samples.append({
                    "sample_id":group+f"-HINT-{level}",
                    "task":"hint_retrieval",
                    "request":{"level":level,"session_context_sample":group},
                    "http_status":h_status,
                    "response":h_body,
                    "collected_at":datetime.now(timezone.utc).isoformat(),
                    "is_live_model_output":False,
                    "note":"서버에 저장된 guidance를 조회한 결과이며 별도 LLM 호출이 아닙니다."
                })
            compare_payload={
                "session_id":session_id,
                "original_thought":sc["original_thought"]
            }
            c_status,c_body=paced_post("/api/compare",compare_payload,True)
            samples.append({
                "sample_id":group+"-COMPARE",
                "task":"comparison",
                "request":{
                    "question":sc["question"],"code":sc.get("code",""),
                    "question_type":sc["question_type"],
                    "original_thought":sc["original_thought"],
                    "session_id":"[EPHEMERAL_SESSION_ID]"
                },
                "http_status":c_status,
                "response":c_body,
                "collected_at":datetime.now(timezone.utc).isoformat(),
                "is_live_model_output":c_status == 200
            })

        learning_payload={
            "question":sc["question"],
            "code":sc.get("code",""),
            "question_type":sc["question_type"]
        }
        l_status,l_body=paced_post("/api/basic-learning",learning_payload,True)
        samples.append({
            "sample_id":group+"-LEARNING",
            "task":"basic_learning",
            "request":learning_payload,
            "http_status":l_status,
            "response":l_body,
            "collected_at":datetime.now(timezone.utc).isoformat(),
            "is_live_model_output":l_status == 200
        })
        print(f"[완료] {group}: question={q_status}, learning={l_status}")

    # Count only successful live model task outputs; hints are not model calls.
    counts = {}
    for s in samples:
        if s.get("is_live_model_output"):
            counts[s["task"]] = counts.get(s["task"],0)+1
    result={
        "dataset_name":"Deveil R6 Input Output Samples",
        "version":"1.0.0",
        "status":"LIVE_COLLECTION_COMPLETE" if all(counts.get(k,0)>=2 for k in ("question_generation","comparison","basic_learning")) else "PARTIAL_OR_FAILED_COLLECTION",
        "source":"Collected from deployed Deveil backend endpoints",
        "backend_base_url":args.base_url,
        "created_at":datetime.now(timezone.utc).isoformat(),
        "successful_live_sample_counts":counts,
        "samples":samples,
        "review_required":True,
        "review_notes":[
            "HTTP 200 여부와 응답 JSON 스키마를 검토하세요.",
            "질문 생성 응답에는 공개 필드만 포함됩니다. reference_answer와 guidance는 서버 내부 private 데이터입니다.",
            "세션 ID, 개인정보, 비밀값이 응답이나 로그에 노출되지 않았는지 확인하세요.",
            "비교 분석은 question 생성 시 발급된 임시 session_id를 사용하므로 재현용으로는 원 질문/코드/유형/사용자 생각을 함께 보관합니다."
        ]
    }
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("저장:",args.output)
    print("실제 모델 출력 건수:",counts)
    if result["status"] != "LIVE_COLLECTION_COMPLETE":
        print("주의: 각 작업별 실제 성공 샘플이 2개 이상이 아닙니다. 실패한 호출은 수정 후 재수집하세요.")

if __name__=="__main__":
    main()
