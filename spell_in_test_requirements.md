# Spell in Test — Project Requirements

**Status:** Draft v3 — Python/FastAPI stack, post-MVP build
**Last updated:** 13 May 2026
**Stack note:** Initial planning assumed a Node/Netlify Functions stack. After review, switched to Python/FastAPI to match developer preference and skill set. The frontend remains plain HTML/CSS/JS.

## 1. Purpose and Scope

Spell in Test is an online spelling assessment for an adult audience (ages 16–70), intended for **public launch as a research instrument**. It presents a sequential series of fill-in-the-blank sentences, each requiring the user to type the missing word. Scoring is automatic and server-side. No personally identifying information is collected; demographic data is not collected in this version.

This document is the working reference for design and implementation decisions. Items marked **TBD** are open and must be decided before launch. Items marked ✅ are implemented as of v3.

---

## 2. Functional Requirements

### 2.1 Test Flow

- **F-1.** ✅ The test presents one question at a time, in a fixed sequential order. No "back" or "skip" button is provided; submissions are final.
- **F-2.** ✅ Each question consists of a fill-in-the-blank sentence (e.g. "A _______ of a country is a person who was born there.") and a single text input for the missing word.
- **F-3.** ✅ A persistent progress indicator is shown (e.g. "Question 12 of 50").
- **F-4.** ✅ On submission, the answer is sent to the server for scoring. The next question is shown only after the server acknowledges the submission.
- **F-5.** ✅ At the end of the test, the user is shown a completion screen displaying their final score as "You got X out of N correct." No per-question feedback is shown during the test.
- **F-16.** ✅ The first letter of the target word is displayed as a hint alongside the sentence. This is an intentional design decision: the hint isolates spelling ability from word-retrieval ability, reducing construct-irrelevant variance in the data.
- **F-17.** ✅ An intro screen is shown before the test begins, explaining the rules (number of questions, time per question, paste disabled, no going back). A "Start the test" button advances to the first question.

### 2.2 Answer Validation

- **F-6.** ✅ Answer comparison is **case-insensitive** and **trims leading/trailing whitespace**. No other normalisation is applied (e.g. punctuation inside the answer is significant).
- **F-7.** ✅ Each item defines an `accepted_answers` array to handle regional spelling variants (e.g. `["manoeuvring", "maneuvering"]`). A match against any element in the array is correct.
- **F-8.** ✅ **All scoring is performed server-side.** The client never knows whether an answer was correct until the server responds, and never has access to the answer key.

### 2.3 Time Limit

- **F-9.** ✅ Each question has a per-question time limit of **12 seconds**, to be re-piloted and adjusted based on response-time distributions on easier items.
- **F-10.** ✅ The timer is displayed as a visible depleting bar (not a numeric countdown).
- **F-11.** ✅ A short grace period (~0.5 s) elapses before the timer starts, to allow the user to read the sentence.
- **F-12.** ✅ When the timer expires, whatever is currently in the input is auto-submitted. An empty input is submitted as a blank answer.
- **F-13.** ✅ The timer **does not pause** when the browser tab loses focus.

### 2.4 Progress Persistence

- **F-14.** Current question index and answers-so-far are saved to `localStorage` after each submission, so an accidental refresh does not lose progress. **Not yet implemented.**
- **F-15.** On page load, if a saved session exists, the user is offered the option to resume or restart. **Not yet implemented.**

---

## 3. Anti-Cheat and Integrity Requirements

### 3.1 Input Restrictions

- **I-1.** ✅ The answer input has `spellcheck="false"`, `autocorrect="off"`, `autocomplete="off"`, and `autocapitalize="off"` set.
- **I-2.** ✅ Paste events (`paste`), drop events (`drop`), and the right-click context menu (`contextmenu`) are blocked on the answer input via JavaScript `preventDefault()`.
- **I-3.** ✅ When a paste attempt is blocked, a brief non-judgmental message is shown ("Please type your answer — paste is disabled for this test."). The message fades after a few seconds.

