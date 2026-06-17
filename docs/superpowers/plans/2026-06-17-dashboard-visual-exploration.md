# Dashboard Visual Exploration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, runnable React + Tailwind dashboard prototype exploring a "cozy digital sanctuary" visual direction for DayQuest, using static placeholder data only.

**Architecture:** A self-contained Vite + React project at `dashboard-concept/` (sibling to the Flask app, no shared code or imports). Each visual element is its own component, assembled incrementally into `App.jsx` task by task, ending in a final layout-assembly task that arranges everything into the spec's grid.

**Tech Stack:** Vite, React 18, Tailwind CSS v3.4 (pinned — v4's setup differs and isn't what these steps target), `lucide-react` for icons. No backend, no API, no test framework — see Global Constraints.

## Global Constraints

- Project lives entirely inside the new top-level folder `dashboard-concept/`. No imports from, or references to, the Flask `app/` directory.
- No backend, no API calls. All data comes from `dashboard-concept/src/data/placeholder.js`.
- Tailwind CSS pinned to `^3.4.0` specifically so `npx tailwindcss init -p` and the classic `postcss.config.js` flow apply as written below.
- Visual system (from spec): dark mode only, background `#0d0b1a`, glassmorphism cards (`rounded-3xl`, `border-white/10`, `bg-white/5`, `backdrop-blur-xl`), violet → lavender → pink accent gradient, no red/green colors, Inter font, generous spacing, slow/subtle motion only.
- No automated test framework exists for this prototype (per spec's Testing section — verification is visual). Each task's automated gate is `npm run build` succeeding with zero errors. Final human visual review in a browser happens after Task 12, outside this plan.

---

### Task 1: Scaffold Vite + React + Tailwind project

**Files:**
- Create: `dashboard-concept/` (Vite scaffold: `package.json`, `vite.config.js`, `index.html`, `src/main.jsx`, `src/App.jsx`, `src/index.css`, `public/vite.svg`, etc.)
- Create: `dashboard-concept/tailwind.config.js`
- Create: `dashboard-concept/postcss.config.js`

**Interfaces:**
- Produces: a working Vite dev server and `npm run build` pipeline at `dashboard-concept/`, with Tailwind's content paths wired to scan `index.html` and `src/**/*.{js,jsx}`.

- [ ] **Step 1: Scaffold the Vite React app**

Run (from the repo root):
```bash
cd "C:/Projectsss/DayQuest"
npm create vite@latest dashboard-concept -- --template react
```
Expected: creates `dashboard-concept/` containing `package.json`, `vite.config.js`, `index.html`, `src/main.jsx`, `src/App.jsx`, `src/index.css`, `public/vite.svg`.

- [ ] **Step 2: Install base dependencies**

Run:
```bash
cd "C:/Projectsss/DayQuest/dashboard-concept"
npm install
```
Expected: `node_modules/` created, exit code 0, no errors.

- [ ] **Step 3: Install Tailwind CSS v3, PostCSS, Autoprefixer**

Run:
```bash
npm install -D tailwindcss@^3.4.0 postcss autoprefixer
```
Expected: three packages added under `devDependencies` in `package.json`.

- [ ] **Step 4: Initialize Tailwind config**

Run:
```bash
npx tailwindcss init -p
```
Expected: creates `tailwind.config.js` and `postcss.config.js` in `dashboard-concept/`.

- [ ] **Step 5: Configure Tailwind content paths**

Edit `dashboard-concept/tailwind.config.js` to:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

- [ ] **Step 6: Verify the dev server boots**

Run:
```bash
npm run dev -- --port 5174 &
SERVER_PID=$!
sleep 2
curl -s http://localhost:5174 | head -c 300
kill $SERVER_PID
```
Expected: the curl output contains `<div id="root">` (the Vite scaffold's root mount point), no connection error.

- [ ] **Step 7: Commit**

```bash
cd "C:/Projectsss/DayQuest"
git add dashboard-concept
git commit -m "Scaffold dashboard-concept: Vite + React + Tailwind"
```

---

### Task 2: Configure Tailwind theme and global styles

**Files:**
- Modify: `dashboard-concept/tailwind.config.js`
- Modify: `dashboard-concept/index.html`
- Modify: `dashboard-concept/src/index.css`

**Interfaces:**
- Produces: Tailwind theme extensions — `colors.midnight` (`#0d0b1a`), `boxShadow.glow` / `boxShadow['glow-sm']`, `fontFamily.sans` (Inter-first), `animation['pulse-slow']` + `keyframes.pulseSlow` — plus a global `.glass-card` utility class (via `@layer components`), usable by every later component.

- [ ] **Step 1: Extend the Tailwind theme**

Edit `dashboard-concept/tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        midnight: "#0d0b1a",
      },
      boxShadow: {
        glow: "0 0 50px rgba(196, 181, 253, 0.45)",
        "glow-sm": "0 0 20px rgba(167, 139, 250, 0.35)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulseSlow 6s ease-in-out infinite",
      },
      keyframes: {
        pulseSlow: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.6" },
          "50%": { transform: "scale(1.08)", opacity: "1" },
        },
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 2: Load the Inter font and update the page title**

Edit `dashboard-concept/index.html` — inside `<head>`, add the font links and change the title:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<title>DayQuest — Dashboard</title>
```
(Replace the existing `<title>` tag rather than adding a second one.)

- [ ] **Step 3: Replace global styles with Tailwind directives and base/component layers**

Replace the entire contents of `dashboard-concept/src/index.css` with:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-midnight text-violet-50/90 font-sans antialiased;
  }
}

