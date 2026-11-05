# AI Tourism — PWA Visual Design & Experience Brief

- **Version:** 0.1
- **Status:** Owner-approved visual quality requirement; creative direction is the starting design system for Phase 1
- **Owner stack approval:** 2026-11-05
- **Target:** Persian-first, RTL, mobile-first installable PWA
- **Implementation stack:** React + TypeScript; backend FastAPI + Python 3.13
- **Product boundary:** MVP modular monolith; no agent swarm, booking/payment engine or live provider dependency in Phase 1

## Multilingual interface requirement (owner-approved)

The interface ships with complete Persian (`fa-IR`, default RTL), English (`en-US`, LTR), and Arabic (`ar`, RTL) support. This is a first-release foundation, not a Persian-only shell with later translation placeholders. Navigation, forms, validation, loading/empty/error/offline states, warnings, itinerary and fixture text must be translated together. The language control is keyboard accessible; selection updates the root `lang` and `dir` attributes. Layout uses CSS logical properties, supports mixed-script names and long strings, and formats dates, numbers and currency through `Intl`. No runtime translation service is permitted.

Font fallback must cover Arabic, Persian and Latin glyphs without depending on a remote font service. UI-only destination examples are clearly labelled as fixtures and are not production facts. Phase 1 establishes a locale-aware API contract but performs no LLM calls. The final MVP release is not multilingual-ready until destination content and assistant responses are supported and quality-tested in all three languages.

The Phase 1 visual uses a locally bundled imagined hero composite and CSS illustration cards. They are decorative UI fixtures and must never be represented as documentary destination imagery.

## 1. Design intent — a travel product, not an admin dashboard

The PWA must feel like a thoughtfully art-directed travel publication with the utility of a fast modern product. It should evoke the anticipation of discovering a place, then make planning feel calm, clear and trustworthy.

The visual direction is **Contemporary Iranian Travel Editorial**:

- Editorial composition, strong image-led storytelling, confident Persian typography and generous negative space.
- A contemporary visual identity inspired by Iranian landscapes, architecture, craft, materials and light — not a collage of clichés or a literal historical theme.
- Warm, tactile surfaces paired with deep botanical/ink tones and restrained turquoise/saffron accents.
- Clear hierarchy and varied composition. Do not repeat the same generic rounded-card layout for every section.
- Trustworthy, useful and calm. The product should not look like a casino, crypto dashboard, generic AI chat clone or travel-booking template.

The design must be recognizable and beautiful without sacrificing speed, accessibility, clarity or RTL correctness.

## 2. Visual concept and design tokens

Treat the values below as an initial controlled palette, not as permission to use every color in every component. Define CSS variables/design tokens and semantic aliases; components must consume tokens rather than scattered hex values.

### 2.1 Initial palette

| Token | Initial value | Intended use |
|---|---|---|
| `--color-paper` | `#F7F4EC` | Warm primary canvas |
| `--color-surface` | `#FFFEFA` | Elevated content surface |
| `--color-ink` | `#1E2B28` | Main text / dark surface |
| `--color-forest` | `#174E45` | Primary action / anchor |
| `--color-teal` | `#2B8178` | Secondary accent / interactive highlight |
| `--color-sand` | `#DCCDB5` | Subtle border / warm neutral |
| `--color-saffron` | `#D79A38` | Small emphasis / discovery accent |
| `--color-clay` | `#B9644E` | Rare editorial accent / warning context |
| `--color-muted` | `#68736F` | Secondary text |
| `--color-border` | `#E5E0D5` | Quiet separators |
| `--color-success` | `#28745A` | Confirmed/success states |
| `--color-danger` | `#B54747` | Destructive/error states |

The final foreground/background pairings must pass contrast checks. Do not assume that every accent is suitable for text or small icons. Semantic status must use text/icon as well as color.

### 2.2 Typography

