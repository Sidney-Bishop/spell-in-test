"""FastAPI application entry point for Spell in Test."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.items import get_item, public_view
from app.models import (
    CompletionSummary,
    QuestionView,
    SessionStarted,
    SubmissionResult,
    SubmitRequest,
)
from app.sessions import store
from app.storage import save_session

# Project paths.
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Spell in Test")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# --- Page routes ---

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "Spell in Test"},
    )


# --- API routes ---

@app.post("/api/session", response_model=SessionStarted)
def start_session():
    """Begin a new test session. Returns the session id and total question count."""
    session = store.create()
    return SessionStarted(
        session_id=session.id,
        total_questions=session.total_questions,
    )


@app.get("/api/session/{session_id}/question", response_model=QuestionView)
def get_current_question(session_id: str):
    """Return the next unanswered question for this session."""
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    if session.is_complete:
        raise HTTPException(status_code=409, detail="Session already complete")

    item = get_item(session.next_item_id)
    assert item is not None
    pub = public_view(item)

    return QuestionView(
        item_id=pub["id"],
        sentence=pub["sentence"],
        first_letter=pub["first_letter"],
        question_number=session.current_index + 1,
        total_questions=session.total_questions,
    )


@app.post("/api/submit", response_model=SubmissionResult)
def submit_answer(body: SubmitRequest):
    """Score a submitted answer and advance the session."""
    session = store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    result, response = store.submit(
        session,
        submitted=body.submitted,
        response_time_ms=body.response_time_ms,
        blur_count=body.blur_count,
        time_hidden_ms=body.time_hidden_ms,
    )

    if result == "complete":
        raise HTTPException(status_code=409, detail="Session already complete")

    # If this submission completed the test, persist the record.
    if session.is_complete:
        save_session(session)

    score = session.score()
    return SubmissionResult(
        correct=response.correct,
        score=score["correct"],
        answered=session.current_index,
        total_questions=session.total_questions,
        is_complete=session.is_complete,
    )


@app.get(
    "/api/session/{session_id}/summary", response_model=CompletionSummary
)
def get_summary(session_id: str):
    """Return final results for a completed session."""
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    if not session.is_complete:
        raise HTTPException(status_code=409, detail="Session not yet complete")

    score = session.score()
    return CompletionSummary(
        session_id=session.id,
        score=score["correct"],
        total_questions=session.total_questions,
        started_at=session.started_at,
        completed_at=session.last_activity,
    )