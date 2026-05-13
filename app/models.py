"""Pydantic models for the public API.

These define what crosses the network boundary: validated request bodies,
serialised response bodies. Internal domain objects (Session, Item) stay
as dataclasses/TypedDict; these are their wire-format equivalents.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# --- Requests ---

class StartSessionRequest(BaseModel):
    """Body of POST /api/session.

    The 'website' field is a honeypot: real users never see or fill in this
    field. Bots that auto-fill all form fields will populate it, which lets
    us identify and silently reject them.
    """

    website: str = Field(default="", max_length=200)


class SubmitRequest(BaseModel):
    """Body of POST /api/submit."""

    session_id: str
    submitted: str = Field(..., max_length=200)
    response_time_ms: int | None = Field(default=None, ge=0, le=600_000)
    blur_count: int = Field(default=0, ge=0, le=1000)
    time_hidden_ms: int = Field(default=0, ge=0, le=3_600_000)


# --- Responses ---

class SessionStarted(BaseModel):
    """Returned when a new test session is created."""

    session_id: str
    total_questions: int


class QuestionView(BaseModel):
    """One question, as it should appear to the participant.

    Notably absent: the answer. This is the public view of an item plus
    session-level context.
    """

    item_id: int
    sentence: str
    first_letter: str
    question_number: int   # 1-indexed for display
    total_questions: int


class SubmissionResult(BaseModel):
    """Returned after submitting an answer."""

    correct: bool
    score: int
    answered: int
    total_questions: int
    is_complete: bool


class CompletionSummary(BaseModel):
    """Returned when the test is finished."""

    session_id: str
    score: int
    total_questions: int
    started_at: datetime
    completed_at: datetime