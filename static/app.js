// Spell in Test — frontend logic.
// Talks to /api/session, /api/submit, etc.

const QUESTION_TIME_MS = 12_000;
const READING_GRACE_MS = 500;
const PASTE_MESSAGE = "Please type your answer — paste is disabled for this test.";

// --- DOM references ---
const screens = {
    intro: document.getElementById("screen-intro"),
    resume: document.getElementById("screen-resume"),
    test: document.getElementById("screen-test"),
    complete: document.getElementById("screen-complete"),
};
const elProgress = document.getElementById("progress-text");
const elSentence = document.getElementById("sentence");
const elHint = document.getElementById("hint");
const elAnswer = document.getElementById("answer");
const elTimerBar = document.getElementById("timer-bar");
const elPasteWarn = document.getElementById("paste-warning");
const elForm = document.getElementById("answer-form");
const elFinalCorrect = document.getElementById("final-correct");
const elFinalTotal = document.getElementById("final-total");
const elBtnStart = document.getElementById("btn-start");
const elBtnResume = document.getElementById("btn-resume");
const elBtnRestart = document.getElementById("btn-restart");
const elResumePosition = document.getElementById("resume-position");
const elResumeTotal = document.getElementById("resume-total");

// --- State ---
let sessionId = null;
let totalQuestions = 0;
let questionStart = 0;       // timestamp when current question was shown
let timerInterval = null;     // setInterval handle for the timer bar
let timeoutHandle = null;     // setTimeout handle for auto-submit
let submitting = false;       // guard against double-submit

// Visibility tracking — reset per question.
let blurCount = 0;
let timeHiddenMs = 0;
let hiddenSince = null;       // timestamp when page became hidden, or null

// --- localStorage progress persistence ---

const STORAGE_KEY = "spell-in-test:session";
const FRESHNESS_MS = 30 * 60 * 1000; // 30 minutes

function saveProgress(sessionId, totalQuestions) {
    const record = {
        session_id: sessionId,
        total_questions: totalQuestions,
        started_at: Date.now(),
    };
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
    } catch (err) {
        // localStorage might be disabled (private browsing) or full.
        // Not fatal — the test still works, it just won't survive a refresh.
        console.warn("Could not save progress:", err);
    }
}

function loadProgress() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return null;
        const record = JSON.parse(raw);
        if (!record.session_id || !record.started_at) return null;
        if (Date.now() - record.started_at > FRESHNESS_MS) {
            // Too old — clear and treat as no saved session.
            clearProgress();
            return null;
        }
        return record;
    } catch (err) {
        console.warn("Could not read saved progress:", err);
        return null;
    }
}

function clearProgress() {
    try {
        localStorage.removeItem(STORAGE_KEY);
    } catch (err) {
        // Ignore.
    }
}

// --- Screen helpers ---

function showScreen(name) {
    for (const key in screens) {
        screens[key].classList.toggle("active", key === name);
    }
}

// --- API ---

async function apiStartSession() {
    const honeypot = document.getElementById("hp-website").value;
    const res = await fetch("/api/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ website: honeypot }),
    });
    if (!res.ok) throw new Error("Failed to start session");
    return res.json();
}

async function apiGetSessionState(sid) {
    const res = await fetch(`/api/session/${sid}`);
    if (res.status === 404) return null;  // expired or unknown
    if (!res.ok) throw new Error("Failed to fetch session state");
    return res.json();
}

async function apiGetQuestion(sid) {
    const res = await fetch(`/api/session/${sid}/question`);
    if (!res.ok) throw new Error("Failed to fetch question");
    return res.json();
}

async function apiSubmit(sid, submitted, responseTimeMs, blurCount, timeHiddenMs) {
    const res = await fetch("/api/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            session_id: sid,
            submitted,
            response_time_ms: responseTimeMs,
            blur_count: blurCount,
            time_hidden_ms: timeHiddenMs,
        }),
    });
    if (!res.ok) throw new Error("Failed to submit answer");
    return res.json();
}

async function apiGetSummary(sid) {
    const res = await fetch(`/api/session/${sid}/summary`);
    if (!res.ok) throw new Error("Failed to fetch summary");
    return res.json();
}

// --- Timer ---

function startTimer() {
    const startedAt = performance.now();
    elTimerBar.style.width = "100%";

    // Visible countdown — update every 100ms.
    timerInterval = setInterval(() => {
        const elapsed = performance.now() - startedAt;
        const remaining = Math.max(0, QUESTION_TIME_MS - elapsed);
        const pct = (remaining / QUESTION_TIME_MS) * 100;
        elTimerBar.style.width = `${pct}%`;
    }, 100);

    // Hard timeout — auto-submit at expiry.
    timeoutHandle = setTimeout(() => {
        handleSubmit({ timedOut: true });
    }, QUESTION_TIME_MS);
}

function stopTimer() {
    clearInterval(timerInterval);
    clearTimeout(timeoutHandle);
    timerInterval = null;
    timeoutHandle = null;
}

// --- Paste warning ---

