"""Persistence for completed test sessions.

Appends one JSON line per completed session to data/responses.jsonl.
This is a deliberately simple format: append-only, no schema migrations,
easy to inspect with `cat`, easy to load with pandas later. A real
database will replace this before public launch.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.sessions import Session


# Resolve the responses file relative to the project root.
RESPONSES_FILE = Path(__file__).resolve().parent.parent / "data" / "responses.jsonl"


def _serialise_datetime(obj: Any) -> str:
    """JSON serialiser for datetime objects (which json.dumps can't handle)."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def session_to_record(session: Session) -> dict[str, Any]:
    """Convert a completed Session into the dict shape we persist.

    Kept as a separate pure function so it can be tested without touching disk.
    """
    score = session.score()
    return {
        "session_id": session.id,
        "started_at": session.started_at,
        "completed_at": session.last_activity,
        "score": score["correct"],
        "total_questions": score["total"],
        "responses": [asdict(r) for r in session.responses],
    }


def save_session(session: Session) -> None:
    """Append a completed session's record to the responses file.

    Creates the file if it doesn't exist. Each session is one line of JSON.
    Should only be called for sessions where is_complete is True.
    """
    if not session.is_complete:
        # Defensive guard. The caller should only invoke this on completed
        # sessions, but if they don't, fail loudly rather than write partial data.
        raise ValueError(
            f"save_session called on incomplete session {session.id}"
        )

    record = session_to_record(session)

    # Ensure the data directory exists. parents=True handles fresh checkouts
    # where the directory might not exist yet.
    RESPONSES_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Append one JSON line. ensure_ascii=False preserves accented characters.
    with RESPONSES_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=_serialise_datetime, ensure_ascii=False))
        f.write("\n")


def count_completed_sessions() -> int:
    """Return how many completed sessions are on disk. Useful for sanity checks."""
    if not RESPONSES_FILE.exists():
        return 0
    with RESPONSES_FILE.open(encoding="utf-8") as f:
        return sum(1 for _ in f)