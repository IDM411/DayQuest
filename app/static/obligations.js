// DayQuest — Obligations Vault.
// Talks to the existing /api endpoints; no framework, no build step (same as
// the home screen's app.js). Lists obligations sorted by urgency and lets you
// add new ones through the inline capture field (POST /api/capture).

const activeList = document.getElementById("active-list");
const activeEmpty = document.getElementById("active-empty");
const activeError = document.getElementById("active-error");
const completedSection = document.getElementById("completed-section");
const completedList = document.getElementById("completed-list");

const captureForm = document.getElementById("capture-form");
const captureInput = document.getElementById("capture-input");
const captureSubmit = document.getElementById("capture-submit");
const captureFeedback = document.getElementById("capture-feedback");

// ---- Formatting helpers (shared shape with app.js) ----------------------

// ISO datetime -> "Overdue", "Today", "Thursday", or "Jun 23".
function formatDeadline(iso) {
  const d = new Date(iso);
  const now = new Date();
  const days = Math.round((d - now) / 86400000);
  if (d < now) return "Overdue";
  if (days === 0) return "Today";
  if (days < 7) return d.toLocaleDateString([], { weekday: "long" });
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

// Map a deadline to an urgency tier. Each tier names a real token color so the
// styling pulls from _design_tokens.html, never a hardcoded hex.
//   red (error)     — overdue or due within 2 days
//   yellow (tertiary) — due within the week
//   blue (secondary)  — further out
function urgencyTier(iso) {
  const days = (new Date(iso) - new Date()) / 86400000;
  if (days <= 2) {
    return { color: "error", icon: "warning" };
  }
  if (days <= 7) {
    return { color: "tertiary", icon: "schedule" };
  }
  return { color: "secondary", icon: "event" };
}

// Minimal HTML escaping for user-supplied titles injected via innerHTML.
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str == null ? "" : String(str);
  return div.innerHTML;
}

// ---- Rendering ----------------------------------------------------------

function activeCard(o) {
  const { color, icon } = urgencyTier(o.deadline);
  const deadlineLabel = formatDeadline(o.deadline);
  // "Overdue" reads better alone than "Due Overdue".
  const badgeText = deadlineLabel === "Overdue" ? "Overdue" : `Due ${deadlineLabel}`;
  const firstStep = o.first_step
    ? `
      <div class="mt-4 bg-surface-container-lowest/50 rounded-lg p-3 border border-outline-variant/20 flex items-center gap-3">
        <div class="w-6 h-6 rounded-full border-2 border-outline-variant flex items-center justify-center shrink-0">
          <div class="w-2 h-2 rounded-full bg-outline-variant/50"></div>
        </div>
        <span class="font-body-md text-body-md text-on-surface-variant">${escapeHtml(o.first_step)}</span>
      </div>`
    : "";
  return `
    <article class="relative overflow-hidden rounded-xl p-5 bg-surface-glass/40 backdrop-blur-lg border-t-2 border-l-2 border-${color} border-b border-r border-white/10 shadow-[0_20px_40px_rgba(0,0,0,0.6)] transition-colors duration-300 hover:bg-surface-variant/10">
      <div class="absolute bottom-0 left-0 w-full h-1 bg-${color}"></div>
      <div class="flex justify-between items-start mb-3">
        <h2 class="font-headline-sm text-headline-sm text-on-surface pr-4">${escapeHtml(o.title)}</h2>
        <span class="material-symbols-outlined text-${color}" style="font-variation-settings: 'FILL' 1;">${icon}</span>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <div class="bg-${color}/20 text-${color} px-3 py-1 rounded-md font-label-sm text-label-sm uppercase flex items-center gap-1.5 border border-${color}/30">
          <span class="material-symbols-outlined text-[14px]">schedule</span>
          ${escapeHtml(badgeText)}
        </div>
      </div>
      ${firstStep}
    </article>`;
}

function completedCard(o) {
  return `
    <article class="bg-surface-container-lowest border border-outline-variant/30 rounded-xl p-4 opacity-50 flex items-center gap-4">
      <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center border border-primary/30 shrink-0">
        <span class="material-symbols-outlined text-primary text-[18px]" style="font-variation-settings: 'FILL' 1;">check</span>
      </div>
      <div>
        <h4 class="font-body-lg text-body-lg text-on-surface-variant line-through decoration-outline-variant/50">${escapeHtml(o.title)}</h4>
        <span class="font-label-sm text-label-sm text-outline-variant">Completed</span>
      </div>
    </article>`;
}

function render(items) {
  activeError.hidden = true;

  const pending = items.filter((o) => o.status === "pending");
  const done = items.filter((o) => o.status === "done");

  // Urgency order: soonest (and overdue) deadlines first.
  pending.sort((a, b) => new Date(a.deadline) - new Date(b.deadline));

  if (pending.length === 0) {
    activeList.innerHTML = "";
    activeEmpty.hidden = false;
  } else {
    activeEmpty.hidden = true;
    activeList.innerHTML = pending.map(activeCard).join("");
  }

  if (done.length === 0) {
    completedSection.hidden = true;
    completedList.innerHTML = "";
  } else {
    completedSection.hidden = false;
    completedList.innerHTML = done.map(completedCard).join("");
  }
}

async function loadObligations() {
  try {
    const res = await fetch("/api/obligations");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    render(await res.json());
  } catch (err) {
    activeList.innerHTML = "";
    activeEmpty.hidden = true;
    activeError.textContent = "Couldn't load obligations. Is the server running?";
    activeError.hidden = false;
  }
}

// ---- Capture ------------------------------------------------------------

function showFeedback(message, isError) {
  captureFeedback.textContent = message;
  captureFeedback.className =
    "mt-2 font-label-sm text-label-sm px-2 " +
    (isError ? "text-error" : "text-on-surface-variant");
  captureFeedback.hidden = false;
}

captureForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = captureInput.value.trim();
  if (!text) {
    showFeedback("Type something to capture.", true);
    return;
  }

  captureSubmit.disabled = true;
  showFeedback("Capturing…", false);
  try {
    const res = await fetch("/api/capture", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body.description || `HTTP ${res.status}`);
    }
    // capture() may classify the text as a goal or commitment instead; the
    // summary tells the user exactly what was created.
    showFeedback(body.summary || "Captured.", false);
    captureInput.value = "";
    // Refresh so a new obligation shows up immediately (and in urgency order).
    await loadObligations();
  } catch (err) {
    showFeedback(`Couldn't capture that: ${err.message}`, true);
  } finally {
    captureSubmit.disabled = false;
  }
});

// ---- Init ---------------------------------------------------------------

loadObligations();
