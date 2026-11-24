# Rahgard V3 — local safe handoff for one Git commit/push

Baseline:
- Main repository: `AiDev168/Ai_Tourism`
- Intended branch: `feat/rahgard-unified-travel-v2`
- Previously verified live SHA: `9b5b07d0786578abdfac56848baf3c6d1260832e` (not a guarantee of current head).

**No application production code is changed directly by this handoff.** The documents/prototype and read-only schema tool are review inputs for Codex to integrate into the ORIGINAL Rahgard components. Do not host the standalone HTML as a second company portal.

Safe one-step Windows installation/push, from PowerShell in the folder containing both downloads:

```powershell
.\Install-Rahgard-Handoff.ps1 `
  -RepoRoot 'C:\Projects\Ai_Tourism' `
  -BundleZip '.\rahgard_v3_safe_handoff.zip' `
  -CommitAndPush
```

For review without committing, omit `-CommitAndPush`. Re-run with it after review.

The script refuses to continue if the existing branch/remote is wrong, tracked changes are present, remote HEAD changed, a destination file conflicts, or the bundle hashes differ. It **never overwrites** a differing tracked file.

It copies the two known local Issue #24 private artifacts into `%LOCALAPPDATA%` with verification and adds only those paths to `.git/info/exclude`, so they remain present locally but are not published.

Use Codex task `docs/operations/CODEX_TASK_RAHGARD_SCHEMA_AND_FORMS.md` after the upload. Access to live PostgreSQL and true role-backed API integration is Codex-owned. The metadata schema extractor must run with an approved read-only database identity; no production DDL is necessary for extraction.