@layer components {
  .glass-card {
    @apply rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-glow-sm;
  }
}
```

- [ ] **Step 4: Verify the build succeeds**

Run:
```bash
npm run build
```
Expected: exit code 0, output includes a generated `dist/assets/*.css` file, no PostCSS/Tailwind errors.

- [ ] **Step 5: Commit**

```bash
cd "C:/Projectsss/DayQuest"
git add dashboard-concept
git commit -m "Configure Tailwind theme (palette, glow, font, slow pulse) and global styles"
```

---

### Task 3: Placeholder data module

**Files:**
- Create: `dashboard-concept/src/data/placeholder.js`

**Interfaces:**
- Produces:
  - `greeting`: `{ name: string, timeOfDay: string }`
  - `goals`: `Array<{ id: number, title: string, progress: number }>` (progress is 0-100)
  - `todaysFocus`: `{ title: string, firstStep: string }`
  - `progressSummary`: `{ overallPercent: number, weeklyPercent: number }` (0-100)
  - `nestCompletion`: `number` (0-1)

- [ ] **Step 1: Create the placeholder data file**

Create `dashboard-concept/src/data/placeholder.js`:
```js
export const greeting = {
  name: "Alex",
  timeOfDay: "evening",
};

export const goals = [
  { id: 1, title: "Finish thesis literature review", progress: 62 },
  { id: 2, title: "Learn conversational Spanish", progress: 34 },
  { id: 3, title: "Run a 10k", progress: 80 },
  { id: 4, title: "Read 12 books this year", progress: 45 },
];

export const todaysFocus = {
  title: "Draft Chapter 3 outline",
  firstStep: "Open the doc and write three bullet points",
};

export const progressSummary = {
  overallPercent: 58,
  weeklyPercent: 72,
};

export const nestCompletion = 0.58;
```

- [ ] **Step 2: Verify the module loads and exports the expected shape**

Run (from `dashboard-concept/`):
```bash
node --input-type=module -e "
import { greeting, goals, todaysFocus, progressSummary, nestCompletion } from './src/data/placeholder.js';
console.log(greeting.name, goals.length, todaysFocus.title, progressSummary.overallPercent, nestCompletion);
"
```
Expected output: `Alex 4 Draft Chapter 3 outline 58 0.58`

- [ ] **Step 3: Commit**

```bash
cd "C:/Projectsss/DayQuest"
git add dashboard-concept/src/data/placeholder.js
git commit -m "Add placeholder data module for dashboard prototype"
```

---

### Task 4: RadialProgress component

**Files:**
- Create: `dashboard-concept/src/components/RadialProgress.jsx`
- Modify: `dashboard-concept/src/App.jsx`
- Delete: `dashboard-concept/src/App.css`

**Interfaces:**
- Consumes: `progressSummary` from `src/data/placeholder.js` (Task 3).
- Produces: `RadialProgress({ percent, size = 120, strokeWidth = 10, label })` default export — a circular SVG progress ring with a violet→lavender→pink gradient stroke and a soft glow.

- [ ] **Step 1: Create the RadialProgress component**

Create `dashboard-concept/src/components/RadialProgress.jsx`:
```jsx
import { useId } from "react";

export default function RadialProgress({ percent, size = 120, strokeWidth = 10, label }) {
  const id = useId();
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - percent / 100);

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={`grad-${id}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#8b5cf6" />
            <stop offset="50%" stopColor="#c4b5fd" />
            <stop offset="100%" stopColor="#f5d0fe" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#grad-${id})`}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-700 ease-out"
          style={{ filter: "drop-shadow(0 0 8px rgba(196,181,253,0.6))" }}
        />
      </svg>
      {label && <span className="text-sm text-violet-100/70">{label}</span>}
    </div>
  );
}
```

- [ ] **Step 2: Wire it into App.jsx and remove scaffold cruft**

Delete `dashboard-concept/src/App.css` (no longer used).

Replace the entire contents of `dashboard-concept/src/App.jsx` with:
```jsx
import RadialProgress from "./components/RadialProgress";
import { progressSummary } from "./data/placeholder";

export default function App() {
  return (
    <div className="min-h-screen bg-midnight p-8">
      <RadialProgress percent={progressSummary.overallPercent} label="Overall" />
    </div>
  );
}
```

- [ ] **Step 3: Verify the build succeeds**

Run:
```bash
npm run build
```
Expected: exit code 0, no errors.

- [ ] **Step 4: Commit**

```bash
cd "C:/Projectsss/DayQuest"
git add dashboard-concept
git commit -m "Add RadialProgress component"
```

---

### Task 5: Sidebar component

**Files:**
- Create: `dashboard-concept/src/components/Sidebar.jsx`
- Modify: `dashboard-concept/src/App.jsx`
- Modify: `dashboard-concept/package.json` (via `npm install`)

**Interfaces:**
- Produces: `Sidebar({ activeId = "dashboard" })` default export — fixed-width left nav rail with `lucide-react` icons, active item glow.

- [ ] **Step 1: Install lucide-react**

Run (from `dashboard-concept/`):
```bash
npm install lucide-react
```
Expected: added to `dependencies` in `package.json`.

- [ ] **Step 2: Create the Sidebar component**

Create `dashboard-concept/src/components/Sidebar.jsx`:
```jsx
import { LayoutDashboard, Target, Sparkles, Settings } from "lucide-react";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "goals", label: "Goals", icon: Target },
  { id: "focus", label: "Focus", icon: Sparkles },
  { id: "settings", label: "Settings", icon: Settings },
];

export default function Sidebar({ activeId = "dashboard" }) {
  return (
    <aside className="flex h-screen w-20 flex-col gap-2 border-r border-white/5 bg-white/[0.02] p-4 md:w-56">
      <div className="mb-6 hidden px-2 text-lg font-semibold text-violet-100 md:block">
        DayQuest
      </div>
      {navItems.map(({ id, label, icon: Icon }) => {
        const active = id === activeId;
        return (
          <button
            key={id}
            className={`flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm transition-all ${
              active
                ? "bg-violet-500/15 text-violet-100 shadow-glow-sm"
                : "text-violet-200/50 hover:bg-white/5 hover:text-violet-100"
            }`}
          >
            <Icon size={20} className={active ? "text-violet-300" : ""} />
            <span className="hidden md:inline">{label}</span>
          </button>
        );
      })}
    </aside>
  );
}
```

- [ ] **Step 3: Wire it into App.jsx**

Replace `dashboard-concept/src/App.jsx` with:
```jsx
import Sidebar from "./components/Sidebar";
import RadialProgress from "./components/RadialProgress";
import { progressSummary } from "./data/placeholder";

export default function App() {
  return (
    <div className="flex min-h-screen bg-midnight">
      <Sidebar activeId="dashboard" />
      <main className="flex-1 p-8">
        <RadialProgress percent={progressSummary.overallPercent} label="Overall" />
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Verify the build succeeds**

Run:
```bash
npm run build
```
Expected: exit code 0, no errors.

- [ ] **Step 5: Commit**

```bash
cd "C:/Projectsss/DayQuest"
git add dashboard-concept
git commit -m "Add Sidebar component"
```

---

### Task 6: GreetingHeader component

**Files:**
- Create: `dashboard-concept/src/components/GreetingHeader.jsx`
- Modify: `dashboard-concept/src/App.jsx`

**Interfaces:**
- Consumes: `greeting` from `src/data/placeholder.js` (Task 3).
- Produces: `GreetingHeader({ name, timeOfDay })` default export.

- [ ] **Step 1: Create the GreetingHeader component**

Create `dashboard-concept/src/components/GreetingHeader.jsx`:
```jsx
export default function GreetingHeader({ name, timeOfDay }) {
  return (
    <header className="mb-8">
      <h1 className="text-3xl font-semibold text-violet-50">
        Good {timeOfDay}, {name}
      </h1>
      <p className="mt-1 text-sm text-violet-200/50">
        Here's a quiet look at where things stand.
      </p>
    </header>
  );
}
```

- [ ] **Step 2: Wire it into App.jsx**

Replace `dashboard-concept/src/App.jsx` with:
```jsx
import Sidebar from "./components/Sidebar";
import GreetingHeader from "./components/GreetingHeader";
import RadialProgress from "./components/RadialProgress";
import { greeting, progressSummary } from "./data/placeholder";

export default function App() {
  return (
    <div className="flex min-h-screen bg-midnight">
      <Sidebar activeId="dashboard" />
      <main className="flex-1 p-8">
        <GreetingHeader name={greeting.name} timeOfDay={greeting.timeOfDay} />
        <RadialProgress percent={progressSummary.overallPercent} label="Overall" />
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Verify the build succeeds**

Run:
```bash
npm run build
```
Expected: exit code 0, no errors.

- [ ] **Step 4: Commit**

```bash
cd "C:/Projectsss/DayQuest"
git add dashboard-concept
git commit -m "Add GreetingHeader component"
```

---

### Task 7: GoalCard and ActiveGoalsPanel components

**Files:**
- Create: `dashboard-concept/src/components/GoalCard.jsx`
- Create: `dashboard-concept/src/components/ActiveGoalsPanel.jsx`
- Modify: `dashboard-concept/src/App.jsx`

**Interfaces:**
- Consumes: `goals` from `src/data/placeholder.js` (Task 3); `.glass-card` global class (Task 2).
- Produces: `GoalCard({ title, progress })` and `ActiveGoalsPanel({ goals })` default exports.

- [ ] **Step 1: Create the GoalCard component**

Create `dashboard-concept/src/components/GoalCard.jsx`:
```jsx
export default function GoalCard({ title, progress }) {
  return (
    <div className="glass-card p-5">
      <p className="text-sm font-medium text-violet-50/90">{title}</p>
      <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-white/5">
        <div
          className="h-full rounded-full bg-gradient-to-r from-violet-500 via-violet-300 to-fuchsia-200"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="mt-2 text-right text-xs text-violet-200/40">{progress}%</p>
    </div>
  );
}
```

- [ ] **Step 2: Create the ActiveGoalsPanel component**

Create `dashboard-concept/src/components/ActiveGoalsPanel.jsx`:
```jsx
import GoalCard from "./GoalCard";

export default function ActiveGoalsPanel({ goals }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-violet-200/40">
        Active Goals
      </h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {goals.map((goal) => (
          <GoalCard key={goal.id} title={goal.title} progress={goal.progress} />
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Wire it into App.jsx**

Replace `dashboard-concept/src/App.jsx` with:
```jsx
import Sidebar from "./components/Sidebar";
import GreetingHeader from "./components/GreetingHeader";
import ActiveGoalsPanel from "./components/ActiveGoalsPanel";
import RadialProgress from "./components/RadialProgress";
import { greeting, goals, progressSummary } from "./data/placeholder";

export default function App() {
  return (
    <div className="flex min-h-screen bg-midnight">
      <Sidebar activeId="dashboard" />
      <main className="flex-1 space-y-6 p-8">
        <GreetingHeader name={greeting.name} timeOfDay={greeting.timeOfDay} />
        <ActiveGoalsPanel goals={goals} />
        <RadialProgress percent={progressSummary.overallPercent} label="Overall" />
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Verify the build succeeds**

Run:
```bash
npm run build
```
Expected: exit code 0, no errors.

- [ ] **Step 5: Commit**

```bash
cd "C:/Projectsss/DayQuest"
git add dashboard-concept
git commit -m "Add GoalCard and ActiveGoalsPanel components"
```

---

### Task 8: TodaysFocusCard component

**Files:**
- Create: `dashboard-concept/src/components/TodaysFocusCard.jsx`
- Modify: `dashboard-concept/src/App.jsx`

**Interfaces:**
- Consumes: `todaysFocus` from `src/data/placeholder.js` (Task 3); `.glass-card`, `shadow-glow` global classes (Task 2).
- Produces: `TodaysFocusCard({ title, firstStep })` default export.

- [ ] **Step 1: Create the TodaysFocusCard component**

Create `dashboard-concept/src/components/TodaysFocusCard.jsx`:
```jsx
export default function TodaysFocusCard({ title, firstStep }) {
  return (
    <section className="glass-card relative overflow-hidden p-8 shadow-glow">
      <p className="text-xs font-medium uppercase tracking-wide text-violet-200/50">
        Today's Focus
      </p>
      <h3 className="mt-3 text-2xl font-semibold text-violet-50">{title}</h3>
      <p className="mt-2 text-violet-200/60">{firstStep}</p>
    </section>
  );
}
```

- [ ] **Step 2: Wire it into App.jsx**

Replace `dashboard-concept/src/App.jsx` with:
```jsx
import Sidebar from "./components/Sidebar";
import GreetingHeader from "./components/GreetingHeader";
import TodaysFocusCard from "./components/TodaysFocusCard";
import ActiveGoalsPanel from "./components/ActiveGoalsPanel";
import RadialProgress from "./components/RadialProgress";
import { greeting, goals, todaysFocus, progressSummary } from "./data/placeholder";

export default function App() {
  return (
    <div className="flex min-h-screen bg-midnight">
      <Sidebar activeId="dashboard" />
      <main className="flex-1 space-y-6 p-8">
        <GreetingHeader name={greeting.name} timeOfDay={greeting.timeOfDay} />
        <TodaysFocusCard title={todaysFocus.title} firstStep={todaysFocus.firstStep} />
        <ActiveGoalsPanel goals={goals} />
        <RadialProgress percent={progressSummary.overallPercent} label="Overall" />
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Verify the build succeeds**

Run:
```bash
npm run build
```
Expected: exit code 0, no errors.

- [ ] **Step 4: Commit**

```bash
cd "C:/Projectsss/DayQuest"
git add dashboard-concept
git commit -m "Add TodaysFocusCard component"
```

---

### Task 9: ProgressSummary component

**Files:**
- Create: `dashboard-concept/src/components/ProgressSummary.jsx`
- Modify: `dashboard-concept/src/App.jsx`

**Interfaces:**
- Consumes: `RadialProgress` (Task 4); `progressSummary` from `src/data/placeholder.js` (Task 3); `.glass-card` global class.
- Produces: `ProgressSummary({ overallPercent, weeklyPercent })` default export.

- [ ] **Step 1: Create the ProgressSummary component**

Create `dashboard-concept/src/components/ProgressSummary.jsx`:
```jsx
import RadialProgress from "./RadialProgress";

export default function ProgressSummary({ overallPercent, weeklyPercent }) {
  return (
    <section className="glass-card flex items-center justify-around gap-6 p-6">
      <RadialProgress percent={overallPercent} label="Overall" />
      <RadialProgress percent={weeklyPercent} label="This week" />
    </section>
  );
}
```

- [ ] **Step 2: Wire it into App.jsx, replacing the standalone RadialProgress usage**

Replace `dashboard-concept/src/App.jsx` with:
```jsx
import Sidebar from "./components/Sidebar";
import GreetingHeader from "./components/GreetingHeader";
import TodaysFocusCard from "./components/TodaysFocusCard";
import ActiveGoalsPanel from "./components/ActiveGoalsPanel";
import ProgressSummary from "./components/ProgressSummary";
import { greeting, goals, todaysFocus, progressSummary } from "./data/placeholder";

export default function App() {
  return (
    <div className="flex min-h-screen bg-midnight">
      <Sidebar activeId="dashboard" />
      <main className="flex-1 space-y-6 p-8">
        <GreetingHeader name={greeting.name} timeOfDay={greeting.timeOfDay} />
        <TodaysFocusCard title={todaysFocus.title} firstStep={todaysFocus.firstStep} />
        <ActiveGoalsPanel goals={goals} />
        <ProgressSummary
          overallPercent={progressSummary.overallPercent}
          weeklyPercent={progressSummary.weeklyPercent}
        />
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Verify the build succeeds**

Run:
```bash
npm run build
```
Expected: exit code 0, no errors.

- [ ] **Step 4: Commit**

```bash
cd "C:/Projectsss/DayQuest"
git add dashboard-concept
git commit -m "Add ProgressSummary component"
```

---

### Task 10: NestVisualization component

**Files:**
- Create: `dashboard-concept/src/components/NestVisualization.jsx`
- Modify: `dashboard-concept/src/App.jsx`

**Interfaces:**
- Consumes: `nestCompletion` from `src/data/placeholder.js` (Task 3); `animate-pulse-slow` global animation (Task 2).
- Produces: `NestVisualization({ completion })` default export — `completion` is 0-1.

- [ ] **Step 1: Create the NestVisualization component**

Create `dashboard-concept/src/components/NestVisualization.jsx`:
```jsx
export default function NestVisualization({ completion }) {
  const glowSize = 200 + completion * 160;
  const opacity = 0.35 + completion * 0.45;

  return (
    <div className="relative flex items-center justify-center py-10">
      <div
        className="absolute animate-pulse-slow rounded-full"
        style={{
          width: glowSize,
          height: glowSize,
          background:
            "radial-gradient(circle, rgba(196,181,253,0.55) 0%, rgba(139,92,246,0.25) 45%, transparent 75%)",
          filter: "blur(20px)",
          opacity,
        }}
      />
      <div
        className="relative rounded-full border border-white/10"
        style={{
          width: 140,
          height: 140,
          background:
            "radial-gradient(circle at 35% 30%, rgba(245,208,254,0.8), rgba(139,92,246,0.6) 60%, rgba(13,11,26,0.9) 100%)",
          boxShadow: "0 0 60px rgba(196,181,253,0.45)",
        }}
      />
    </div>
  );
}
```

- [ ] **Step 2: Wire it into App.jsx**

Replace `dashboard-concept/src/App.jsx` with:
```jsx
import Sidebar from "./components/Sidebar";
import GreetingHeader from "./components/GreetingHeader";
import TodaysFocusCard from "./components/TodaysFocusCard";
import ActiveGoalsPanel from "./components/ActiveGoalsPanel";
import ProgressSummary from "./components/ProgressSummary";
import NestVisualization from "./components/NestVisualization";
import { greeting, goals, todaysFocus, progressSummary, nestCompletion } from "./data/placeholder";

export default function App() {
  return (
    <div className="flex min-h-screen bg-midnight">
      <Sidebar activeId="dashboard" />
      <main className="flex-1 space-y-6 p-8">
        <GreetingHeader name={greeting.name} timeOfDay={greeting.timeOfDay} />
        <NestVisualization completion={nestCompletion} />
        <TodaysFocusCard title={todaysFocus.title} firstStep={todaysFocus.firstStep} />
        <ActiveGoalsPanel goals={goals} />
        <ProgressSummary
          overallPercent={progressSummary.overallPercent}
          weeklyPercent={progressSummary.weeklyPercent}
        />
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Verify the build succeeds**

Run:
```bash
npm run build
```
Expected: exit code 0, no errors.

- [ ] **Step 4: Commit**

```bash
cd "C:/Projectsss/DayQuest"
git add dashboard-concept
git commit -m "Add NestVisualization component"
```

---

### Task 11: QuickAddButton component

**Files:**
- Create: `dashboard-concept/src/components/QuickAddButton.jsx`
- Modify: `dashboard-concept/src/App.jsx`

**Interfaces:**
- Produces: `QuickAddButton()` default export, no props — fixed-position pill button.

- [ ] **Step 1: Create the QuickAddButton component**

Create `dashboard-concept/src/components/QuickAddButton.jsx`:
```jsx
import { Plus } from "lucide-react";

export default function QuickAddButton() {
  return (
    <button className="fixed bottom-8 right-8 flex items-center gap-2 rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-400 px-5 py-3 text-sm font-medium text-white shadow-glow transition-transform hover:scale-105">
      <Plus size={18} />
      Quick Add Goal
    </button>
  );
}
```

- [ ] **Step 2: Wire it into App.jsx**

Replace `dashboard-concept/src/App.jsx` with:
```jsx
import Sidebar from "./components/Sidebar";
import GreetingHeader from "./components/GreetingHeader";
import TodaysFocusCard from "./components/TodaysFocusCard";
import ActiveGoalsPanel from "./components/ActiveGoalsPanel";
import ProgressSummary from "./components/ProgressSummary";
import NestVisualization from "./components/NestVisualization";
import QuickAddButton from "./components/QuickAddButton";
import { greeting, goals, todaysFocus, progressSummary, nestCompletion } from "./data/placeholder";

export default function App() {
  return (
    <div className="flex min-h-screen bg-midnight">
      <Sidebar activeId="dashboard" />
      <main className="flex-1 space-y-6 p-8">
        <GreetingHeader name={greeting.name} timeOfDay={greeting.timeOfDay} />
        <NestVisualization completion={nestCompletion} />
        <TodaysFocusCard title={todaysFocus.title} firstStep={todaysFocus.firstStep} />
        <ActiveGoalsPanel goals={goals} />
        <ProgressSummary
          overallPercent={progressSummary.overallPercent}
          weeklyPercent={progressSummary.weeklyPercent}
        />
      </main>
      <QuickAddButton />
    </div>
  );
}
```

- [ ] **Step 3: Verify the build succeeds**

Run:
```bash
npm run build
```
Expected: exit code 0, no errors.

- [ ] **Step 4: Commit**

```bash
cd "C:/Projectsss/DayQuest"
git add dashboard-concept
git commit -m "Add QuickAddButton component"
```

---

### Task 12: Final layout assembly

**Files:**
- Modify: `dashboard-concept/src/App.jsx`

**Interfaces:**
- Consumes: every component from Tasks 4-11 and the full placeholder data set from Task 3.
- Produces: the final `App` layout matching the spec — sidebar on the left; main content with the greeting header, a two-column grid (left: Today's Focus + Active Goals, right: Nest + Progress Summary), and the Quick Add button fixed in the corner.

- [ ] **Step 1: Rewrite App.jsx into the final grid layout**

Replace `dashboard-concept/src/App.jsx` with:
```jsx
import Sidebar from "./components/Sidebar";
import GreetingHeader from "./components/GreetingHeader";
import ActiveGoalsPanel from "./components/ActiveGoalsPanel";
import TodaysFocusCard from "./components/TodaysFocusCard";
import ProgressSummary from "./components/ProgressSummary";
import NestVisualization from "./components/NestVisualization";
import QuickAddButton from "./components/QuickAddButton";
import { greeting, goals, todaysFocus, progressSummary, nestCompletion } from "./data/placeholder";

export default function App() {
  return (
    <div className="flex min-h-screen bg-midnight">
      <Sidebar activeId="dashboard" />
      <main className="flex-1 px-6 py-8 md:px-12">
        <GreetingHeader name={greeting.name} timeOfDay={greeting.timeOfDay} />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <TodaysFocusCard title={todaysFocus.title} firstStep={todaysFocus.firstStep} />
            <ActiveGoalsPanel goals={goals} />
          </div>
          <div className="space-y-6">
            <NestVisualization completion={nestCompletion} />
            <ProgressSummary
              overallPercent={progressSummary.overallPercent}
              weeklyPercent={progressSummary.weeklyPercent}
            />
          </div>
        </div>
      </main>
      <QuickAddButton />
    </div>
  );
}
```

- [ ] **Step 2: Verify the build succeeds**

Run:
```bash
npm run build
```
Expected: exit code 0, no errors.

- [ ] **Step 3: Boot the dev server for handoff**

Run:
```bash
npm run dev -- --port 5174 &
SERVER_PID=$!
sleep 2
curl -s http://localhost:5174 | head -c 300
kill $SERVER_PID
```
Expected: curl output contains `<div id="root">`, no connection error. (This confirms the app serves correctly; full visual confirmation — colors, glow, spacing — is a human review step in a real browser, per the spec's Testing section.)

- [ ] **Step 4: Commit**

```bash
cd "C:/Projectsss/DayQuest"
git add dashboard-concept
git commit -m "Assemble final dashboard layout"
```
