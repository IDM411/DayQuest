# DayQuest — Product Requirements Document
*(working title — rename freely)*

## 1. Problem Statement

The user experiences a specific kind of paralysis: too many wants and too many needs compete for the same mental slot, so picking anything feels like abandoning everything else. The result is "I feel like doing everything, yet I do nothing." Starting feels disproportionately hard (studying "feels like torture") even though the actual work, once started, is rarely as bad as anticipated. The friction lives almost entirely in the *decision to start*, not in the work itself.

This tool exists to remove decision-making from the user's day-to-day, automate prioritization, and replace the dopamine loop currently only triggered by video games with one triggered by real, finished tasks.

## 2. Core Design Principle

**The system never asks the user to choose — it only declares.**

Every feature decision flows from this rule. No manual prioritization screens, no "what do you want to work on" prompts, no category pickers. The user's only job is to act on whatever the system currently shows them.

## 3. Goals

- Eliminate decision fatigue around "what do I work on right now."
- Treat real obligations (deadlines) and personal goals (open-ended ambitions) as first-class, both protected from being silently dropped.
- Make starting easy by shrinking every task to a literal first step.
- Capture new tasks/goals via free-form text with zero structured input.
- Notify proactively rather than requiring the user to check in.
- Run for close to $0/month using infrastructure the user already owns.

## 4. Non-Goals (for now)

- No manual scheduling UI or drag-and-drop calendar.
- No multi-user support or accounts — single user only.
- No gamification layer (XP, streaks, mascot) in the initial build — deferred to a later phase, architected so it can bolt on without a rewrite.
- No third-party calendar sync (Google Calendar, etc.) in V1.

## 5. Phased Roadmap

| Phase | Feature | Status |
|---|---|---|
| 1 | Fixed commitments + obligations + auto-scheduler + "Right Now" screen | **Build first** |
| 2 | Goals (effort-estimate-based, non-deadline) | Next |
| 3 | Natural language capture via LLM parsing | Next |
| 4 | Push notifications (ntfy.sh) | Next |
| 5 | Gamification layer — quests/XP/streaks/mascot companion | Deferred, documented below for architectural continuity |

## 6. User Stories (Phase 1)

- As the user, I want my gym and class times entered once so the scheduler never double-books me.
- As the user, I want every assignment/deadline entered with a tiny literal first step, not a vague title, so starting doesn't trigger avoidance.
- As the user, I want to open the app and see exactly one thing to do right now, not a list I have to evaluate.
- As the user, I want to push a task to later and have everything downstream shift automatically, with no manual replanning.
- As the user, I want to mark something done and have my actual time spent logged automatically.

## 7. Functional Requirements (Phase 1)

**Fixed Commitments** — recurring or one-off blocks (gym, classes) that the scheduler treats as immovable. Entered once, rarely edited.

**Obligations** — deadline-bound items (assignments, applications). Fields: title, first step, deadline, estimated effort, source.

**Auto-Scheduler** — fills every open gap around fixed commitments using an urgency score (see Section 9). Re-runs automatically whenever anything changes — no manual trigger.

**"Right Now" Screen** — the entire home view. Shows the single highest-urgency task and its first step. Nothing else, by design.

**Push / Cascade Reschedule** — tapping "push" on the current block shifts it later and cascades every subsequent block forward. No manual time-editing.

**Mark Done** — logs actual time spent against the task, feeding future estimate corrections (Phase 2+).

## 8. Data Model (Phase 1)

```
FixedCommitment
  id, title, day_of_week (or specific_date), start_time, end_time, recurring (bool)

Obligation
  id, title, first_step, deadline (datetime), estimated_effort_minutes,
  time_logged_minutes, status (pending/done), source

ScheduledBlock
  id, ref_type (fixed/obligation), ref_id, start_time, end_time,
  status (planned/active/done/pushed)
```

## 9. Scheduling Algorithm

1. Lock all fixed commitments first — these never move automatically.
2. For every open obligation, compute:
   `urgency = remaining_effort_minutes / minutes_until_deadline`
3. Fill open slots chronologically with whichever pending item currently has the highest urgency score.
4. Tie-break order: closer deadline wins, then larger remaining effort.
5. On "push": shift the pushed block forward, cascade all subsequent blocks, re-run step 3 for the remainder of the day.
6. On overload (total required time > available time): the lowest-urgency item is silently bumped to the next available slot — the user is never asked to choose what slips. A passive notification informs them after the fact (see Phase 4).

## 10. Future Phases (documented now to avoid rework later)

### 10.1 Goals (Phase 2)
Non-deadline-driven ambitions. Fields: title, estimated total effort, soft target date. The scheduler back-calculates a session cadence (e.g., two 45-minute blocks/week) and competes in the same urgency formula as obligations, using the soft date in place of a hard deadline. Logged time per session feeds a velocity calculation that quietly tightens or loosens the cadence over time — the estimate self-corrects rather than staying fixed.

### 10.2 Natural Language Capture (Phase 3)
A single always-visible "+" text field. Raw input (e.g. "kubernetes sometime this month, maybe 5 hrs") is sent to Claude Haiku via the Anthropic API with a structured-output prompt extracting: title, deadline (nullable), effort estimate (nullable), and obligation-vs-goal classification (presence of a hard deadline = obligation; absence = goal with a default soft window). Missing effort estimates fall back to a heuristic default, later corrected by logged time. The scheduler re-runs immediately in the background; "Right Now" updates silently if the new item outranks the current task.

### 10.3 Notifications (Phase 4)
Via ntfy.sh (free, no signup, works identically on phone and laptop):
- **Change alert** — fires whenever "Right Now" changes.
- **Daily digest** — informational pace status ("on pace" / "Goal X falling behind") with no action required, consistent with the "never ask the user to choose" rule.

### 10.4 Gamification Layer (Phase 5, deferred)
Quest/XP/streak system and a mascot companion reflecting real progress (not its own engagement loop). Reward logic strictly tied to completed real tasks, never to app-opens or session-extending, to avoid creating a second avoidance loop. Architecture: separate Quest/XP tables that subscribe to the same "task completed" event as the core scheduler, so this phase can be added without touching Phase 1–4 logic.

## 11. Tech Stack & Hosting

- **Backend:** Flask + SQLite
- **Frontend:** single HTML/JS page served directly by Flask (no separate build step)
- **NLP parsing:** Claude Haiku via existing Anthropic API key
- **Notifications:** ntfy.sh free public instance
- **Hosting:** home lab (Proxmox container) + Cloudflare Tunnel for remote/phone access without exposing a home IP

## 12. Cost Estimate

Near $0/month beyond existing electricity and fractions of a cent per Claude Haiku parsing call.

**Known risk:** uptime is tied to the home lab and home internet connection — if either drops, "Right Now" and notifications go dark. If guaranteed uptime becomes important later, Oracle Cloud's Always Free tier is a genuinely free fallback, at the cost of moving off personal hardware.

## 13. Open Questions / Risks

- What happens if the user never taps "done" on anything — does the system stall, or does it need an inactivity nudge?
- NLP parsing edge cases: fully ambiguous input with no time/effort signal at all.
- iOS has historically had weaker push notification support outside installed apps — confirm ntfy.sh's iOS behavior is acceptable before relying on it daily.
- Home lab uptime as a single point of failure (see Section 12).

## 14. Success Metrics

- Fewer missed/late obligations week over week.
- Increase in actual completed goal-sessions vs. baseline (currently near zero, per stated pattern of unfinished projects).
- Subjective: time between opening the app and starting the shown task trends toward seconds, not minutes of deliberation.
