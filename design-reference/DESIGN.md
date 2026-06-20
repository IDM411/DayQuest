---
name: Nocturne Sanctuary
colors:
  surface: '#141219'
  surface-dim: '#141219'
  surface-bright: '#3b383f'
  surface-container-lowest: '#0d0b14'
  surface-container-low: '#1d1a21'
  surface-container: '#211e25'
  surface-container-high: '#2b2930'
  surface-container-highest: '#36343b'
  on-surface: '#e6e0ea'
  on-surface-variant: '#cac4d4'
  inverse-surface: '#e6e0ea'
  inverse-on-surface: '#322f37'
  outline: '#948e9d'
  outline-variant: '#494552'
  surface-tint: '#cebdff'
  primary: '#cebdff'
  on-primary: '#381385'
  primary-container: '#a78bfa'
  on-primary-container: '#3c1989'
  inverse-primary: '#674bb5'
  secondary: '#c0c1ff'
  on-secondary: '#1000a9'
  secondary-container: '#3131c0'
  on-secondary-container: '#b0b2ff'
  tertiary: '#dbc839'
  on-tertiary: '#373100'
  tertiary-container: '#af9e00'
  on-tertiary-container: '#3b3500'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e8ddff'
  primary-fixed-dim: '#cebdff'
  on-primary-fixed: '#21005e'
  on-primary-fixed-variant: '#4f319c'
  secondary-fixed: '#e1e0ff'
  secondary-fixed-dim: '#c0c1ff'
  on-secondary-fixed: '#07006c'
  on-secondary-fixed-variant: '#2f2ebe'
  tertiary-fixed: '#f8e454'
  tertiary-fixed-dim: '#dbc839'
  on-tertiary-fixed: '#201c00'
  on-tertiary-fixed-variant: '#504700'
  background: '#0d0b14'
  on-background: '#e6e0ea'
  surface-variant: '#36343b'
  # Custom tokens promoted from previously-hardcoded hex values so future
  # screens reference them by name instead of re-typing the literal.
  surface-glass: '#1a1625'    # glass card/panel base, used at 40% opacity
  accent-goal: '#2dd4bf'      # Goals / on-pace semantic accent (teal)
  accent-calendar: '#fb7185'  # Calendar semantic accent (coral)
typography:
  display-lg:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  headline-sm:
    fontFamily: Manrope
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
# Radius scale as actually shipped in the tailwind.config. Tiles and primary
# cards use 2xl (1rem / 16px); buttons are pills (full). The earlier 1.5rem/24px
# tile value was never built — the code is canon, this reflects it.
rounded:
  DEFAULT: 0.25rem
  lg: 0.5rem
  xl: 0.75rem
  2xl: 1rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 20px
  margin: 24px
  tile-gap: 16px
---

## Brand & Style
The design system embodies a serene, celestial atmosphere designed for productivity within a private, late-night sanctuary. The aesthetic is a fusion of **Glassmorphism** and **Corporate Modern**, leveraging deep nocturnal tones to reduce eye strain and foster deep focus.

The brand personality is "The Wise Companion"—intelligent, calm, and slightly mystical. The UI should evoke a sense of quiet competence. This is reinforced by a mascot that features sharp, focused blue eyes, subtle translucent horns, and a soft, ethereal glow, suggesting a creature of higher intelligence that thrives in the quiet hours.

**Visual Principles:**
- **Luminance over Flatness:** Use light to define edges rather than high-contrast lines.
- **Atmospheric Depth:** Layers should feel like they are floating in a nebula, using blurs and soft glows.
- **Focused Clarity:** While the environment is dark, the active content must be vibrantly legible.

