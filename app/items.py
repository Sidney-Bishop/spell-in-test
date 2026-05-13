"""Item bank loader for Spell in Test.

Loads the item bank from data/items.json at module import time.
The bank is read-only at runtime; the answer key never leaves the server.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict


class Item(TypedDict):
    """Shape of a single item in the bank."""

    id: int
    sentence: str
    first_letter: str
    answer: str
    accepted_answers: list[str]


# Resolve the data file relative to the project root, not the current working dir.
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "items.json"


def _load_items() -> list[Item]:
    """Read and validate the item bank from disk. Called once at import."""
    with DATA_FILE.open(encoding="utf-8") as f:
        data = json.load(f)

    items: list[Item] = data["items"]

    # Sanity checks — fail fast at startup rather than mid-test.
    seen_ids: set[int] = set()
    for item in items:
        if item["id"] in seen_ids:
            raise ValueError(f"Duplicate item id: {item['id']}")
        seen_ids.add(item["id"])

        if not item["accepted_answers"]:
            raise ValueError(f"Item {item['id']} has no accepted answers")

        if item["answer"] not in item["accepted_answers"]:
            raise ValueError(
                f"Item {item['id']}: canonical answer "
                f"{item['answer']!r} not in accepted_answers"
            )

    return items


# Loaded once at import; treated as immutable thereafter.
ITEMS: list[Item] = _load_items()
ITEMS_BY_ID: dict[int, Item] = {item["id"]: item for item in ITEMS}


def get_item(item_id: int) -> Item | None:
    """Return the item with the given id, or None if not found."""
    return ITEMS_BY_ID.get(item_id)


def get_all_items() -> list[Item]:
    """Return the full list of items, in canonical order."""
    return ITEMS


def public_view(item: Item) -> dict[str, int | str]:
    """Return only the fields safe to send to the client.

    The answer key (answer, accepted_answers) is stripped.
    """
    return {
        "id": item["id"],
        "sentence": item["sentence"],
        "first_letter": item["first_letter"],
    }