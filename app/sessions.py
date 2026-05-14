"""In-memory session management for Spell in Test.

A Session represents one participant's test attempt: a fixed-at-creation
order of items, the current position, and the responses so far.

Sessions live in process memory only; they do not survive a server restart.
This is acceptable for development and pilot use. A persistent store will
replace this module before public launch.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.items import ITEMS, get_item


# Tunables. Worth promoting to config later, but inline for now.
SESSION_IDLE_TIMEOUT = timedelta(minutes=30)
RANDOMISE_ORDER = True  # If False, items are served in canonical (id) order.
ITEMS_PER_SESSION = 10  # Set to None to use all available items.


@dataclass
class Response:
    """A single submitted answer within a session."""

    item_id: int
    submitted: str
    correct: bool
    submitted_at: datetime
    response_time_ms: int | None = None
    blur_count: int = 0
    time_hidden_ms: int = 0


@dataclass
class Session:
    """One participant's test attempt."""

    id: str
    item_ids: list[int]
    current_index: int = 0
    responses: list[Response] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def total_questions(self) -> int:
        return len(self.item_ids)

    @property
    def is_complete(self) -> bool:
        return self.current_index >= self.total_questions

    @property
    def next_item_id(self) -> int | None:
        """The id of the next item to serve, or None if the test is done."""
        if self.is_complete:
            return None
        return self.item_ids[self.current_index]

    def touch(self) -> None:
        """Record that the session has been interacted with."""
        self.last_activity = datetime.now(timezone.utc)

    def score(self) -> dict[str, int]:
        """Return the current score summary."""
        correct = sum(1 for r in self.responses if r.correct)
        return {"correct": correct, "total": self.total_questions}


class SessionStore:
    """In-memory store of active sessions, keyed by session id."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        """Create a new session with a freshly-determined item order."""
        self._expire_old()

        item_ids = [item["id"] for item in ITEMS]
        if RANDOMISE_ORDER:
            random.shuffle(item_ids)
        if ITEMS_PER_SESSION is not None:
            item_ids = item_ids[:ITEMS_PER_SESSION]

        session = Session(id=str(uuid.uuid4()), item_ids=item_ids)
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        """Look up a session by id, expiring stale ones on the way."""
        self._expire_old()
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.touch()
        return session

    def submit(
        self,
        session: Session,
        submitted: str,
        response_time_ms: int | None = None,
        blur_count: int = 0,
        time_hidden_ms: int = 0,
    ) -> tuple[Literal["ok"], Response] | tuple[Literal["complete"], None]:
        """Score and record an answer for the session's current question.

        Returns ('ok', response) if a response was recorded, advancing the
        session. Returns ('complete', None) if the test was already finished.
        """
        if session.is_complete:
            return ("complete", None)

        item = get_item(session.next_item_id)  # type: ignore[arg-type]
        assert item is not None, "Session referenced an unknown item id"

        # Scoring is delegated to app.scoring to keep the single-source-of-truth.
        from app.scoring import score_answer

        correct = score_answer(item, submitted)

        response = Response(
            item_id=item["id"],
            submitted=submitted,
            correct=correct,
            submitted_at=datetime.now(timezone.utc),
            response_time_ms=response_time_ms,
            blur_count=blur_count,
            time_hidden_ms=time_hidden_ms,
        )
        
        session.responses.append(response)
        session.current_index += 1
        session.touch()
        return ("ok", response)

    def _expire_old(self) -> None:
        """Remove sessions that have been idle longer than the timeout."""
        now = datetime.now(timezone.utc)
        stale = [
            sid
            for sid, s in self._sessions.items()
            if now - s.last_activity > SESSION_IDLE_TIMEOUT
        ]
        for sid in stale:
            del self._sessions[sid]

    @property
    def active_count(self) -> int:
        """Number of active (non-expired) sessions. Mostly for debugging."""
        self._expire_old()
        return len(self._sessions)


# A single store instance shared by the FastAPI app.
store = SessionStore()