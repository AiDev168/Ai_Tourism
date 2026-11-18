# Rahgard VPS release decision — 2026-11-18

## Current decision

**READY FOR OWNER PRODUCTION APPROVAL.** The hosted d5 API/Web images passed the strict isolated restore, migrations, security, runtime, Web, and rollback rehearsal. This is readiness only; the owner has **not** authorized production rollout.

- Prepared application SHA: `d5d9847373b20087a8a866449c6550d306f45b63`
- Current live VPS SHA (unchanged): `5e2664fb51e18f52549aa37a8b5793e12ace09b2`
- GitHub Actions run / artifact: `44228225648` / `14393716721`
- Isolated rehearsal: exit 0; PostgreSQL clone advanced from migration 0017 to 0021; restored data counts unchanged; 27 protected tables have RLS and 67 policies.
- Live database: still at 16 migrations through 0017; persistent volume and records preserved.
- Live services: API, Web, and PostgreSQL remained healthy with their pre-rehearsal image IDs.
- Deployment, live migration, service restart, and publication: **not performed**.

The five high-severity npm audit package findings are confined to the locked frontend build/test dependency graph. `npm audit --omit=dev` reported zero production dependency findings; the final Web image contains the compiled static assets served by Nginx, not those npm packages. A separate dependency update review is recommended; d5's lockfile was not changed.

## Evidence

See [the exact hosted-image and isolated-rehearsal report](RAHGARD_HOSTED_IMAGES_ISOLATED_REHEARSAL_2026-11-18.md) and [the prior release-preparation history](VPS_RELEASE_GO_NO_GO_2026-11-17_HISTORICAL.md). Machine-readable sanitized results are in `evidence/hosted-image-rehearsal-2026-11-18.json`.

## Explicit owner approval gate

Before any production operation, the owner must approve the exact application SHA above, migrations 0018–0021, the maintenance/restart window, and the verified backup and application rollback procedure. Published content requires separate approval. No production command should run before that authorization.