### 3.2 Behavioural Logging

- **I-4.** ✅ Response time per question is recorded and submitted alongside each answer.
- **I-5.** ✅ Tab-visibility changes during each question are logged via the Page Visibility API (`visibilitychange` event). The number of blur events (`blur_count`) and total time hidden (`time_hidden_ms`) per question are recorded. Tab-switching is **not blocked**, only logged.
- **I-6.** ✅ These signals are stored with the response and may be used to flag or exclude responses during analysis. The user is not penalised in real time.

### 3.3 Acknowledged Limitations

The following are known and accepted limitations, to be acknowledged in any research output:

- A user with browser devtools can disable client-side JavaScript and bypass paste-blocking and timer enforcement.
- A user with a second device or a second person in the room cannot be detected.
- Browser extensions (e.g. Grammarly) may inject spell-check despite the input attributes; this is mitigated but not eliminated.

The combined defences (time limit + paste block + spell-check attributes + visibility logging) make casual cheating slower than honest answering, which is the practical goal. Anonymous participants have no incentive to cheat.

---

## 4. Bot and Spam Protection

- **B-1.** **Cloudflare Turnstile** is used on test submission. The token is verified server-side before any data is stored. **Not yet implemented.**
- **B-2.** ✅ A **honeypot field** (a hidden text input named `website`, off-screen via CSS) is included on the intro screen. Submissions with the honeypot populated receive a silent fake-success response (all-zeros UUID, zero questions) so the bot cannot distinguish rejection from success.
- **B-3.** A **minimum-completion-time check** is enforced server-side: a submission claiming to complete the full test in less than a plausible human minimum (TBD based on test length and per-question timer) is rejected. **Not yet implemented.**
- **B-4.** Per-IP rate limiting is applied. **Not yet implemented.** Likely via **slowapi** (FastAPI/Starlette port of Flask-Limiter), or via host-provided edge limits.
- **B-5.** ✅ All submissions go through the FastAPI backend. The data store is **not** exposed to the client directly.

---

## 5. Technical Architecture

### 5.1 Frontend

- **T-1.** ✅ Vanilla HTML, CSS, and JavaScript in the browser. No frontend framework (React, Vue, etc.). HTML is rendered server-side from Jinja2 templates; the browser receives plain HTML/CSS/JS with no build step.
- **T-2.** ✅ Mobile-first responsive design. Large touch targets (minimum 44×44 px), large input field, comfortable text size (≥18 px body).
- **T-3.** ✅ Client-side JavaScript handles only: per-question timer countdown, paste/drop/context-menu blocking, tab-visibility logging, and form submission. All scoring logic is server-side.

### 5.2 Backend

- **T-4.** ✅ **Python** with **FastAPI** as the web framework, served by **Uvicorn** (ASGI server). Single application; no separate "serverless function" tier.
- **T-5.** ✅ Templating via **Jinja2**, integrated with FastAPI. Templates live in `templates/`, static assets (CSS, JS) in `static/`.
- **T-6.** ✅ Python version: **>=3.12**. Dependencies managed by **uv** via `pyproject.toml` and `uv.lock`.
- **T-7.** ✅ FastAPI routes handle, on each submission:
  1. Cloudflare Turnstile token verification. *(not yet implemented)*
  2. Honeypot field check and rate-limit check. *(honeypot done; rate-limit not yet)*
  3. Server-side scoring against the answer key.
  4. Persisting the scored result to the data store.
- **T-8.** ✅ The answer key (item bank with `accepted_answers` arrays) is loaded from `data/items.json` at server startup and **never** sent to the client. The browser only ever receives the sentence text and the first-letter hint.

### 5.3 Session Management

