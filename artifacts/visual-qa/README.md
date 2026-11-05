# Phase 1 visual QA

Generated locally on 2026-11-05 against the production Vite preview after the 2646d19 visual refresh and the local asset/trip-intake changes. The screenshot matrix covers Persian (`fa-IR`), English (`en-US`) and Arabic (`ar`) at 360, 390, 430, 768, 1024 and 1440 CSS px. Each full-page PNG is stored under its locale directory; `report.json` records the checks and relative screenshot paths.

## Automated checks

- 18 locale/viewport cases; zero failures for document language/direction, horizontal overflow, long mixed-script request/destination/itinerary content, local image and font loading, intake validation/clarification, keyboard focus, reduced motion, browser exceptions or unexpected external requests.
- axe-core 4.14.0: zero WCAG 2.0/2.1/2.2 A/AA rule violations in all 18 cases.
- Offline reload check passed for the service-worker-controlled app shell, one local image and a local font.
- The screenshots were manually inspected in all three languages at 360px and 1440px. This is a browser check, not a full assistive-technology audit.

## Lighthouse status

The existing `artifacts/lighthouse-mobile.json` is a historical Phase 1 baseline from before this visual/asset refresh and is not a measurement of the current build. Lighthouse and field Core Web Vitals were not rerun for this update. No current performance score or INP claim is made. Manual screen-reader, zoom, color-vision and touch-target review remains necessary before claiming full WCAG 2.2 AA conformance.
