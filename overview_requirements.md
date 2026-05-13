# Spell in Test — Project Requirements

**Status:** Draft v2 — supersedes original overview
**Last updated:** 13 May 2026

## 1. Purpose and Scope

Spell in Test is an online spelling assessment for an adult audience (ages 16–70), intended for **public launch as a research instrument**. It presents a sequential series of fill-in-the-blank sentences, each requiring the user to type the missing word. Scoring is automatic and server-side. No personally identifying information is collected; demographic data is not collected in this version.

This document is the working reference for design and implementation decisions. Items marked **TBD** are open and must be decided before launch.

---

## 2. Functional Requirements

### 2.1 Test Flow

- **F-1.** The test presents one question at a time, in a fixed sequential order. No "back" or "skip" button is provided; submissions are final.
- **F-2.** Each question consists of a fill-in-the-blank sentence (e.g. "A _______ of a country is a person who was born there.") and a single text input for the missing word.
- **F-3.** A persistent progress indicator is shown (e.g. "Question 12 of 50").
- **F-4.** On submission, the answer is sent to the server for scoring. The next question is shown only after the server acknowledges the submission.
- **F-5.** At the end of the test, the user is shown a completion screen. **TBD:** whether a final score is displayed, and in what form (raw, percentage, qualitative band, none).

### 2.2 Answer Validation

- **F-6.** Answer comparison is **case-insensitive** and **trims leading/trailing whitespace**. No other normalisation is applied (e.g. punctuation inside the answer is significant).
- **F-7.** Each item defines an `acceptedAnswers` array to handle regional spelling variants (e.g. `["colour", "color"]`, `["judgement", "judgment"]`). A match against any element in the array is correct.
- **F-8.** **All scoring is performed server-side.** The client never knows whether an answer was correct until the server responds, and never has access to the answer key.

### 2.3 Time Limit

- **F-9.** Each question has a per-question time limit. **Initial target: 12 seconds**, to be piloted and adjusted based on response-time distributions on easier items.
- **F-10.** The timer is displayed as a visible depleting bar (not a numeric countdown).
- **F-11.** A short grace period (~0.5 s) elapses before the timer starts, to allow the user to read the sentence.
- **F-12.** When the timer expires, whatever is currently in the input is auto-submitted. An empty input is submitted as a blank answer.
- **F-13.** The timer **does not pause** when the browser tab loses focus.

### 2.4 Progress Persistence

- **F-14.** Current question index and answers-so-far are saved to `localStorage` after each submission, so an accidental refresh does not lose progress.
- **F-15.** On page load, if a saved session exists, the user is offered the option to resume or restart.

---

## 3. Anti-Cheat and Integrity Requirements

### 3.1 Input Restrictions

- **I-1.** The answer input has `spellcheck="false"`, `autocorrect="off"`, `autocomplete="off"`, and `autocapitalize="off"` set.
- **I-2.** Paste events (`paste`), drop events (`drop`), and the right-click context menu (`contextmenu`) are blocked on the answer input via JavaScript `preventDefault()`.
- **I-3.** When a paste attempt is blocked, a brief non-judgmental message is shown (e.g. "Please type your answer — paste is disabled for this test"). The message fades after a few seconds.

### 3.2 Behavioural Logging

- **I-4.** Response time per question is recorded and submitted alongside each answer.
- **I-5.** Tab-visibility changes during each question are logged via the Page Visibility API (`visibilitychange` event). The number of blur events and total time hidden per question is recorded. Tab-switching is **not blocked**, only logged.
- **I-6.** These signals are stored with the response and may be used to flag or exclude responses during analysis. The user is not penalised in real time.

### 3.3 Acknowledged Limitations

The following are known and accepted limitations, to be acknowledged in any research output:

- A user with browser devtools can disable client-side JavaScript and bypass paste-blocking and timer enforcement.
- A user with a second device or a second person in the room cannot be detected.
- Browser extensions (e.g. Grammarly) may inject spell-check despite the input attributes; this is mitigated but not eliminated.

The combined defences (time limit + paste block + spell-check attributes + visibility logging) make casual cheating slower than honest answering, which is the practical goal. Anonymous participants have no incentive to cheat.

---

## 4. Bot and Spam Protection