- **T-13.** ✅ Sessions are managed server-side. The frontend never selects which question to ask; it requests the "next question" and the server decides. This prevents tampering with question order or repetition.
- **T-14.** ✅ Sessions are stored **in memory** in the Python process, keyed by UUID. They do not survive a server restart. This is acceptable for development and pilot use; a persistent session store will be required before public deployment.
- **T-15.** ✅ Item order within a session is **randomised at session creation** and fixed thereafter. Each session gets its own random sample of items.
- **T-16.** ✅ Number of items per session is configurable (constant `ITEMS_PER_SESSION` in `app/sessions.py`). Currently set to 2 for development; will be raised before launch.
- **T-17.** ✅ Sessions expire after **30 minutes of inactivity**. Expired sessions are reaped opportunistically on the next store interaction (no background sweeper required at current traffic levels).

### 5.4 Hosting

- **T-9.** Hosting platform: **TBD.** Realistic candidates for a Python/FastAPI application: **Railway**, **Render**, **Fly.io**, or **PythonAnywhere**. Railway and Render are the most beginner-friendly and integrate directly with GitHub for automatic deploys.
- **T-10.** ✅ Local development uses `uvicorn app.main:app --reload` for hot-reloading on file changes.

### 5.5 Data Store

- **T-11.** ✅ Completed test results are persisted to `data/responses.jsonl`, one JSON line per completed session. This is a deliberately simple, append-only format suitable for pilot use. A database (SQLite or PostgreSQL) will replace this for public launch.
- **T-12.** ✅ The `responses.jsonl` file is gitignored.

### 5.6 Data Recorded per Submission

For each completed test, a single record is appended to `data/responses.jsonl` containing:

- ✅ Anonymous session ID (UUID generated server-side, no link to identity)
- ✅ Timestamp started (`started_at`, ISO 8601 UTC)
- ✅ Timestamp completed (`completed_at`, ISO 8601 UTC)
- ✅ Final score (count correct) and total questions
- ✅ For each question: `item_id`, submitted answer (raw), correct/incorrect (server-determined), `response_time_ms`, `blur_count`, `time_hidden_ms`, `submitted_at`
- Coarse locale indicator from `Accept-Language` header (for regional-spelling analysis). **Not yet implemented.**

**No** IP address, email, name, or identifying information is stored.

---

## 6. Accessibility Requirements

- **A-1.** ✅ High-contrast colour scheme meeting WCAG AA contrast ratios. *(implemented as defaults; not yet audited)*
- **A-2.** ✅ Full keyboard navigation: Tab to input, Enter to submit, no mouse required.
- **A-3.** ✅ Visible focus states on all interactive elements.
- **A-4.** ✅ Screen-reader labels (`aria-label`, `aria-live` for progress and timer updates).
- **A-5.** ✅ Sufficient text size (18 px body, larger for the question itself).
- **A-6.** Tested with at least one screen reader (NVDA or VoiceOver) before public launch. **Not yet done.**

---

## 7. Privacy

- **P-1.** ✅ A brief privacy notice is shown on the intro screen, stating: no personal data is collected, results are anonymous, and the purpose of data collection (research). Clicking "Start the test" constitutes consent.
- **P-2.** ✅ No demographics, no email, no name, no account, no IP address recorded.
- **P-3.** As an Irish-based project under GDPR, the legal basis for processing is legitimate interest in research, applied to anonymous-only data.

---

## 8. Item Bank