- Persian is the primary editorial language. Choose a Persian-capable, high-quality font with clear letterforms, good numerals, proper diacritics and a variable-weight range where licensing and technical quality permit.
- Evaluate Persian families such as Vazirmatn or Estedad during implementation; select one primary family and one compatible Latin fallback only after checking glyph coverage, license, file weight and rendering on Windows/Android/iOS.
- Prefer self-hosted/subsetted WOFF2 assets. Do not make first paint depend on a third-party font CDN.
- Establish a deliberate type scale for display headlines, section titles, body, metadata and dense data. Avoid excessively thin Persian weights at small sizes.
- Use tabular numerals for budgets, dates, distances and counts where helpful. Keep numeral and calendar formatting in a locale-aware presentation layer; do not change stored data formats.
- Test Persian/Latin mixed strings, URLs, English destination names, digits, punctuation and bidirectional snippets.

### 2.3 Shape, layout and depth

- Use an 8-point spacing rhythm with a small set of consistent spacing tokens.
- Use a restrained radius scale: tighter for controls, larger for editorial image panels, and consistent card geometry. Avoid turning every element into a pill.
- Prefer layered surfaces, fine borders and soft natural shadows over heavy glassmorphism, neon glow or excessive blur.
- Use a clear responsive grid. The desktop canvas may use wider editorial compositions; the phone layout must be intentionally composed, not a squeezed desktop page.
- Keep primary content widths readable. Long Persian paragraphs should not span the full desktop viewport.

## 3. Photography and visual content

Photography is a core part of the visual identity, not decorative filler.

- Use high-quality, relevant, correctly licensed images with documented source/usage rights. Prefer a curated local asset pipeline or an approved image service; never hotlink random search-result images.
- Use a deliberate art direction: natural light, strong composition, authentic landscapes/architecture/details, coherent color treatment and realistic context.
- Use varied crops and aspect ratios intentionally: wide hero imagery, editorial landscape panels, and consistent recommendation thumbnails.
- Preserve focal points with responsive `object-position`; do not crop important architectural or human details accidentally.
- Use responsive AVIF/WebP where supported, with a safe fallback, explicit width/height or aspect-ratio reservation, lazy loading below the fold, and eager/high-priority loading only for the actual hero/LCP image.
- Every informative image needs meaningful Persian alternative text. Decorative images must have empty alt text.
- Never invent a photograph of a real destination or present an AI-generated visual as documentary evidence. Illustrative/AI-generated art, if ever approved, must be clearly separated from factual destination photography.
- No destination without an approved image? Use a designed neutral placeholder with a clear missing-media state; do not use unrelated imagery.
- The current 17 UNESCO entries remain `needs_review`. Do not expose them as live recommendations or imply editorial approval just to populate attractive screens. Visual development may use isolated fixtures clearly marked as demo/test content and excluded from production data/API.

## 4. Page and journey direction

Design the whole journey as one coherent product. Detailed interaction behavior is refined in later phases, but the component language and responsive layouts must be established in Phase 1.

### 4.1 Home / discovery

- A distinctive, spacious hero composition with one strong destination/travel photograph, a short Persian promise and a highly visible start-planning action.
- Avoid generic gradient hero + centered SaaS search field. Use purposeful editorial alignment and a clear visual focal point.
- Show discovery sections only when supported by approved real content. Otherwise use a clearly labeled empty/coming-soon state in development.
- Navigation should be light and focused. On mobile, keep the primary action reachable without a large permanent header.

### 4.2 Trip conversation / assistant

- The conversation must look like a premium travel concierge, not a clone of a generic AI chat UI.
- Give the user message, assistant response, sources/warnings and suggested next action distinct visual hierarchy.
- The composer must remain usable above mobile keyboards and safe areas. Avoid overlapping the final message or hiding the submit action.
- On wider screens, a secondary trip-summary panel may show extracted requirements. On mobile, convert it to a compact expandable sheet/section; it must not squeeze the conversation into a narrow column.
- Loading, clarification, retry, disconnected, empty and provider-unavailable states must be designed, not left to browser defaults.

### 4.3 Recommendation results

- Use a deliberately varied editorial ranking: one lead recommendation may receive more visual weight, while alternatives remain easy to compare.
- Each result must clearly distinguish the destination name, approved image, reason for recommendation, satisfied constraints, unknowns/warnings and traceable source information.
- Do not rely on fake radial scores, stars, badges or arbitrary percentages. Display only metrics supported by deterministic application data.
- A visually attractive result must never hide that a fact is unverified, stale or unknown.

### 4.4 Destination detail

