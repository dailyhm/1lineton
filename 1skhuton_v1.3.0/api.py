"""Deveil AI API. The reference answer is retained server-side, never returned."""
from __future__ import annotations

import logging
import os
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from deveil_ai import AIConfig, AITimeoutError, AIInvalidJSONError, DeveilAIError, DeveilAIService, GeminiProvider

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
SESSION_TTL_SECONDS = max(60, int(os.getenv("DEVEIL_SESSION_TTL_SECONDS", "1800")))
SESSIONS: dict[str, dict] = {}
logger = logging.getLogger("deveil.api")

app = FastAPI(
    title="Deveil AI API",
    version="1.3.0",
    description=(
        "Deveil AI 테스트 어댑터. 새 질문마다 새 chat_id를 만들고, 사이드바용 제목·요약을 반환합니다. "
        "기준 답변과 행동 안내는 서버 내부에 보관합니다. API 상세 명세는 /docs에서 확인하세요."
    ),
)

cors_origins = [x.strip() for x in os.getenv("DEVEIL_CORS_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    code: str = Field(default="")
    selected_type: str = Field(default="DEBUGGING", pattern="^(CONCEPT|DEBUGGING|PROBLEM_SOLVING|DESIGN)$")

    @field_validator("question")
    @classmethod
    def validate_question_length(cls, value: str) -> str:
        value = value.strip()
        if not value or len(value) > 2000:
            raise ValueError("질문은 앞뒤 공백 제외 1~2,000자여야 합니다.")
        return value

    @field_validator("code")
    @classmethod
    def validate_code_length(cls, value: str) -> str:
        if len(value.strip()) > 6000:
            raise ValueError("코드는 앞뒤 공백 제외 최대 6,000자까지 입력할 수 있습니다.")
        return value


class HintRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    level: int = Field(ge=1, le=2)


class CompareRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    original_thought: str = Field(min_length=30, max_length=4000)


class LearningRequest(BaseModel):
    question: str = Field(min_length=1)
    code: str = Field(default="")
    question_type: str = Field(default="CONCEPT", pattern="^(CONCEPT|DEBUGGING|PROBLEM_SOLVING|DESIGN)$")

    @field_validator("question")
    @classmethod
    def validate_question_length(cls, value: str) -> str:
        value = value.strip()
        if not value or len(value) > 2000:
            raise ValueError("질문은 앞뒤 공백 제외 1~2,000자여야 합니다.")
        return value

    @field_validator("code")
    @classmethod
    def validate_code_length(cls, value: str) -> str:
        if len(value.strip()) > 6000:
            raise ValueError("코드는 앞뒤 공백 제외 최대 6,000자까지 입력할 수 있습니다.")
        return value



def get_service() -> DeveilAIService:
    if not os.getenv("GEMINI_API_KEY", "").strip():
        raise HTTPException(status_code=503, detail="서버에 GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    try:
        return DeveilAIService(GeminiProvider(AIConfig()))
    except Exception as exc:
        logger.exception("Failed to initialize Gemini provider")
        raise HTTPException(status_code=503, detail="AI 제공자를 초기화하지 못했습니다. 서버 환경변수를 확인하세요.") from exc


def cleanup_sessions() -> None:
    cutoff = time.time() - SESSION_TTL_SECONDS
    expired_ids = [sid for sid, data in SESSIONS.items() if data["created_at"] < cutoff]
    for sid in expired_ids:
        SESSIONS.pop(sid, None)


def get_session(session_id: str) -> dict:
    cleanup_sessions()
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션이 만료되었거나 서버가 재시작되었습니다. 새 채팅을 시작해 주세요.")
    return session


@app.get("/", include_in_schema=False)
def playground():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "deveil-ai", "version": "1.3.0"}


@app.post("/api/question", tags=["Deveil"])
def create_question(payload: QuestionRequest):
    service = get_service()
    try:
        prepared = service.prepare_question(payload.question, payload.code, payload.selected_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AITimeoutError as exc:
        raise HTTPException(status_code=504, detail={"code": "AI_TIMEOUT", "message": str(exc)}) from exc
    except AIInvalidJSONError as exc:
        raise HTTPException(status_code=502, detail={"code": "AI_INVALID_JSON", "message": str(exc)}) from exc
    except DeveilAIError as exc:
        raise HTTPException(status_code=502, detail={"code": "AI_API_ERROR", "message": str(exc)}) from exc
    except Exception as exc:
        logger.exception("Question preparation failed")
        raise HTTPException(status_code=502, detail="질문 생성에 실패했습니다. 입력을 확인하거나 잠시 후 다시 시도해 주세요.") from exc

    # 질문 생성은 항상 새 대화방을 시작합니다. chat_id는 UI/백엔드 연결용이며,
    # session_id는 Render 테스트 어댑터의 임시 서버 세션 식별자입니다.
    chat_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "created_at": time.time(),
        "chat_id": chat_id,
        "question": payload.question,
        "code": payload.code,
        "question_type": payload.selected_type,
        "private": prepared["private"],  # Includes reference_answer; never serialize this object.
        "compared": False,
    }
    # Deliberately return only public data. Do not return prepared["private"].
    return {
        "chat": {
            "chat_id": chat_id,
            "title": prepared["public"]["chat_title"],
            "summary": prepared["public"]["chat_summary"],
            "is_new": True,
        },
        "session_id": session_id,
        "public": prepared["public"],
        "security": prepared["security"],
        "expires_in_seconds": SESSION_TTL_SECONDS,
    }


@app.post("/api/hint", tags=["Deveil"])
def reveal_hint(payload: HintRequest):
    session = get_session(payload.session_id)
    if payload.level not in (1, 2):
        raise HTTPException(status_code=422, detail="안내 단계는 1 또는 2만 가능합니다.")
    # 기존 /api/hint 경로는 유지하되 실제 반환값은 살펴볼 지점과 행동 힌트의 한 묶음입니다.
    guidance = session["private"].get("guidance", [])
    if len(guidance) != 2:
        raise HTTPException(status_code=500, detail="저장된 안내 데이터가 올바르지 않습니다.")
    item = guidance[payload.level - 1]
    return {"look_at": item["look_at"], "try_this": item["try_this"], "level": str(payload.level)}


@app.post("/api/compare", tags=["Deveil"])
def compare(payload: CompareRequest):
    session = get_session(payload.session_id)
    if session["compared"]:
        raise HTTPException(status_code=409, detail="이미 비교 분석을 완료한 대화입니다. 새 채팅을 시작해 주세요.")
    try:
        result = get_service().compare(
            question=session["question"],
            code=session["code"],
            question_type=session["question_type"],
            original_thought=payload.original_thought,
            reference_answer=session["private"]["reference_answer"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AITimeoutError as exc:
        raise HTTPException(status_code=504, detail={"code": "AI_TIMEOUT", "message": str(exc)}) from exc
    except AIInvalidJSONError as exc:
        raise HTTPException(status_code=502, detail={"code": "AI_INVALID_JSON", "message": str(exc)}) from exc
    except DeveilAIError as exc:
        raise HTTPException(status_code=502, detail={"code": "AI_API_ERROR", "message": str(exc)}) from exc
    except Exception as exc:
        logger.exception("Comparison failed")
        raise HTTPException(status_code=502, detail="비교 분석에 실패했습니다. 잠시 후 다시 시도해 주세요.") from exc
    session["compared"] = True
    # Only the five-field comparison schema is returned; reference_answer is withheld.
    return {"comparison": result}


@app.post("/api/basic-learning", tags=["Deveil"])
def basic_learning(payload: LearningRequest):
    try:
        result = get_service().basic_learning(payload.question, payload.code, payload.question_type)
        return {"learning": result}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AITimeoutError as exc:
        raise HTTPException(status_code=504, detail={"code": "AI_TIMEOUT", "message": str(exc)}) from exc
    except AIInvalidJSONError as exc:
        raise HTTPException(status_code=502, detail={"code": "AI_INVALID_JSON", "message": str(exc)}) from exc
    except DeveilAIError as exc:
        raise HTTPException(status_code=502, detail={"code": "AI_API_ERROR", "message": str(exc)}) from exc
    except Exception as exc:
        logger.exception("Basic learning generation failed")
        raise HTTPException(status_code=502, detail="학습 자료 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.") from exc


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
