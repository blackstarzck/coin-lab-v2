```markdown
# Design System Specification: The Kinetic Laboratory

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Quantum Observer."** 

Unlike standard fintech platforms that feel like static spreadsheets, this system treats data as a living, breathing element. It moves away from the "boxed-in" aesthetic of traditional dashboards, favoring an editorial, high-precision laboratory feel. We achieve this through **Intentional Asymmetry**—where dense data clusters are balanced by expansive negative space—and **Chromatic Depth**, using light as a functional signifier rather than just decoration.

The system breaks the "template" look by treating the screen as a deep, multi-layered viewport. Elements aren't just placed; they are "docked" within a fluid, glass-like environment.

---

## 2. Colors & Surface Architecture
The palette is rooted in the deep void of a high-contrast dark mode, using luminance to guide the eye through complex financial strategies.

### The "No-Line" Rule
**Explicit Instruction:** Do not use 1px solid `#FFFFFF` or high-contrast borders to section the UI. Boundaries must be defined through:
1.  **Background Shifts:** Placing a `surface_container_low` card on a `surface` background.
2.  **Tonal Transitions:** Using `surface_container_highest` to draw attention to active modules.

### Surface Hierarchy (Nesting)
Treat the UI as stacked sheets of obsidian and frosted glass.
*   **Base Layer:** `surface` (#10131a) - The infinite laboratory floor.
*   **Sectioning:** `surface_container_low` (#191c22) - Large architectural blocks.
*   **Interactive Cards:** `surface_container_high` (#272a31) - Strategy and data cards.
*   **Floating Modals/Tooltips:** `surface_bright` (#363940) - Elements that exist "above" the logic.

### The "Glass & Gradient" Rule
To evoke a premium laboratory feel, use **Glassmorphism** for floating elements. 
*   **Recipe:** Apply `surface_variant` (#32353c) at 60% opacity with a `20px` backdrop-blur. 
*   **Signature Textures:** For primary CTAs and active chart fills, use a linear gradient: `primary_container` (#00d1ff) to `primary` (#a4e6ff) at a 135° angle.

---

## 3. Typography
The typographic system balances the high-fashion editorial feel of *Space Grotesk* with the invisible utility of *Inter*.

*   **Display & Headlines (Space Grotesk):** Used for "The Narrative." Large scales (up to `display-lg` 3.5rem) should be used for portfolio totals and strategy titles to provide an authoritative, boutique feel.
*   **Body & UI (Inter):** Used for "The Logic." Maintains 1.5x line-height for maximum readability in dense data environments.
*   **Numerical Data (Monospace/Inter Medium):** All tickers, prices, and status codes must use a monospace font or Inter with `tnum` (tabular numbers) enabled to ensure vertical alignment in tables.

---

## 4. Elevation & Depth
Depth is a functional tool for hierarchy, not a stylistic flourish.

*   **The Layering Principle:** Avoid shadows on static containers. Instead, create "soft lift" by placing a `surface_container_lowest` (#0b0e14) element inside a `surface_container` (#1d2026). This "sunken" effect denotes a protected data area.
*   **Ambient Shadows:** For floating strategy pickers, use a massive, soft shadow: `0px 24px 48px rgba(0, 0, 0, 0.4)`. The shadow should feel like a soft glow of "absence" rather than a hard drop-shadow.
*   **The "Ghost Border" Fallback:** If a separator is required for accessibility, use `outline_variant` (#3c494e) at **15% opacity**. High-contrast lines are strictly forbidden as they clutter the data-rich environment.

---

## 5. Components

### Strategy Cards & Data Tables
*   **No Dividers:** Forbid the use of horizontal rules (`<hr>`). Separate rows using a `0.2rem` (Space 1) vertical gap to let the `surface` color peek through, or alternate background shades between `surface_container_low` and `surface_container`.
*   **Dense Data Tables:** Use `label-sm` for headers in `on_surface_variant` (#bbc9cf). Content uses `body-sm` for maximum information density.

### Buttons & Interaction
*   **Primary Button:** Gradient fill (`primary_container` to `primary`). No border. `xl` roundedness (0.75rem).
*   **Secondary/Ghost:** `outline` (#859399) border at 20% opacity. Text in `primary`.
*   **Status Chips:** Use a subtle outer glow (bloom effect). A "Profit" chip should use `emerald_green` with a `0px 0px 8px` glow at 30% opacity of the same color.

### Multi-Line Charts
*   **The Glow Trace:** Chart lines should be `primary_fixed` (#b7eaff) with a subtle `2px` Gaussian blur glow underneath the main stroke to simulate a neon CRT monitor.
*   **Area Fills:** Use a gradient from `primary` (10% opacity) to transparent at the baseline.

---

## 6. Do’s and Don’ts

### Do:
*   **Do** embrace negative space. Even in a "data-rich" system, the space between containers (using `20` or `24` spacing scale) is what makes the data readable.
*   **Do** use `primary_fixed_dim` for non-interactive icons to keep them secondary to the data.
*   **Do** use micro-animations (0.2s ease-out) for hover states on strategy cards, increasing the backdrop-blur rather than changing the background color.

### Don't:
*   **Don't** use pure white (#FFFFFF) for text. Always use `on_surface` (#e1e2eb) to reduce eye strain in dark mode.
*   **Don't** use standard "Material Design" rounded corners. Stick to the refined `sm` (0.125rem) for data cells and `xl` (0.75rem) for major containers.
*   **Don't** ever use a solid 1px border for a grid. If the grid doesn't work without lines, the spacing is incorrect.

---

## 7. Spacing & Rhythm
This system operates on a custom fractional scale. For high-density data, use the `0.5` (0.1rem) and `1` (0.2rem) tokens for internal padding. For layout-level breathing room, jump to `16` (3.5rem) or `20` (4.5rem). The intentional jump from "ultra-tight" to "ultra-wide" is what gives the system its high-end editorial character.```