- Use an image-led but readable page: photographic header, clear identity/location, concise overview, verified highlights, contextual source references and explicit unknowns.
- Coordinate semantics matter. A `property_reference` must never be styled or labelled as a visitor entrance or a directions-ready gate.
- Keep practical actions distinct from editorial description.

### 4.5 Editable itinerary

- Show a clear day-by-day structure with an understandable timeline and elegant stop hierarchy.
- Editing, reorder, remove and add actions must have clear touch targets, keyboard alternatives and confirmation/undo behavior where appropriate.
- Never make a route line, duration or travel-time label appear authoritative when no routing provider supports it.
- Empty days, long names, warnings, and small-screen scrolling must be handled intentionally.

### 4.6 Profile and settings (later phase)

- Use the same visual system but keep account controls calm and conventional.
- Privacy, consent, export and deletion states must be explained plainly; do not imply deletion or retention guarantees that the approved policy does not support.

## 5. Mobile-first and responsive behavior

Primary quality must be demonstrated at narrow widths first. At minimum review:

- 360 CSS px — narrow Android baseline;
- 390 CSS px — common modern phone baseline;
- 430 CSS px — large phone baseline;
- 768 CSS px — tablet transition;
- 1024 CSS px — compact desktop/tablet landscape;
- 1440 CSS px — wide desktop composition.

Requirements:

- Use CSS logical properties (`padding-inline`, `margin-inline`, `inset-inline`, `border-inline`) and `dir="rtl"`; do not hard-code left/right assumptions into reusable components.
- Verify navigation, forms, cards, timelines, pagination, skeletons, toasts and dialogs in RTL.
- Ensure mobile bottom actions respect safe-area insets and the on-screen keyboard.
- Keep touch targets comfortably large; aim for at least 44×44 CSS px for primary interactive controls.
- Do not make horizontal scrolling necessary for core product journeys.
- Test both Persian text and long Latin names/URLs without clipping or broken bidi order.

## 6. Interaction and motion

- Use purposeful micro-interactions for selection, focus, card reveal, transitions and progress. Motion should reinforce hierarchy, not entertain at the user's expense.
- Keep animation brief and restrained; avoid parallax backgrounds, continuously moving decoration, large particle effects and scroll-jacking.
- Respect `prefers-reduced-motion`; essential information and controls must not depend on animation.
- Use clear pressed, hover, focus-visible, disabled, pending, success and error states.
- Avoid layout shifts when images load, errors appear or text streams.
- Streaming text must remain readable and stable; do not continuously force-scroll when the user has moved away from the bottom.

## 7. Performance is part of the visual design

The PWA must feel immediate on a normal mobile device and a constrained network, not just look good on a developer workstation.

### 7.1 Initial field targets

At the 75th percentile for real users, aim for the published "good" Core Web Vitals thresholds:

- LCP ≤ 2.5 seconds;
- INP ≤ 200 milliseconds;
- CLS ≤ 0.1.

These thresholds follow Google's [Core Web Vitals guidance](https://developers.google.com/search/docs/appearance/core-web-vitals). They are product targets to measure, not claims that the current code already achieves them.

### 7.2 Engineering budgets and rules

- Establish a repeatable mobile Lighthouse baseline in Phase 1 and record device/network settings.
- Target Lighthouse Performance ≥ 90 for the static Phase 1 shell on the agreed mobile profile; investigate regressions rather than hiding them with desktop-only scores.
- Keep the initial JS bundle small; route-level code splitting and lazy-loaded below-the-fold sections are preferred.
- Avoid heavy UI libraries, large icon packs, unnecessary charting packages, autoplay video and multiple animation runtimes.
- Images must be responsive and correctly sized. Reserve dimensions to prevent layout shifts.
- Load only required font subsets/weights; use `font-display: swap` and a compatible fallback.
- Defer non-critical work. Health/landing pages must not trigger LLM, RAG, weather or maps requests.
- Use skeletons only where they accurately represent the final layout. Do not animate every placeholder.
- PWA service-worker caching must be conservative: cache versioned static assets and the application shell only. Do not cache personal conversation/trip responses in a shared or opaque cache by default.
- Offline state must be explicit. Do not claim full offline travel planning; preserve safe drafts only if their privacy behavior is designed and tested.

