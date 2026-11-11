# Rahgard Issue 6 launch status

Branch: `feat/rahgard-issue6-launch-v1`
Base: `b66ab219308f54cda7898c06861516c33229603c`

## Delivered in this worktree

- Authenticated traveller UI can browse/search the published structured
  destination catalogue, select exact canonical identities, and see a
  localized coordinate-role disclosure. A representative/property point is
  not called an entrance or route. Unsaved itinerary state is preserved.
- Added a private-pilot geographic publication chain: owner signs the exact
  reviewed batch and target; a separately credentialed authorizer provisions
  short-lived authorization rows; the publisher role can only call the
  audited, non-login `SECURITY DEFINER` function. Migration 013 verifies
  canonical/source identity and marker before activation. It does not approve
  any POI by itself.
- Added protected persistent-backup and restore-rehearsal commands and a
  configuration preflight. Windows ACL validation is intentionally missing,
  so these commands fail closed on this Windows host. They do not provision a
  persistent database or choose retention.
- Fixed Issue 6 disposable-container shutdown to re-inspect ownership after
  stop and handle auto-removal without returning a false failure.

## Executed evidence

- Geo publication/review focused tests: 29 passed; Ruff passed.
- Migration `013_private_pilot_geo_audit.sql`: isolated PG17 test passed over
  loopback. It checked QA-only activation, production-view inclusion, audit,
  denied publisher direct writes, and idempotent retry. The runner returned 0
  and removed only its labelled disposable container.
- Backup/restore command tests: 19 passed; Ruff passed. The first run used an
  invalid pytest temp path and failed in setup; the corrected repository-local
  temp path passed.
- Frontend: 114 tests passed; TypeScript/Vite/PWA production build passed.
- Earlier in this same worktree, focused auth tests: 17 passed; Ruff passed.
- Browser: the existing `RAHGARD_GEO_BROWSE_E2E=1` fa-IR scenario passed in
  Chromium 156 against actual Vite/FastAPI and disposable PG17, using QA-only
  canonical records and fake OTP/Chat. It demonstrated catalogue browse,
  15-day 3+1 geographic grouping, 13 unplanned days, edit/save/reopen. It is
  not a persistent-pilot or owner-approved-data acceptance.

## Still blocked

- No owner approval for visibility of any of the four approximate Fars map
  points; no persistent publication has occurred.
- No approved persistent private database/host, database authority, trusted
  TLS/proxy configuration, secret-management path, backup target/retention,
  or rollback operator.
- Real SMS/auth recovery, administrator MFA/bootstrap, remote Chat consent,
  provider/budget/credentials, and privacy/incident policy remain owner gates.
- No physical-device acceptance. Coordinate disclosure is text, not a map or
  routing experience. No road times, opening hours, access, or accessibility
  facts are asserted.
- Therefore private pilot and public launch remain **NO-GO**.
