// DayQuest — Sanctuary home screen.
// Talks to the existing /api endpoints; no framework, no build step.
// Right Now + Done/Push are restored from the previous frontend, adapted to the
// new markup. The 6-tile grid pulls live data for the tiles that have a backing
// endpoint (Obligations, Goals, Calendar); the rest are static for now.

// ---- Right Now ----------------------------------------------------------

const rnContent = document.getElementById("rn-content");
const rnEmpty = document.getElementById("rn-empty");
const rnTitle = document.getElementById("rn-title");
const rnFirstStep = document.getElementById("rn-first-step");
const rnError = document.getElementById("rn-error");
const doneBtn = document.getElementById("done-btn");
const pushBtn = document.getElementById("push-btn");

// The block currently shown in "Right Now" (null when nothing is scheduled).
let currentBlock = null;

// Render whatever the API hands us as the current block (or null).
function renderRightNow(block) {
  currentBlock = block;
  rnError.hidden = true;

  if (!block) {
    rnContent.hidden = true;
    rnEmpty.hidden = false;
    return;
  }

  rnEmpty.hidden = true;
  rnContent.hidden = false;

  rnTitle.textContent = block.title || "Untitled";

  if (block.first_step) {
    rnFirstStep.textContent = block.first_step;
    rnFirstStep.hidden = false;
  } else {
    rnFirstStep.hidden = true;
  }
}

function showActionError(message) {
  rnError.textContent = message;
  rnError.hidden = false;
}

async function fetchRightNow() {
  try {
    const res = await fetch("/api/schedule/right-now");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const block = await res.json();
    renderRightNow(block);
  } catch (err) {
    showActionError("Couldn't reach the scheduler. Is the server running?");
  }
}

// Done / Push both return the *new* right-now block, so we render straight
// from their response — no extra fetch needed.
async function actOnCurrentBlock(action) {
  if (!currentBlock) return;
  rnError.hidden = true;
  try {
    const res = await fetch(`/api/schedule/${currentBlock.id}/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const nextBlock = await res.json();
    renderRightNow(nextBlock);
    // Acting on a block can shift deadlines/pace, so refresh the data tiles.
    loadTiles();
  } catch (err) {
    showActionError(`Couldn't ${action} this task. Try again.`);
  }
}

doneBtn.addEventListener("click", () => actOnCurrentBlock("done"));
pushBtn.addEventListener("click", () => actOnCurrentBlock("push"));

// ---- Formatting helpers -------------------------------------------------

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// "17:00:00" / "17:00" -> "5:00 PM"
function formatClock(timeStr) {
  if (!timeStr) return "";
  const [h, m] = timeStr.split(":");
  const d = new Date();
  d.setHours(Number(h), Number(m), 0, 0);
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

// ISO datetime -> "Thu" / "Jun 23"
function formatDeadline(iso) {
  const d = new Date(iso);
  const now = new Date();
  const days = Math.round((d - now) / 86400000);
  if (days >= 0 && days < 7) {
    return d.toLocaleDateString([], { weekday: "long" });
  }
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

// ---- OBLIGATIONS tile ---------------------------------------------------

async function loadObligations() {
  const summaryEl = document.getElementById("obl-summary");
  const nextEl = document.getElementById("obl-next");
  try {
    const res = await fetch("/api/obligations");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const items = await res.json();

    const now = new Date();
    const pending = items.filter((o) => o.status === "pending");
    const overdue = pending.filter((o) => new Date(o.deadline) < now);

    if (pending.length === 0) {
      summaryEl.textContent = "All caught up";
      nextEl.textContent = "";
      return;
    }

    summaryEl.textContent = overdue.length
      ? `${overdue.length} overdue`
      : `${pending.length} open`;

    // Soonest deadline first.
    const next = [...pending].sort(
      (a, b) => new Date(a.deadline) - new Date(b.deadline)
    )[0];
    nextEl.textContent = `${next.title} — Due ${formatDeadline(next.deadline)}`;
  } catch (err) {
    summaryEl.textContent = "Couldn't load obligations";
    nextEl.textContent = "";
  }
}

// ---- GOALS tile ---------------------------------------------------------

// pace_status() returns on_pace | behind | ahead.
const PACE = {
  on_pace: { label: "On Pace", color: "#2dd4bf" },
  ahead: { label: "Ahead", color: "#2dd4bf" },
  behind: { label: "Falling Behind", color: "#ffb4ab" },
};

async function loadGoals() {
  const listEl = document.getElementById("goals-list");
  try {
    const res = await fetch("/api/goals");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const goals = (await res.json()).filter((g) => g.status === "active");

    if (goals.length === 0) {
      listEl.innerHTML =
        '<div class="font-label-sm text-label-sm text-on-surface-variant">No active goals</div>';
      return;
    }

    listEl.innerHTML = goals
      .slice(0, 3)
      .map((g) => {
        const meta = PACE[g.pace] || PACE.on_pace;
        const total = g.estimated_total_effort_minutes || 1;
        const pct = Math.max(
          0,
          Math.min(100, Math.round((g.time_logged_minutes / total) * 100))
        );
        return `
        <div>
          <div class="flex items-center justify-between text-[10px] uppercase text-on-surface-variant">
            <span class="truncate pr-2">${escapeHtml(g.title)}</span>
            <span style="color:${meta.color}">${meta.label}</span>
          </div>
          <div class="w-full h-1 bg-surface-container-high rounded-full overflow-hidden mt-1">
            <div class="h-full" style="width:${pct}%;background:${meta.color}"></div>
          </div>
        </div>`;
      })
      .join("");
  } catch (err) {
    listEl.innerHTML =
      '<div class="font-label-sm text-label-sm text-error">Couldn\'t load goals</div>';
  }
}

// ---- CALENDAR tile ------------------------------------------------------

async function loadCalendar() {
  const listEl = document.getElementById("cal-list");
  try {
    const res = await fetch("/api/commitments");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const items = await res.json();

    if (items.length === 0) {
      listEl.innerHTML =
        '<div class="font-label-sm text-label-sm text-on-surface-variant">No fixed commitments</div>';
      return;
    }

    listEl.innerHTML = items
      .slice(0, 4)
      .map((c) => {
        const when = c.recurring
          ? DAY_NAMES[c.day_of_week] || "?"
          : c.specific_date || "";
        const time = formatClock(c.start_time);
        return `
        <div class="font-label-sm text-label-sm text-on-surface-variant truncate">
          <span class="text-[#fb7185] mr-2">•</span>${escapeHtml(c.title)} — ${when} ${time}
        </div>`;
      })
      .join("");
  } catch (err) {
    listEl.innerHTML =
      '<div class="font-label-sm text-label-sm text-error">Couldn\'t load calendar</div>';
  }
}

// Minimal HTML escaping for user-supplied titles injected via innerHTML.
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str == null ? "" : String(str);
  return div.innerHTML;
}

// ---- Init ---------------------------------------------------------------

function loadTiles() {
  loadObligations();
  loadGoals();
  loadCalendar();
}

fetchRightNow();
loadTiles();