## 8. Accessibility and inclusive interaction

Target **WCAG 2.2 Level AA** for the PWA, including mobile/touch requirements. WCAG 2.2 is the current W3C recommendation and is also ISO/IEC 40500:2025; see [W3C WCAG overview](https://www.w3.org/WAI/standards-guidelines/wcag/) and [W3C publication history](https://www.w3.org/standards/history/WCAG22/).

Minimum implementation checks:

- Text contrast at least 4.5:1 for normal text and 3:1 for large text/essential UI boundaries where required.
- Full keyboard operation for interactive flows; visible focus indicator and logical focus order in RTL.
- Programmatic labels, meaningful headings, landmarks, button names and status announcements.
- Errors are described in text and associated with the relevant field; color alone never communicates status.
- Zoom/reflow, reduced motion and appropriate target sizes are tested.
- Images and icon-only buttons have appropriate accessible names.
- Dialogs/sheets trap and restore focus correctly and are dismissible without losing user data.

## 9. Visual quality bar and acceptance criteria

A page is not accepted merely because it renders.

1. The Home, conversation shell, recommendation layout and itinerary layout have deliberate visual hierarchy and page-specific composition.
2. The result looks like one branded travel product rather than unrelated component-library defaults.
3. Persian typography, mixed-script rendering and RTL layout are reviewed at every required viewport.
4. Images have a documented source/license, responsive delivery and correct alt behavior.
5. Empty, loading, error, warning, disconnected and unavailable states receive the same design care as the happy path.
6. No horizontal overflow, clipped control, overlapping composer, unstable image region or inaccessible focus state is present in core journeys.
7. Screenshots are captured for the agreed mobile and desktop viewports and reviewed against this brief; obvious hierarchy, crop, spacing, bidi and contrast defects are fixed before sign-off.
8. The visual review includes both a cold/first-load state and a returning/cached state.
9. Performance and accessibility results are attached to the Phase 1 delivery report. Targets are reported honestly; any miss is listed with a remediation plan.
10. The app must remain responsive and usable with reduced motion, image loading failure and slower network conditions.

## 10. Phase 1 visual deliverables

- A small token-based design system (colors, type, spacing, radii, elevation, focus, motion).
- Reusable primitives for buttons, inputs, navigation, cards, badges/status text, source references, alerts, skeletons, sheets/dialogs and empty/error states.
- A high-fidelity Persian RTL PWA shell with Home/discovery and representative conversation/recommendation/itinerary layouts. Interactive product behavior may remain limited in Phase 1; no fake live data is allowed.
- A responsive image strategy and local/licensed asset manifest; no random hotlinked photos.
- A screenshot review pack at 360/390/430/768/1024/1440 CSS px.
- A short visual QA report, a mobile performance baseline and an accessibility checklist.

Do not build all future product pages or complete all user journeys in Phase 1. The goal is a visually finished, technically sound shell with reusable foundations for later feature phases.

## 11. Visual anti-patterns

Reject:

- generic dashboard templates as the public travel experience;
- default component-library styling without art direction;
- a wall of identical white rounded cards;
- random gradients, neon, glassmorphism, giant shadows or excessive badges;
- stock imagery unrelated to the place;
- tiny Persian type, weak contrast, forced letter spacing that damages Persian shaping;
- desktop-first layouts squeezed onto mobile;
- motion that harms readability, accessibility or battery/network performance;
- synthetic or review-required destinations presented as real approved recommendations.

## 12. Phase 1 design review checklist

- [ ] Owner-approved stack used; no unapproved framework or UI kit added.
- [ ] Persian is the default language and layout is RTL from the document root.
- [ ] Tokenized palette, typography, spacing and component states exist.
- [ ] Home and representative product layouts have distinctive editorial composition.
- [ ] Desktop is not simply the mobile layout stretched; mobile is not a shrunk desktop.
- [ ] Photography is licensed, responsive and does not shift layout.
- [ ] Core pages function with keyboard, touch, zoom and reduced-motion settings.
- [ ] No user data or credentials are cached in the service worker by default.
- [ ] Lighthouse/performance and accessibility checks are documented with their environment.
- [ ] Screenshot pack and visual QA findings are included in the delivery report.
