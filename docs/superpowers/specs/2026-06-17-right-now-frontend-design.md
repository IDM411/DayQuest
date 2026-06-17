# Right Now Frontend — Design Spec

## Context

Phase 1 backend (models, scheduler, API routes) is complete and tested. The PRD's Phase 1 also calls for a "Right Now" screen — the entire home view, showing only the single highest-urgency task — but no frontend exists yet. This spec covers building that screen, plus the data-entry forms needed to actually populate the system before Phase 3 (NLP capture) exists.

## Goals

- Build the "Right Now" home view per PRD section 7: one task, its first step, nothing else.
- Build a separate "Add" page for entering fixed commitments and obligations via structured forms (no NLP yet).
- Keep the stack as simple as the PRD specifies: Flask-served HTML/JS, no build step, no frontend framework.
- Visual styling (palette, type, spacing) is deferred to the `ui-ux-pro-max` skill at implementation time, applied within the structure/behavior defined here. Direction: minimal/calm.

## Non-Goals

- No NLP capture (Phase 3).
- No push notifications (Phase 4) — polling is the interim mechanism for staying current.
- No editing or deleting existing commitments/obligations — only add + view.
- No prompting the user for actual time spent on Done — stays zero-tap per the PRD's "never ask the user to choose" principle.

## Architecture & File Layout

Two new Flask page routes, separate from the existing `/api` blueprint:

- `GET /` — renders the Right Now view.
- `GET /add` — renders the entry-forms view.

Both are plain Jinja templates with no server-side data — all data is fetched client-side against the existing JSON API (`/api/commitments`, `/api/obligations`, `/api/schedule/*`).

```
app/
  views.py          # new blueprint: GET / and GET /add
  templates/
    index.html       # Right Now
    add.html          # entry forms
  static/
    style.css         # shared, minimal/calm theme (built via ui-ux-pro-max)
    app.js            # Right Now logic
    add.js            # forms logic
```

`views.py` registers as a second blueprint in `create_app()`, alongside the existing `api` blueprint. No changes to `routes.py`, `models.py`, or `scheduler.py`.

## Right Now Page (`index.html` + `app.js`)

- On load, and every 30s via `setInterval`: `GET /api/schedule/right-now`.
- If a block is returned: show its title, first step (obligations only), time range, and two buttons — **Push** and **Done**. One focal card, nothing else on the page, plus a small `+` link to `/add`.
- If `null`: calm idle message — "Nothing right now. You're clear." — styled distinctly from the active-task state so it's obviously not a bug.
- **Push**: `POST /api/schedule/<id>/push` with no body (backend default `DEFAULT_PUSH_MINUTES`) → re-render from the response. No prompt.
- **Done**: `POST /api/schedule/<id>/done` with empty body → re-render. No prompt for actual time spent (backend falls back to elapsed/estimated time).
- Re-render replaces only the card's content — no full page reload.

## Add Page (`add.html` + `add.js`)

Two forms, plus read-only lists for confirmation:

- **Fixed Commitment form**: title, recurring toggle (recurring → day-of-week picker; one-off → specific date picker), start time, end time. `POST /api/commitments`.
- **Obligation form**: title, first step, deadline (date+time), estimated effort (minutes), source (optional). `POST /api/obligations`.
- Below each form, a read-only list of existing commitments/obligations (`GET /api/commitments`, `GET /api/obligations`).
- On successful submit: clear the form, refresh the corresponding list, no full page reload.
- A `← Right Now` link back to the home view.

## Error Handling

- Right Now polling failures: keep showing the last known state, retry silently on the next interval. No error popups for transient network issues.
- Push/Done action failures (e.g. 400 from the API): small inline message under the card, not a JS `alert()`.
- Add-form submit failures: inline message near the form; form values are preserved, nothing is lost.

## Testing

- Add `pytest-playwright` as a new dev dependency — the first JS-adjacent tooling in an otherwise pure-Python project. Setup adds a `requirements-dev` entry and a `playwright install` step.
- Coverage:
  - Right Now: renders the active task when one exists; shows the idle message when `right-now` returns `null`; clicking **Push** updates the card; clicking **Done** advances to the next task (or idle state).
  - Add page: submitting the Fixed Commitment form adds it to its list; submitting the Obligation form adds it to its list; invalid/missing fields show the inline error instead of submitting.
- Tests run against a real instance of the Flask app in a real browser.

## Open Questions

None outstanding — all resolved during design discussion.