## Colors
This design system utilizes a "Deep Space" palette. The page **`background`** is a near-black obsidian (**#0d0b14**) — this is canon and is the single source of truth for the body backdrop. Note the distinction from **`surface`** (#141219), a fractionally lighter tone reserved for elevated, translucent layers such as the top bar (`bg-surface/40`); the two are intentionally different, not a mistake.

**Functional Palettes:**
- **Primary (Lavender):** Used for primary actions, active states, and brand-level highlights.
- **Semantic Sections:** Each core pillar of the interface is color-coded to provide immediate cognitive mapping. These colors should be used for thin top/left card borders (2px) and as subtle inner glows within their respective tiles. Pillars without a Material slot use the promoted accent tokens: **`accent-goal`** (#2dd4bf, teal) for Goals/on-pace, **`accent-calendar`** (#fb7185, coral) for Calendar. Reference these tokens — do not re-type the hex.
- **Glass surface:** Cards and panels are built on **`surface-glass`** (#1a1625) at 40% opacity. Reference the token rather than the literal.
- **Neutrals:** Grays are infused with purple tints to maintain the "Nocturne" warmth, preventing the UI from feeling cold or clinical.

## Typography
The typography system balances modern technical precision with organic warmth. 

- **Manrope** is used for headlines to provide a geometric yet friendly structure. 
- **Hanken Grotesk** serves as the body face, offering exceptional legibility in dark mode settings with its generous x-height.
- **Geist** is reserved for labels and metadata, providing a "developer-tool" level of precision that complements the intelligent mascot theme.

**Future enhancement (not yet applied in code):** headlines sitting atop vibrant gradients should take a slight `text-shadow` of `0 2px 4px rgba(0,0,0,0.5)` to ensure maximum contrast. No shipped screen currently does this; treat it as a planned refinement, not an existing rule.

## Layout & Spacing
The home screen utilizes a **6-Tile Grid System**. This is a 2-column, 3-row configuration on mobile, scaling to a 3-column, 2-row configuration on tablet and desktop.

**Grid Rules:**
- **Tile Aspect Ratio:** Tiles should aim for a square or slightly vertical 4:5 ratio to maintain density.
- **Rhythm:** All spacing is based on a 4px baseline. Components within tiles use 12px or 16px internal padding.
- **Adaptive Reflow:** On desktop, the grid expands into a 12-column underlying system where the 6 tiles occupy 4 columns each. On mobile, the tiles stack vertically in a single column or stay in a tight 2x3 grid depending on screen height.

## Elevation & Depth
Depth is created through "Luminous Layering." Instead of traditional drop shadows, this design system uses **Ambient Glows** and **Tinted Shadows**.

- **Cards/Tiles:** Use a background of `surface-glass` (#1a1625) at 40% opacity with backdrop blur (Glassmorphism).
- **Shadows:** Shadows are deep and wide: `0 20px 40px rgba(0, 0, 0, 0.6)`. 
- **Accents:** Every tile must have a 2px solid border on the **Top** and **Left** edges using its specific semantic color. The Bottom and Right edges should use a subtle, low-opacity white (10%) to simulate a light source from the top-left.
- **Active State:** Elements in focus gain an outer "aura" glow using their semantic color at 20% opacity.

## Shapes
The shape language is "Organic Geometric." 

- **Tiles & Primary Cards:** Use `rounded-2xl` (1rem / 16px) to create a soft, friendly container that contrasts with the technical typography. (The `.tile` component pins this to `border-radius: 1rem` directly.)
- **Buttons:** Primary actions (Done, Push, FAB) are full pills — `rounded-full`.
- **Inputs:** Use `rounded-lg`-scale 16px rounding for a consistent tactile feel.
- **Mascot Elements:** Use circular and elliptical shapes for the mascot’s aura and interactive elements to distinguish them from the structural grid.

## Components

### 6-Tile Grid Cards
The primary navigation units. Each tile features a large semantic-colored icon in the top right, a `headline-sm` title in the top left, and summary data (e.g., "4 tasks left") in `label-sm` at the bottom.

### Buttons
- **Primary:** Gradient background (Semantic Color to its darker shade), `body-md` bold white text, deep shadow.
- **Ghost:** No background, 1px border of semantic color, high-transparency hover state.

### Input Fields
Dark backgrounds (`surface-container-lowest` / #0d0b14), 16px rounding, and a 1px lavender border that glows when focused. Placeholder text should be in a muted indigo-gray.

### The Mascot Widget
The mascot appears in a dedicated header area or a floating "Capture" bubble. It should be rendered with a soft-focus background blur and a subtle breathing animation (scaling 1.0 to 1.02). Its eyes should track the user's cursor or tap location subtly.