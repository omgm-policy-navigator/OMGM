---
name: Serene Hearth
colors:
  surface: '#fbf9f8'
  surface-dim: '#dbd9d9'
  surface-bright: '#fbf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f3'
  surface-container: '#efeded'
  surface-container-high: '#eae8e7'
  surface-container-highest: '#e4e2e2'
  on-surface: '#1b1c1c'
  on-surface-variant: '#444840'
  inverse-surface: '#303030'
  inverse-on-surface: '#f2f0f0'
  outline: '#74786f'
  outline-variant: '#c4c8bd'
  surface-tint: '#516447'
  primary: '#516447'
  on-primary: '#ffffff'
  primary-container: '#8fa382'
  on-primary-container: '#283920'
  inverse-primary: '#b8cdaa'
  secondary: '#7d562d'
  on-secondary: '#ffffff'
  secondary-container: '#ffca98'
  on-secondary-container: '#7a532a'
  tertiary: '#635e57'
  on-tertiary: '#ffffff'
  tertiary-container: '#a29c95'
  on-tertiary-container: '#38342e'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d4e9c4'
  primary-fixed-dim: '#b8cdaa'
  on-primary-fixed: '#101f09'
  on-primary-fixed-variant: '#3a4c31'
  secondary-fixed: '#ffdcbd'
  secondary-fixed-dim: '#f0bd8b'
  on-secondary-fixed: '#2c1600'
  on-secondary-fixed-variant: '#623f18'
  tertiary-fixed: '#e9e1d9'
  tertiary-fixed-dim: '#cdc5be'
  on-tertiary-fixed: '#1e1b16'
  on-tertiary-fixed-variant: '#4a4640'
  background: '#fbf9f8'
  on-background: '#1b1c1c'
  surface-variant: '#e4e2e2'
typography:
  headline-xl:
    fontFamily: Manrope
    fontSize: 40px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.25'
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-md:
    fontFamily: Be Vietnam Pro
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-sm:
    fontFamily: Be Vietnam Pro
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-lg:
    fontFamily: Manrope
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.05em
  label-md:
    fontFamily: Manrope
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.2'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 64px
---

## Brand & Style

This design system is anchored in an "Organic Editorial" aesthetic. It targets users seeking a calm, intentional, and curated experience—ideal for life planning, high-end lifestyle journals, or boutique wellness platforms. The personality is grounded and warm, avoiding the clinical coldness of typical SaaS products.

The visual direction leans into **Modern Minimalism** with a **Tactile** edge. It utilizes generous whitespace, delicate hairlines, and an arched geometry inspired by classical architecture and organic forms. The emotional response should be one of "quiet productivity" and "composed elegance," where the UI feels like a high-quality physical stationery set.

## Colors

The palette is derived directly from botanical sage and sun-bleached linen.
- **Primary (Sage):** Used for key actions, success states, and subtle brand accents. It represents growth and stability.
- **Secondary (Ochre/Warm Beige):** Used for highlighting interactive cues like checkboxes and progress indicators.
- **Surface (Warm Linen):** The background is a soft, non-white neutral (#F8F5F2) to reduce eye strain and provide a tactile, paper-like feel.
- **Text:** High-contrast charcoal (#2D2D2D) is used for headings, while a softer grey-brown is used for body copy to maintain a gentle visual hierarchy.

## Typography

The typography strategy balances modern precision with approachable warmth. **Manrope** is used for structural elements and headings to provide a clean, geometric foundation. **Be Vietnam Pro** handles body content, offering high readability with a friendly, contemporary character.

Headings should be set with tight letter spacing to feel "locked" and editorial. Body text utilizes a generous 1.6x line height to allow the organic layout to breathe. All labels are set in Manrope with slight tracking to ensure clarity at small sizes.

## Layout & Spacing

This design system employs a **Fluid-Fixed Hybrid** model. Content is contained within a 12-column grid on desktop (max-width 1280px) but scales fluidly between breakpoints. 

Spacing follows a strict 4pt rhythm, but "Macro-spaces" (XL and above) are used aggressively to create a sense of luxury and focus.
- **Mobile:** 4-column grid, 16px margins, 16px gutters.
- **Tablet:** 8-column grid, 32px margins, 20px gutters.
- **Desktop:** 12-column grid, 64px margins (or auto-centered), 24px gutters.

Horizontal groups of cards should use `space-between` to ensure a balanced distribution of visual weight across the container.

## Elevation & Depth

Depth is achieved through **Tonal Layering** and **Fine Outlines** rather than heavy shadows. 
- **Surface Level:** The base background is the warmest neutral.
- **Container Level:** Cards and input fields use a slightly lighter or darker tint (e.g., #EFEDE9) to distinguish themselves.
- **Outlines:** Elements use 1px solid borders in a muted version of the text color (opacity 10-15%) to define boundaries without adding visual "weight."
- **Shadows:** Reserved strictly for floating elements like dropdowns or modals. These should be "Ambient Shadows"—extremely diffused, using a tint of the primary sage color instead of pure black to maintain the organic feel.

## Shapes

The defining characteristic of this design system is the **Arched Motif**. 
- **Image Containers:** Use a "top-arch" style (semi-circle top, flat bottom) to mimic traditional windows or portals.
- **General Elements:** Buttons and cards follow a standard `rounded-md` (0.5rem) or `rounded-lg` (1rem) rule.
- **Interactive Elements:** Checkboxes are squares with a subtle 2px radius, maintaining a structured, organized look that contrasts against the fluid arches of the imagery.

## Components

- **Category Cards:** Feature a top-arched image followed by a subtle text label container. The container should have a background tint of the secondary color at low opacity (5-10%).
- **Buttons:** Primarily "Flat" or "Ghost" styles. The primary button uses a solid Sage fill with white text; the secondary button uses an Ochre outline.
- **Checkboxes:** Custom styled with an Ochre (#D4A373) fill when active. The check icon should be a clean 2px stroke.
- **Input Fields:** Minimalist design with a bottom-border only or a very soft 1px perimeter. Focus states are indicated by a color shift to Sage.
- **Chips/Badges:** Small, pill-shaped elements with a background color that matches the primary sage at 10% opacity, used for status or categories.
- **Progress Bars:** Thin 4px lines using the Ochre secondary color to denote movement and completion.