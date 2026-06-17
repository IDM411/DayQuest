// DayQuest — Right Now view + secondary add forms.
// Talks to the existing /api endpoints; no framework, no build step.

const taskEl = document.getElementById("rn-task");
const emptyEl = document.getElementById("rn-empty");
const titleEl = document.getElementById("rn-title");
const firstStepEl = document.getElementById("rn-first-step");
const timeEl = document.getElementById("rn-time");
const errorEl = document.getElementById("rn-error");
const doneBtn = document.getElementById("done-btn");
const pushBtn = document.getElementById("push-btn");

// The block currently shown in "Right Now" (null when nothing is scheduled).
let currentBlock = null;

function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// Render whatever the API hands us as the current block (or null).
function renderRightNow(block) {
  currentBlock = block;
  errorEl.hidden = true;

  if (!block) {
    taskEl.hidden = true;
    emptyEl.hidden = false;
    return;
  }

  emptyEl.hidden = true;
  taskEl.hidden = false;

  titleEl.textContent = block.title || "Untitled";

  if (block.first_step) {
    firstStepEl.textContent = block.first_step;
    firstStepEl.hidden = false;
  } else {
    firstStepEl.hidden = true;
  }

  if (block.start_time && block.end_time) {
    timeEl.textContent = `${formatTime(block.start_time)} – ${formatTime(block.end_time)}`;
    timeEl.hidden = false;
  } else {
    timeEl.hidden = true;
  }
}

function showActionError(message) {
  errorEl.textContent = message;
  errorEl.hidden = false;
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
  errorEl.hidden = true;
  try {
    const res = await fetch(`/api/schedule/${currentBlock.id}/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const nextBlock = await res.json();
    renderRightNow(nextBlock);
  } catch (err) {
    showActionError(`Couldn't ${action} this task. Try again.`);
  }
}

doneBtn.addEventListener("click", () => actOnCurrentBlock("done"));
pushBtn.addEventListener("click", () => actOnCurrentBlock("push"));

// ---- Secondary add forms ------------------------------------------------

function showFormMsg(form, text, isError) {
  const msg = form.querySelector(".form-msg");
  msg.textContent = text;
  msg.classList.toggle("error", Boolean(isError));
  msg.hidden = false;
}

async function submitJson(form, url, payload, successText) {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    form.reset();
    showFormMsg(form, successText, false);
    // Adding anything re-runs the scheduler server-side, so refresh the view.
    fetchRightNow();
  } catch (err) {
    showFormMsg(form, "Something went wrong. Check the fields and try again.", true);
  }
}

const commitmentForm = document.getElementById("commitment-form");
commitmentForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const data = new FormData(commitmentForm);
  submitJson(
    commitmentForm,
    "/api/commitments",
    {
      title: data.get("title"),
      recurring: true,
      day_of_week: Number(data.get("day_of_week")),
      start_time: data.get("start_time"),
      end_time: data.get("end_time"),
    },
    "Commitment added."
  );
});

const obligationForm = document.getElementById("obligation-form");
obligationForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const data = new FormData(obligationForm);
  submitJson(
    obligationForm,
    "/api/obligations",
    {
      title: data.get("title"),
      first_step: data.get("first_step"),
      deadline: data.get("deadline"),
      estimated_effort_minutes: Number(data.get("estimated_effort_minutes")),
    },
    "Obligation added."
  );
});

const goalForm = document.getElementById("goal-form");
goalForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const data = new FormData(goalForm);
  // Effort is entered in hours (natural for "how much work is this?") and
  // converted to the minutes the API expects.
  const hours = Number(data.get("estimated_total_effort_hours"));
  submitJson(
    goalForm,
    "/api/goals",
    {
      title: data.get("title"),
      estimated_total_effort_minutes: Math.round(hours * 60),
      soft_target_date: data.get("soft_target_date"),
    },
    "Goal added."
  );
});

// ---- Primary free-text capture ------------------------------------------

const captureForm = document.getElementById("capture-form");
const captureInput = document.getElementById("capture-input");
const captureMsg = document.getElementById("capture-msg");
const captureBtn = captureForm.querySelector("button");

captureForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = captureInput.value.trim();
  if (!text) return;

  captureBtn.disabled = true;
  captureMsg.classList.remove("error");
  captureMsg.textContent = "Reading that…";
  captureMsg.hidden = false;

  try {
    const res = await fetch("/api/capture", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    captureInput.value = "";
    captureMsg.textContent = data.summary || "Added.";
    captureMsg.classList.remove("error");
    // The capture re-runs the scheduler; refresh in case it now outranks.
    fetchRightNow();
  } catch (err) {
    captureMsg.textContent = "Couldn't parse that. Try the manual forms below.";
    captureMsg.classList.add("error");
  } finally {
    captureBtn.disabled = false;
  }
});

// Initial load.
fetchRightNow();