let warningTimeout = null;
function flashPasteWarning() {
    elPasteWarn.textContent = PASTE_MESSAGE;
    elPasteWarn.classList.add("show");
    clearTimeout(warningTimeout);
    warningTimeout = setTimeout(() => {
        elPasteWarn.classList.remove("show");
    }, 3000);
}

// --- Visibility tracking ---

function resetVisibilityTracking() {
    blurCount = 0;
    timeHiddenMs = 0;
    hiddenSince = null;
}

function handleVisibilityChange() {
    if (document.hidden) {
        // Page just became hidden.
        blurCount += 1;
        hiddenSince = performance.now();
    } else if (hiddenSince !== null) {
        // Page just became visible again; accumulate the hidden interval.
        timeHiddenMs += performance.now() - hiddenSince;
        hiddenSince = null;
    }
}

document.addEventListener("visibilitychange", handleVisibilityChange);

// --- Question flow ---

async function loadNextQuestion() {
    const q = await apiGetQuestion(sessionId);
    elSentence.textContent = q.sentence.replace(/_+/g, "______");
    elHint.textContent = q.first_letter;
    elProgress.textContent = `Question ${q.question_number} of ${q.total_questions}`;
    elAnswer.value = "";
    elAnswer.disabled = false;
    submitting = false;

    resetVisibilityTracking();

    // Brief grace period before timer starts and input is focusable.
    setTimeout(() => {
        elAnswer.focus();
        questionStart = performance.now();
        startTimer();
    }, READING_GRACE_MS);
}

async function handleSubmit({ timedOut = false } = {}) {
    if (submitting) return;
    submitting = true;
    stopTimer();
    elAnswer.disabled = true;

    // If the page is still hidden at submission time, close out the interval.
    if (hiddenSince !== null) {
        timeHiddenMs += performance.now() - hiddenSince;
        hiddenSince = null;
    }

    const submitted = elAnswer.value;
    const responseTimeMs = Math.round(performance.now() - questionStart);
    const finalBlurCount = blurCount;
    const finalTimeHiddenMs = Math.round(timeHiddenMs);

    try {
        const result = await apiSubmit(
            sessionId, submitted, responseTimeMs, finalBlurCount, finalTimeHiddenMs
        );
        if (result.is_complete) {
            clearProgress();
            await showCompletion();
        } else {
            saveProgress(sessionId, totalQuestions);
            await loadNextQuestion();
        }
    } catch (err) {
        console.error(err);
        // Best-effort: try to load the next question anyway.
        await loadNextQuestion();
    }
}

async function showCompletion() {
    const summary = await apiGetSummary(sessionId);
    elFinalCorrect.textContent = summary.score;
    elFinalTotal.textContent = summary.total_questions;
    showScreen("complete");
}

// --- Wire up the UI ---

elBtnStart.addEventListener("click", async () => {
    elBtnStart.disabled = true;
    try {
        const session = await apiStartSession();
        sessionId = session.session_id;
        totalQuestions = session.total_questions;
        saveProgress(sessionId, totalQuestions);
        showScreen("test");
        await loadNextQuestion();
    } catch (err) {
        console.error(err);
        alert("Couldn't start the test. Please refresh the page.");
        elBtnStart.disabled = false;
    }
});

elBtnResume.addEventListener("click", async () => {
    elBtnResume.disabled = true;
    elBtnRestart.disabled = true;
    try {
        // The session was already validated on page load; this just continues.
        showScreen("test");
        await loadNextQuestion();
    } catch (err) {
        console.error(err);
        alert("Couldn't resume. Please refresh and start a new test.");
        clearProgress();
        location.reload();
    }
});

elBtnRestart.addEventListener("click", () => {
    clearProgress();
    sessionId = null;
    totalQuestions = 0;
    showScreen("intro");
});

elForm.addEventListener("submit", (e) => {
    e.preventDefault();
    handleSubmit();
});

// Block paste, drop, and right-click context menu on the answer input.
elAnswer.addEventListener("paste", (e) => {
    e.preventDefault();
    flashPasteWarning();
});
elAnswer.addEventListener("drop", (e) => {
    e.preventDefault();
    flashPasteWarning();
});
elAnswer.addEventListener("contextmenu", (e) => {
    e.preventDefault();
});

// --- Page load: check for a resumable session ---

async function checkForResumableSession() {
    const saved = loadProgress();
    if (!saved) return;

    // Validate with the server. The server is authoritative.
    let state;
    try {
        state = await apiGetSessionState(saved.session_id);
    } catch (err) {
        console.warn("Could not validate saved session:", err);
        return;
    }
    if (state === null) {
        // Server doesn't know this session — it expired or the server restarted.
        clearProgress();
        return;
    }
    if (state.is_complete) {
        // Edge case: test was already finished but localStorage wasn't cleared.
        clearProgress();
        return;
    }

    // Valid resumable session. Set up state and show the resume screen.
    sessionId = state.session_id;
    totalQuestions = state.total_questions;
    elResumePosition.textContent = state.current_index + 1;
    elResumeTotal.textContent = state.total_questions;
    showScreen("resume");
}

checkForResumableSession();