- **C-1.** Test length: **TBD.** Currently 59 items available; per-session count configurable via `ITEMS_PER_SESSION`. Original target was 40–60 items per session. At 12 s/question, 50 items = ~10 minutes plus reading time.
- **C-2.** ✅ Each item is a fill-in-the-blank sentence with one missing word. Currently one sentence per item; see C-7.
- **C-3.** ✅ Each item has an `accepted_answers` array covering all valid regional spellings.
- **C-4.** Items must be reviewed by multiple native English speakers for clarity and unambiguity before piloting. **Initial review completed for current 59 items; additional review recommended before launch.**
- **C-5.** Item difficulty range and sourcing approach: items sourced from author's existing list; no difficulty tagging in v1. Difficulty may be inferred from pilot data after launch.
- **C-6.** A piloting phase with a small, friendly audience precedes any public launch.
- **C-7.** **Planned for v2:** Each item supports multiple sentence variants. One sentence is chosen at session creation per item and recorded with the response. The same participant in the same session sees a fixed sentence for each item; different sessions may see different variants. This enables per-sentence analysis of item performance and lets weak sentences be identified and improved.
- **C-8.** **Planned for v2:** Items may carry optional editorial metadata: known typical misspellings (`typical_misspellings`), words commonly confused with the answer (`confused_with`), and free-form authoring notes (`notes`). These are documentation aids, not used for scoring.
- **C-9.** **Architectural principle:** Item performance statistics (correctness rate, observed misspellings, response times) are computed from the responses log on demand, never stored on items themselves. The item bank is *authored content*; statistics are *derived data*. The two must remain in separate storage with separate lifecycles.
- **C-10.** **Planned for v2:** Promote `Item` from TypedDict to frozen `@dataclass` with methods (`pick_sentence`, `is_correct`). Behaviour for "what can I do with an item" co-locates with the data; the dataclass is immutable to prevent runtime mutation of the bank.

---

## 9. Open Items (TBD)

The following decisions are not yet made and should be resolved before public launch:

1. Final test length and total time budget.
2. Choice of data store for production (SQLite vs. PostgreSQL via Railway/Render/Supabase/Neon).
3. Choice of hosting platform (Railway, Render, Fly.io, PythonAnywhere).
4. Choice of rate-limiting implementation (slowapi vs. host-edge).
5. Item sourcing for any additional items beyond the current 59.
6. Recruitment approach for public launch (and how that affects sample composition).
7. Final per-question timer value after piloting.
8. Whether to include a practice/example question before the scored test begins.
9. Number of sentence variants per word to author for v2 (target: 3 per word).
10. Minimum-completion-time threshold for bot rejection (depends on final test length).
11. Persistent session storage strategy (database-backed sessions vs. cookie-backed JWT vs. accept-the-loss-on-restart).

---

## 10. Out of Scope for This Version

The following were considered and explicitly deferred:

- Demographic collection (Age, Gender, Education).
- User accounts or authentication.
- Adaptive difficulty.
- Migration to Next.js / TypeScript / Supabase full-stack architecture.
- Real-time features or multi-user functionality.
- A "back" button or answer revision.
- Showing the correct answer to the user after each question.
- Per-item feedback during the test.

---

## 11. Implementation Status Snapshot

As of v3 of this document (end of day 1 of implementation), the following are implemented and committed to git:

- FastAPI scaffold with Jinja2 templates and static assets
- 59-item bank with regional variants, loaded and validated at startup
- Server-side scoring (case-insensitive, whitespace-tolerant, accepts variants)
- In-memory session store with random ordering and 30-min idle expiry
- Configurable items-per-session cap (currently 2 for testing)
- Four-route API: start session, get current question, submit answer, get summary
- Frontend: intro screen, test screen, completion screen
- 12-second per-question timer with auto-submit
- Paste/drop/right-click blocked on the answer input
- Tab-visibility tracking per question (`blur_count`, `time_hidden_ms`)
- Honeypot bot trap on session creation
- Privacy notice on intro screen
- Persistent JSONL storage of completed test results

Remaining for v1 public launch:

- localStorage progress persistence
- Cloudflare Turnstile integration
- Minimum-completion-time check
- Rate limiting
- Accessibility audit with screen reader
- Persistent session storage
- Deployment to a hosting platform
- Database for results (replacing JSONL)

Planned for v2:

- Multi-sentence-per-word item structure (C-7)
- Editorial metadata on items (C-8)
- `Item` dataclass with methods (C-10)
- Analysis module for derived statistics (C-9)