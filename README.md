# Spell in Test

An online spelling assessment built with Python, FastAPI, and plain HTML/CSS/JS.

This is **version 1.0** — a locally-runnable build intended for development and personal pilot use. It is not yet ready for public deployment; see "Status and limitations" below.

## What it does

Presents the participant with a sequence of fill-in-the-blank sentences, each missing one word. The participant types the missing word and submits. Each question has a 12-second time limit. The test concludes with a final score.

The intent is to support research into adult spelling — specifically, the *kinds* of errors people make when they misspell a word.

## Quick start

Prerequisites: Python 3.12 or newer, and [uv](https://docs.astral.sh/uv/) installed.

```bash
# Clone or copy the project, then from the project root:
uv sync                                  # install dependencies
uv run uvicorn app.main:app --reload     # start the dev server
```

Open <http://127.0.0.1:8000/> in a browser. Click "Start the test" and answer the questions.

The API documentation is available at <http://127.0.0.1:8000/docs> — useful for inspecting endpoints or testing the API directly.

## What's in this version

- **Test flow:** intro screen, 10-question test (randomly sampled from a 59-item bank), completion screen with score.
- **Per-question timer:** 12 seconds, with a visible depleting bar. Auto-submits on expiry.
- **Server-side scoring:** case-insensitive, whitespace-tolerant, accepts regional spelling variants.
- **First-letter hint:** the first letter of the target word is shown alongside each sentence, to isolate spelling ability from word-retrieval ability.
- **Anti-cheat measures:** paste, drop, and right-click blocked on the answer input. Spell-check disabled at the input level. Tab-visibility logged per question (not blocked, just recorded).
- **Bot trap:** a hidden honeypot field on session creation. Submissions with the honeypot populated receive a silent fake-success response.
- **Privacy notice:** displayed on the intro screen. No name, email, IP address, or other identifying information is collected. Demographic data is not collected in this version.
- **Progress persistence:** the test survives an accidental refresh. A "Welcome back" screen offers Resume or Start over.
- **Result storage:** each completed test is appended as one JSON line to `data/responses.jsonl`.

## Project layout

```
spell-in-test/
├── app/                    # Python application code
│   ├── main.py             # FastAPI app and route handlers
│   ├── items.py            # Item bank loader and public-view security boundary
│   ├── scoring.py          # Server-side answer scoring
│   ├── sessions.py         # In-memory session management
│   ├── storage.py          # JSONL persistence for completed sessions
│   └── models.py           # Pydantic request/response models
├── static/                 # CSS, JS served to the browser
│   ├── styles.css
│   └── app.js              # Frontend logic: timer, paste blocking, etc.
├── templates/              # Jinja2 HTML templates
│   └── index.html          # Single-page UI (intro, resume, test, complete)
├── data/
│   ├── items.json          # Item bank (sentences and answers) — server-only
│   └── responses.jsonl     # Completed test results (gitignored)
├── docs/
│   └── questions_source.md # Archive of the original question source
├── pyproject.toml          # Project config and dependencies
├── uv.lock                 # Pinned dependency versions
└── spell_in_test_requirements.md  # Full project requirements
```

## Status and limitations

This version runs locally only. Specifically:

- **Sessions are in-memory.** They do not survive a server restart. Acceptable for local development; unsuitable for public deployment.
- **Results live in a local JSONL file.** Fine for inspecting on disk; a real database is needed before public launch.
- **No deployment configuration.** No Docker, no hosting platform setup, no environment-variable management.
- **Bot defences are partial.** The honeypot works, but Cloudflare Turnstile, rate limiting, and a minimum-completion-time check are not yet implemented.
- **Accessibility has not been audited.** Foundations are in place (high contrast, keyboard navigation, ARIA labels) but no screen-reader testing has been done.
- **No demographic data is collected.** This is by design for v1.0; see the requirements doc for the v2 plan.

For the full list of what's done, what's pending, and what's deferred, see [`spell_in_test_requirements.md`](spell_in_test_requirements.md).

## Inspecting test data

After running the test a few times, you can look at the recorded results:

```bash
cat data/responses.jsonl                                # all completed tests
tail -1 data/responses.jsonl | python3 -m json.tool     # most recent, pretty-printed
```

Each line is a self-contained JSON object representing one completed test, including all submitted answers, per-question response times, and tab-visibility tracking.

## Development notes

- The dev server (`uvicorn ... --reload`) auto-restarts when you change Python files. For frontend changes (HTML, CSS, JS), just refresh the browser.
- The item bank lives in `data/items.json` and is loaded once at server startup. Editing it requires a server restart (or auto-reload will pick it up if you also touch a Python file).
- The number of questions per session is controlled by `ITEMS_PER_SESSION` in `app/sessions.py`. Set to an integer for a fixed sample size, or `None` to use all available items.

## Licence and use

This project is intended for research and personal use. No licence has been formally chosen yet.