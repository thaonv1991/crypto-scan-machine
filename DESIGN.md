# CryptoScan AI - Design System (DESIGN.md)

This file defines the strict visual language for the CryptoScan AI platform. Any AI coding agent working on this project MUST adhere to these design principles to maintain a premium, cohesive, and "billion-dollar" aesthetic.

## 1. Visual Theme & Atmosphere
- **Aesthetic:** Dark-mode exclusive, Cyberpunk-lite, Glassmorphism, Technical Dashboard.
- **Vibe:** Urgent, data-dense, authoritative, and extremely modern. Like a high-end Wall Street terminal built for the year 2050.
- **Density:** High density. Users are VIP traders who want to see maximum alpha (signals) on a single screen without scrolling excessively.

## 2. Color Palette & Roles

| Semantic Role | Hex Value | Tailored Usage |
|---------------|-----------|----------------|
| **Background (Main)** | `#05070D` | The absolute void. Used for the outermost `<body>` background. |
| **Surface (Panel)** | `#0a0d14` | Used for sidebars and topbars. Slightly lighter than the void. |
| **Surface (Card)** | `#121622` | Used for content cards, tables, and inner containers. |
| **Primary Accent** | `#7c5cff` | Deep Neon Purple. Used for active states, AI highlights, primary buttons, and glowing shadows. |
| **Secondary Accent**| `#22d3ee` | Cyber Cyan. Used for tech details, web3 connections, and secondary indicators. |
| **Text Primary** | `#ffffff` | Pure white. Used for headings, numbers, and primary data points. |
| **Text Secondary**| `#94a3b8` | Slate gray. Used for labels, table headers, and descriptions. |
| **Danger (Red)** | `#ef4444` | Used for Scam, Rugpull, Honeypot, and Blacklist warnings. |
| **Warning (Yellow)**| `#f59e0b` | Used for Mintable, Medium-risk indicators. |
| **Success (Green)** | `#10b981` | Used for Safe, High-score, and positive signals. |

## 3. Typography Rules
- **Primary Font:** `Inter` (or `Roboto`). Clean, geometric sans-serif.
- **Numbers/Data:** Must use tabular lining or monospace fonts when displaying live prices, token ages, or scores to prevent horizontal jitter during realtime updates.
- **Hierarchy:**
  - `H1`: 24px, Font Weight 700, White.
  - `H2`: 18px, Font Weight 600, White.
  - `Labels`: 11px-12px, Uppercase, Tracking-Wider, Text Secondary (`#94a3b8`).

## 4. Component Stylings
- **Glass Panels (`.glass-panel`, `.glass-card`):** 
  - Must have `backdrop-blur-[12px]`.
  - Must have an ultra-thin border: `border border-white/5`.
  - Shadow: `shadow-[0_10px_40px_rgba(0,0,0,0.35)]`.
- **Buttons (Primary):**
  - Gradient Background: `bg-gradient-to-r from-primary to-cyan`.
  - Text: Black, Bold, Uppercase.
  - Hover: `hover:opacity-90` + glowing shadow `shadow-[0_0_20px_rgba(34,211,238,0.3)]`.
- **Warning Badges (Traffic Light):**
  - Red flags (HONEYPOT, BLACKLIST) must use `.animate-alert-flash` for a pulsing, urgent neon effect.

## 5. Depth, Elevation & Animations
- The UI should feel "alive".
- **Micro-animations:** Interactive elements should have `transition-all duration-200`.
- **Radar & Scanners:** Use slow, infinite rotation or pinging dots (`animate-ping`) to simulate real-time Web3 listening.
- **Gradients:** Use ambient radial gradients in the background to break up the solid black void.

## 6. Do's and Don'ts
- **DO NOT** use generic Tailwind colors like `bg-blue-500` or `bg-red-500` directly for main branding. Always use the mapped custom CSS variables/Tailwind config (e.g., `bg-primary`, `bg-cyan`).
- **DO NOT** use rounded corners larger than `rounded-2xl` (16px) for cards, and `rounded-xl` (12px) for buttons.
- **DO** blur premium data (Whale Radar, AI Signals) using `.pro-blur-overlay` for non-VIP users to drive conversions.

## 7. Agent Prompt Guide
*When asking an AI agent to build a new section:*
> "Build a new analytics widget following DESIGN.md. Use `.glass-card` for the container. The title should be Text Primary, 18px. Data numbers should be bold. Use the Primary Accent (`#7c5cff`) for the chart line."
