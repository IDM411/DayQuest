# Dashboard Visual Exploration — Design Spec

## Context

A standalone visual exploration of a "main dashboard" concept for DayQuest — a calming productivity feel for overwhelmed students. This is explicitly **not** the real DayQuest app: it does not connect to the Flask backend, does not represent the PRD's Phase 1 "Right Now" screen, and does not change the PRD's direction (single-task minimalism, no gamification yet, Flask + vanilla JS, no build step). It's a separate, isolated prototype to explore a fuller dashboard look-and-feel, built with React + Tailwind, with static placeholder data.

## Goals

- Build real, runnable React components previewable locally via a dev server.
- Visual direction: dark mode, deep purple/indigo/lavender palette, glassmorphism cards, gentle glowing accents, fully rounded corners, generous whitespace — "cozy digital sanctuary at night," not a corporate dashboard or game HUD.
- Static placeholder data only — no backend, no API calls.

## Non-Goals

- No connection to the Flask backend or its API.
- No changes to the PRD, the Phase 1 "Right Now" spec, or the existing Python codebase.
- No real data persistence — all values are hardcoded mocks.

## Tech Setup & Structure

Self-contained Vite + React + Tailwind project in its own top-level folder, isolated from the rest of the repo:

```
dashboard-concept/
  package.json
  index.html
  tailwind.config.js     # custom purple/indigo/lavender palette, glassmorphism utilities
  src/
    main.jsx
    App.jsx
    data/placeholder.js      # mock goals, today's focus, progress values
    components/
      Sidebar.jsx
      GreetingHeader.jsx
      ActiveGoalsPanel.jsx
      GoalCard.jsx
      TodaysFocusCard.jsx
      ProgressSummary.jsx
      RadialProgress.jsx       # reusable custom SVG progress ring
      NestVisualization.jsx
      QuickAddButton.jsx
```

Runs via `npm install && npm run dev`. Icons via `lucide-react`. No charting library — progress visuals are hand-built SVG.

## Component Breakdown

- **Sidebar** — fixed left rail, lucide-react icons + labels (Dashboard, Goals, Focus, Settings), active item gets a soft glow/highlight.
- **GreetingHeader** — "Good evening, Alex" + subtitle (date/time-of-day), minimal.
- **ActiveGoalsPanel** — renders 3-4 `GoalCard`s, each a glassmorphic card (translucent blurred background, `rounded-2xl`+, soft border glow) with title + a slim rounded progress bar.
- **TodaysFocusCard** — single highlighted card, visually the largest/brightest element after the Nest, showing one priority task + its first step.
- **ProgressSummary** — one or two `RadialProgress` rings (custom SVG, gradient stroke, soft glow filter) showing overall completion. No raw numbers framed as stress indicators.
- **NestVisualization** — central organic SVG/CSS blob with layered radial gradients + blur; glow intensity/size scales with a placeholder "completion" value. Styled as ambient art, not a game meter.
- **QuickAddButton** — pill-shaped button with soft purple glow.

All data comes from `data/placeholder.js` — static, hardcoded, no API calls.

## Visual System

- **Palette**: near-black indigo background, card surfaces as translucent indigo/purple over a deep purple base with `backdrop-blur`, accent gradient violet → lavender → soft pink for glows/progress fills. No red/green stress colors anywhere.
- **Typography**: clean modern sans (Inter or Tailwind's default system sans), generous line-height, soft off-white text rather than pure white.
- **Shape language**: `rounded-2xl`/`rounded-3xl` everywhere, no sharp corners; soft glow via shadow/blur on active/focal elements.
- **Spacing**: wide gaps and generous padding; centered, max-width-constrained content so the layout never feels dense.
- **Motion**: subtle only — gentle hover scale/glow transitions, slow Nest pulse animation. Nothing fast or game-like.

## Testing

None — this is a static visual prototype with no logic to test. Verification is visual: run the dev server and review in a browser.

## Open Questions

None outstanding — all resolved during design discussion.
