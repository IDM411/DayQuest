# Screen Migration Backlog

> **Read this first** at the start of any session that touches screen migration —
> alongside `design-reference/DESIGN.md` (the design system, now reconciled to match
> shipped code) and `DayQuest_PRD.md` (product intent).

## Foundation (done)

The shared frontend foundation is in place — future screens build on it, they don't
re-implement it:

- **`design-reference/DESIGN.md`** — single source of truth for tokens (colors,
  spacing, radius, typography). Reconciled so the spec matches the code: canonical
  background `#0d0b14`, tile radius `1rem`/16px (`rounded-2xl`), canonical teal
  `#2dd4bf`, plus promoted tokens `surface-glass` (#1a1625), `accent-goal` (#2dd4bf),
  `accent-calendar` (#fb7185).
- **`app/templates/_design_tokens.html`** — the `tailwind.config` + global `<style>`
  (`.glass-panel`, `.tile`/`::before`, `.tile-icon`, `.mascot-float`, `@keyframes
  breathe`, `.gradient-btn`). Included in `<head>`. Tokens live here in exactly one
  place; values match the reconciled DESIGN.md.
- **`app/templates/base.html`** — the page shell: `<head>` (fonts + tokens include),
  the **canonical top bar** (wordmark, local mascot avatar, level, date/time,
  streak/trophy/notification — **no text nav links**), the FAB, and the ambient-glow
  background layer. Jinja blocks: `title`, `head_extra`, `topbar`, `content`, `fab`,
  `background`, `scripts`.
- **`app/templates/index.html`** — the migrated home screen; reference implementation
  for how a screen extends `base.html` (provides only `content` + `scripts`).
- **`app/templates/obligations.html`** + **`app/static/obligations.js`** — migrated
  Obligations Vault (route `/obligations`). Reference implementation for a **sub-page**:
  `topbar` override (back-arrow + title), suppressed `fab`, live list from
  `/api/obligations` sorted by urgency, inline capture wired to `/api/capture`.
  Linked from the home OBLIGATIONS tile.

A new screen = `{% extends "base.html" %}` + a `content` block + endpoint wiring.

## Backlog (5 remaining reference screens)

> ✅ **Migrated:** `obligations.html` → `app/templates/obligations.html` (done).

Ordered by **ascending backend effort** — wire-able-now screens first, because they
are cheapest to land on `base.html` and prove the foundation before the harder ones.

| # | Screen (`design-reference/…`) | Backend readiness | What it needs |
|---|---|---|---|
| ~~1~~ | ~~`obligations.html`~~ | ✅ **MIGRATED** | Done — `/obligations`, see `app/templates/obligations.html` + `app/static/obligations.js`. |
| 2 | `calendar.html` | ✅ Live (commitments) | `/api/commitments` maps directly onto the week grid (`day_of_week` → column, `start_time`/`end_time` → position/height, `title` → label). Later: overlay `ScheduledBlock` data (needs a list-by-range endpoint) and week navigation. Grid is currently fixed Mon–Sun / 8 AM–8 PM. |
| 3 | `today's_path.html` | 🟡 Small backend add | Data exists in `ScheduledBlock` + the scheduler, but there's no "list today's blocks" GET endpoint. Add one, then wire the timeline (completed / active-NOW / upcoming items). |
| 4 | `archive_vault.html` | 🟡 Medium backend add | `Goal.status` includes `done`/`abandoned` and `Obligation.status` includes `done`, so the Completed/Abandoned sections are partially reachable by filtering existing endpoints. **Missing:** completion/abandonment **timestamp** columns (the per-card dates can't bind) and a **reason/note** field (abandonment notes are unbacked). Ideally add a dedicated archive feed endpoint. |
| 5 | `deep_focus.html` | 🔴 New subsystem | No focus-session / timer backend exists at all. Needs a focus-session model + endpoints (start/pause/complete, elapsed time) before it's more than static. |
| 6 | `stats.html` | 🔴 Most new backend | Needs gamification (XP / level / streak) **and** stats aggregation — none of which exists. Every number is currently hardcoded. Also fix `#00c4b4` → canonical `#2dd4bf` on migration. |

## Cross-cutting cleanup checklist (apply to EVERY screen at migration time)

The reference screens were generated across separate Stitch sessions and drifted.
When migrating any screen, do all of the following so it conforms to the foundation:

- [ ] **Extend `base.html`** — `{% extends "base.html" %}`; put page markup in the
      `content` block, page JS in `scripts`.
- [ ] **Delete the per-file `tailwind.config` `<script>` and global `<style>`** — these
      come from `_design_tokens.html` via the base shell. Do not re-declare tokens.
- [ ] **Drop the duplicated `<link>`** — every reference screen imports the Material
      Symbols stylesheet twice. Fonts come from `base.html`.
- [ ] **Use the canonical top bar** — either inherit it (default `topbar` block) or
      provide a *deliberate* `topbar` override for genuinely different screens (e.g.
      the focus overlay, or a back-arrow detail view). Do not paste a new bespoke bar.
      The references currently ship 5+ different top bars.
- [ ] **Fix stale tokens** — references hardcode `surface-container-lowest: "#0f0d14"`;
      the reconciled value is `#0d0b14`. Inheriting `_design_tokens.html` fixes this.
- [ ] **Collapse off-token accent colors onto real tokens.** Known offenders:
  - `#00c4b4` (stats teal) and `#00b8d4` (archive teal) → canonical `accent-goal`
    `#2dd4bf`.
  - `#ffab00` (archive amber) → a real token (e.g. `tertiary` `#dbc839`, or add one).
  - Inline token-value hexes (e.g. calendar's `#3131c0`/`#cebdff`/`#dbc839`) → use the
    named utility classes instead of raw hex.
- [ ] **Normalize the card style** to the canonical `.tile` / `.glass-panel`
      (`blur(16px)`, radius `1rem`/16px, 2px top/left + 1px bottom/right border).
      References drift to `blur(10px)`/`blur(40px)` and 0.5rem/0.75rem radii.
- [ ] **Use the shared `.gradient-btn`** for the FAB / primary buttons rather than the
      per-screen inline gradients (several different ones exist).
- [ ] **No sidebar or top text-nav links** — the tile grid is the only navigation.
      `today's_path.html` and `stats.html` reintroduce a sidebar; `today's_path.html`
      also adds a bottom nav. Remove these on migration.
- [ ] **Replace ephemeral remote mascot URLs** (`lh3.googleusercontent.com/aida…`
      hotlinks) with a local asset, and watch for the baked-in-white-background mascot
      raster (the `…/aida/AP1WRLtp…` image used by home's floating mascot and
      `deep_focus.html`'s 200px hero). Home replaced these with a local
      `mascot-avatar.png` + an inline SVG ghost.

## Notes / out of scope

- `home.html` is the original reference for the now-migrated `index.html`; no further
  migration needed.
- Gamification (XP, level, streak) is **static placeholder** everywhere it appears
  (home top bar + XP bar, stats) — there is no backend for it yet. Don't present it as
  real until that backend exists.
- The headline `text-shadow` rule in DESIGN.md is a **future enhancement**, not yet
  applied on any screen.
