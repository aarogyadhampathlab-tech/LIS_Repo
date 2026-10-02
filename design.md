---
version: "alpha"
name: "Glassmorphism"
description: "Glassmorphic interface with frosted glass effect. Ideal for overlays, modal dialogs, card components, premium interfaces. AI-ready template."
colors:
  primary: "#0080FF"
  secondary: "#8B00FF"
  tertiary: "#FF1493"
  neutral: "#000000"

typography:
  h1:
    fontFamily: -apple-system, sans-serif
    fontSize: 2.25rem
    fontWeight: 700
  body-md:
    fontFamily: -apple-system, sans-serif
    fontSize: 1rem
    fontWeight: 400
  label-caps:
    fontFamily: -apple-system, sans-serif
    fontSize: 0.75rem
    fontWeight: 500
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral}"
    padding: 12px
---

<!-- @format -->

## Overview

Glassmorphic interface with frosted glass effect. Ideal for overlays, modal dialogs, card components, premium interfaces. AI-ready template. Apple didn't invent frosted glass UI, but they made everyone care about it. iOS 7 dropped the skeuomorphism and introduced those translucent panels that let color bleed through from whatever sat behind them. It was polarizing. People hated it, then copied it. By Big Sur, the entire macOS chrome leaned into layered transparency as a spatial cue — and with visionOS, glass became the literal foundation of their spatial computing interface. It's not decoration there; it's architecture.

Microsoft took a parallel path with Fluent Design's acrylic material around 2017. Windows 11 doubled down on it. Their approach was more systematic — defined noise textures, tint layers, luminosity blend modes. Less "pretty blur" and more "engineered material."

What made glassmorphism actually viable for the web was backdrop-filter landing in all major browsers by 2020. Before that, you were faking it with duplicated backgrounds and clip paths — hacky, brittle, not worth the effort. Now it's a single CSS property. By 2026, it's a mature technique with solid browser support, though you still need to think about what happens when that blur can't render.

- Density: 5/10 — Balanced
- Variance: 4/10 — Moderate
- Motion: 4/10 — Subtle

- **Style:** Translucent, Layered, Vibrant, Blurred
- **Keywords:** Frosted glass, transparent, blurred background, layered, vibrant background, light source, depth, multi-layer
- **Era:** 2020s Modern
- **Light/Dark:** ✓ Full / ✓ Full

## Colors

- \*\*\*\* (rgba(255,255,255,0.1-0.3)) — Primary surface or dominant color
- **Electric Blue** (#0080FF) — Secondary accent
- **Neon Purple** (#8B00FF) — Accent color, emphasis elements
- **Vivid Pink** (#FF1493) — Primary text color
- **Teal** (#20B2AA) — Secondary accent

## Typography

- **Display / Hero:** System UI stack (-apple-system, sans-serif) — Weight 700, tight tracking, used for headline impact
- **Body:** System UI stack (-apple-system, sans-serif) — Weight 400, 16px/1.6 line-height, max 72ch per line
- **UI Labels / Captions:** System UI stack (-apple-system, sans-serif) — 0.875rem, weight 500, slight letter-spacing
- **Monospace:** JetBrains Mono — Used for code, metadata, and technical values

Scale:

- Hero: clamp(2.5rem, 5vw, 4rem)
- H1: 2.25rem
- H2: 1.5rem
- Body: 1rem / 1.6
- Small: 0.875rem

## Layout

- **Grid:** CSS Grid primary. Max-width containment: 1280px centered with 1.5rem side padding.
- **Spacing rhythm:** Balanced. Base unit: 0.5rem (8px).
- **Section vertical gaps:** clamp(4rem, 8vw, 8rem).
- **Hero layout:** Split-screen (text left, visual right).
- **Feature sections:** Zig-zag alternating text+image rows. No 3-equal-columns.
- **Mobile collapse:** All multi-column layouts collapse below 768px. No horizontal overflow.
- **z-index contract:** base (0) / sticky-nav (100) / overlay (200) / modal (300) / toast (500).

## Elevation & Depth

Backdrop blur (10-20px), subtle border (1px solid rgba white 0.2), light reflection, Z-depth

- **Physics:** Ease-out curves, 200-300ms duration. Smooth and predictable.
- **Entry animations:** Fade + translate-Y (16px → 0) over 420ms ease-out. Staggered cascades for lists: 80ms between items.
- **Hover states:** Subtle color shift + shadow adjustment over 200ms.
- **Page transitions:** Fade only (200ms).
- **Performance:** Only transform and opacity animated. No layout-triggering properties.

## Shapes

Base corner radius: 4px. See rounded tokens in front matter for the full scale.

## Components

- **Primary Button:** Subtly rounded (0.5rem) shape. Accent color fill. Hover: 8% darken + subtle lift shadow. Active: -1px translate tactile press. Font weight 600. No outer glows.
- **Secondary / Ghost Button:** Outline variant. 1.5px border in muted color. Text in primary color. Hover: subtle background fill.
- **Cards:** Subtly rounded (0.5rem) corners. Surface background. Subtle shadow (0 2px 12px rgba(0,0,0,0.06)). 1px border stroke.
- **Inputs:** Label above input. 1px border stroke. Focus ring: 2px accent color offset 2px. Error text below in semantic red. No floating labels.
- **Navigation:** Primary surface background. Active item: accent color indicator. Font weight 500 when active.
- **Skeletons:** Shimmer animation matching component dimensions. No circular spinners.
- **Empty States:** Icon-based composition with descriptive text and action button.

## Do's and Don'ts

- No emojis in UI — use icon system only (Lucide, Heroicons)
- No pure black (#000000) — use off-black or charcoal variants
- No oversaturated accent colors (saturation cap: 80%)
- No 3-column equal-width feature layouts — use zig-zag or asymmetric grid
- No `h-screen` — use `min-h-[100dvh]`
- No AI copywriting clichés: "Elevate", "Seamless", "Unleash", "Next-Gen"
- No broken external image links — use picsum.photos or inline SVG
- No generic lorem ipsum in demos

- Do Backdrop-filter blur 10-20px
- Do Translucent white 15-30% opacity
- Do Subtle border 1px light
- Do Vibrant background verified
- Do Text contrast 4.5:1 checked

## Use Case

Overlays, Modal dialogs, Card components, Premium interfaces

<!-- Source: https://designmd.app/library/glassmorphism · designmd.app -->