- **B-1.** **Cloudflare Turnstile** is used on test submission. The token is verified server-side before any data is stored.
- **B-2.** A **honeypot field** (a hidden input that real users never fill in) is included in the form. Submissions with the honeypot populated are silently discarded.
- **B-3.** A **minimum-completion-time check** is enforced server-side: a submission claiming to complete the full test in less than a plausible human minimum (TBD based on test length and per-question timer) is rejected.
- **B-4.** Per-IP rate limiting is applied at the serverless function layer.
- **B-5.** All submissions go through the serverless function. The data store endpoint is **not** exposed to the client.

---

## 5. Technical Architecture

### 5.1 Frontend

- **T-1.** Vanilla HTML, CSS, and JavaScript. No framework (Next.js, React, etc.) in this version. A framework migration may be considered post-launch but is explicitly out of scope here.
- **T-2.** Hosted on **Netlify** (or equivalent static host with serverless function support).
- **T-3.** Mobile-first responsive design. Large touch targets (minimum 44×44 px), large input field, comfortable text size.

### 5.2 Backend

- **T-4.** A single **serverless function** (Netlify Function or Cloudflare Worker — TBD) handles:
  1. Turnstile token verification.
  2. Rate limiting and honeypot check.
  3. Server-side scoring against the answer key.
  4. Writing the scored result to the data store.
- **T-5.** The answer key (item bank with `acceptedAnswers` arrays) lives **only** on the server side. The client receives only the sentence and the position of the blank.
- **T-6.** Data store: **TBD.** Options under consideration: Google Sheets via SheetDB (kept behind the function, not directly exposed), Cloudflare D1, Supabase Postgres. Decision deferred pending estimate of expected volume and analysis needs.

### 5.3 Data Recorded per Submission

For each completed test, a single record containing:

- Anonymous session ID (UUID generated client-side, no link to identity)
- Timestamp of completion
- For each question: question ID, submitted answer (raw), correct/incorrect (server-determined), response time in milliseconds, count of visibility-blur events, total time-hidden in milliseconds
- Final score (count correct, total questions)
- User-agent string (for device/browser analysis only)
- Coarse locale indicator from `Accept-Language` header (for regional-spelling analysis)

**No** IP address, email, name, or identifying information is stored.

---

## 6. Accessibility Requirements

- **A-1.** High-contrast colour scheme meeting WCAG AA contrast ratios.
- **A-2.** Full keyboard navigation: Tab to input, Enter to submit, no mouse required.
- **A-3.** Visible focus states on all interactive elements.
- **A-4.** Screen-reader labels (`aria-label`, `aria-live` for progress and timer updates).
- **A-5.** Sufficient text size (minimum 16 px body, larger for the question itself).
- **A-6.** Tested with at least one screen reader (NVDA or VoiceOver) before public launch.

---

## 7. Privacy

- **P-1.** A brief privacy notice is shown before the test begins, stating: no personal data is collected, results are anonymous, and the purpose of data collection (research).
- **P-2.** No demographics, no email, no name, no account.
- **P-3.** As an Irish-based project under GDPR, the legal basis for processing is legitimate interest in research, applied to anonymous-only data.

---

## 8. Item Bank

- **C-1.** Test length: **TBD.** Original target was 40–60 items; needs revisiting against per-question timer and expected total completion time. (At 12 s/question, 50 items = ~10 minutes plus reading time.)
- **C-2.** Each item is a single fill-in-the-blank sentence with one missing word.
- **C-3.** Each item has an `acceptedAnswers` array covering all valid regional spellings.
- **C-4.** Items must be reviewed by multiple native English speakers for clarity and unambiguity before piloting.
- **C-5.** Item difficulty range and sourcing approach: **TBD.**
- **C-6.** A piloting phase with a small, friendly audience precedes any public launch.

---

## 9. Open Items (TBD)

The following decisions are not yet made and should be resolved before public launch:

1. Final test length and total time budget.
2. Whether and how to show a final score to the user.
3. Choice of data store (SheetDB behind function vs. D1 vs. Supabase).
4. Choice of serverless platform (Netlify Functions vs. Cloudflare Workers).
5. Item sourcing, review process, and difficulty calibration approach.
6. Recruitment approach for public launch (and how that affects sample composition).
7. Final per-question timer value after piloting.
8. Whether to include a practice/example question before the scored test begins.

---

## 10. Out of Scope for This Version

The following were considered and explicitly deferred:

- Demographic collection (Age, Gender, Education).
- User accounts or authentication.
- Adaptive difficulty.
- Migration to Next.js / TypeScript / Supabase full-stack architecture.
- Real-time features or multi-user functionality.
- A "back" button or answer revision.