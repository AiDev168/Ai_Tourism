# Phase 1 visual QA

Generated locally on 2026-11-05. Screenshots came from the Vite development server; Lighthouse ran against the production Vite preview. The screenshot matrix covers Persian (`fa-IR`), English (`en-US`) and Arabic (`ar`) at 360, 390, 430, 768, 1024 and 1440 CSS px. Each full-page PNG is stored under its locale directory; `report.json` records the checks and relative screenshot paths.

## Automated checks

- 18 locale/viewport cases; zero failures for `lang`/`dir`, horizontal overflow, long mixed Latin/Persian/Arabic form and itinerary-edit content, hero image load, or browser page exceptions.
- axe-core 4.14.0: zero WCAG 2.0/2.1/2.2 A/AA rule violations in all 18 cases. Lighthouse accessibility score: 100/100.
- Screenshots were visually inspected at Persian 360 px, English 1440 px, and Arabic 768 px. This is a browser check, not a full assistive-technology audit.

## Lighthouse mobile lab run

The full Lighthouse JSON is in [`lighthouse-mobile.json`](../lighthouse-mobile.json). Lighthouse CLI 13.6.0 ran against the local production preview with mobile device emulation and simulated throttling (Moto G Power 2022 user agent, Chrome 156).

| Measurement | Result |
|---|---:|
| Performance | 99/100 |
| Accessibility | 100/100 |
| First Contentful Paint | 0.8 s |
| Largest Contentful Paint | 2.3 s |
| Cumulative Layout Shift | 0 |
| Total Blocking Time | 20 ms |
| INP | Not measured by this single lab run |

These are one-run lab results, not field Core Web Vitals or 75th-percentile production measurements. No field INP claim is made. Manual keyboard/screen-reader, zoom, color-vision and touch-target review remains necessary before claiming full WCAG 2.2 AA conformance.
