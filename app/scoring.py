"""Server-side scoring for Spell in Test.

All comparisons are case-insensitive and whitespace-trimmed.
This module is the single source of truth for what counts as a correct answer.
"""

from __future__ import annotations

from app.items import Item, get_item


def normalise(text: str) -> str:
    """Strip leading/trailing whitespace and lowercase the string.

    This is the canonical form used for comparison. No other normalisation
    is applied: punctuation inside the answer is preserved and significant.
    """
    return text.strip().lower()


def score_answer(item: Item, submitted: str) -> bool:
    """Return True if the submitted answer matches any accepted spelling.

    Comparison is case-insensitive and whitespace-trimmed. An empty
    submission is always wrong, even if the item somehow accepted an
    empty string.
    """
    submitted_normalised = normalise(submitted)
    if not submitted_normalised:
        return False
    accepted = {normalise(a) for a in item["accepted_answers"]}
    return submitted_normalised in accepted


def score_submission(item_id: int, submitted: str) -> bool | None:
    """Score a submission by item ID. Returns None if the item doesn't exist.

    This is the function the route handler calls. Separating it from
    score_answer() lets us test the pure scoring logic in isolation.
    """
    item = get_item(item_id)
    if item is None:
        return None
    return score_answer(item, submitted)