# Rahgard hosted image build and isolated handoff

## Scope and stop line

This procedure builds the already reviewed application commit
`d5d9847373b20087a8a866449c6550d306f45b63` on a manually started GitHub-hosted
Ubuntu runner, packages the exact API and Web images for `linux/amd64`, and
checks them against the previously rehearsed PostgreSQL restore clone. It does
not deploy, migrate, restart, or publish anything on the live pilot. The live
release remains `5e2664fb51e18f52549aa37a8b5793e12ace09b2`.

The workflow uses only official, full-commit-pinned `actions/checkout` and
`actions/upload-artifact` actions. It passes no runtime credentials or secrets
to Docker builds. Docker Hub and package registries are contacted only from
the authorized GitHub-hosted runner. If that runner cannot reach the pinned
parent images or package registries, the workflow fails and the release remains
blocked; do not substitute tags, mirrors, or registries without review.

## Default-branch prerequisite

The repository's default branch is `main`; at preparation time it contains no
GitHub Actions workflow file. GitHub requires a `workflow_dispatch` workflow
file to exist on the default branch before a manual run can be triggered. The
feature-branch workflow must therefore be reviewed and placed on `main` through
the normal owner-approved PR process before its Run workflow action becomes
available. This package does not change the default branch, merge, or dispatch
the build.

## Run the one-time build

After the workflow file is present on `main`:

1. Open **Actions → Build Rahgard d5 Linux amd64 release images → Run
   workflow**.
2. Select `main` as the workflow branch and enter exactly
   `d5d9847373b20087a8a866449c6550d306f45b63` as `source_sha`.
3. Confirm the run succeeds. Download the single artifact
   `rahgard-release-images-d5d9847-linux-amd64` within its 7-day retention.
4. Confirm it contains only:
   - `rahgard-images-linux-amd64.tar`
   - `release-manifest.json`
   - `SHA256SUMS.txt`

The exact Git source archive is used only inside the runner as the Docker build
context. Its SHA-256 is recorded in the manifest; the archive itself is not
uploaded, avoiding unnecessary transfer of tracked research/visual artifacts.

The equivalent GitHub CLI invocation (after the prerequisite merge) is:

```powershell
gh workflow run .github/workflows/rahgard-release-image-build.yml `
  --repo AiDev168/Ai_Tourism --ref main `
  -f source_sha=d5d9847373b20087a8a866449c6550d306f45b63
gh run list --repo AiDev168/Ai_Tourism `
  --workflow rahgard-release-image-build.yml --limit 5
```

After the run succeeds, download its artifact by the run ID shown above:

```powershell
$RunId = '<successful workflow run ID>'
$Bundle = Join-Path $PWD 'rahgard-release-images-d5d9847-linux-amd64'
gh run download $RunId --repo AiDev168/Ai_Tourism `
  --name rahgard-release-images-d5d9847-linux-amd64 --dir $Bundle
```

The build manifest records the source SHA and Git-archive SHA-256, image tags,
image IDs, OS/architecture, entrypoint/command, revision labels, the three
parent `RepoDigests`, Dockerfile and lockfile hashes, image archive checksum,
and a secret scan result. The target tags are exactly:

```text
rahgard-api:d5d9847373b20087a8a866449c6550d306f45b63
rahgard-web:d5d9847373b20087a8a866449c6550d306f45b63
```

The Dockerfiles and `uv.lock` / `frontend/package-lock.json` at d5 are not
modified. The Docker archive is not committed to Git.

## Verify and transfer

From PowerShell after extracting the GitHub artifact ZIP, verify its listed
hashes before transfer:

```powershell
$Bundle = (Resolve-Path 'C:\path\to\rahgard-release-images-d5d9847-linux-amd64').Path
$Expected = @{}
Get-Content -LiteralPath (Join-Path $Bundle 'SHA256SUMS.txt') | ForEach-Object {
    if ($_ -notmatch '^([0-9a-f]{64})  (.+)$') { throw 'Invalid checksum row' }
    $Expected[$Matches[2]] = $Matches[1]
}
foreach ($Name in $Expected.Keys) {
    $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $Bundle $Name)).Hash.ToLowerInvariant()
    if ($Actual -ne $Expected[$Name]) { throw "Checksum mismatch: $Name" }
}
```

Transfer only the verified artifact files to the operator-protected incoming
directory using the existing authorized SSH identity. Do not transfer `.env`,
secret files, database archives, or any credentials. Also transfer these
three committed tooling files while preserving their relative paths beneath
`/opt/rahgard-staging/tools/`:

```text
scripts/ops/verify_rahgard_release_image_bundle.py
scripts/ops/verify_and_rehearse_rahgard_image_bundle.sh
deploy/staging/rehearse-018-021.sh
```

For example, if the operator-provisioned incoming directory is
`/opt/rahgard-staging/incoming/rahgard-release-images-d5d9847-linux-amd64`:

```powershell
$Remote = 'zoneroot@rahgard-vps:/opt/rahgard-staging/incoming/rahgard-release-images-d5d9847-linux-amd64/'
Get-ChildItem -LiteralPath $Bundle -File | ForEach-Object { scp -- $_.FullName $Remote }
```

The incoming directory and tools directory must be provisioned with the
existing private-pilot ownership and ACL policy; do not make them world
writable or copy secrets into them.

After the files are present, the operator runs:

```bash
bash /opt/rahgard-staging/tools/scripts/ops/verify_and_rehearse_rahgard_image_bundle.sh \
  /opt/rahgard-staging/incoming/rahgard-release-images-d5d9847-linux-amd64 \
  <previously-verified-encrypted-backup-basename>
```

The command checks all hashes and archive paths before `docker load`, verifies
the loaded image IDs and d5 revision labels, then invokes the guarded existing
backup restore rehearsal. In strict mode, the rehearsal refuses any
runtime-derived API image. It restores only to a uniquely named, `--network
none`, tmpfs PostgreSQL clone, applies migrations 0018–0021 only to that clone,
checks retained row counts/security, starts the exact hosted API image against
the clone, and starts the exact hosted Web image in the same isolated network
namespace. It verifies API readiness/catalogue count, static shell and hashed
assets, and the Web-to-API catalogue proxy. It does not publish host ports or
mount the persistent database volume. The currently running API container is
queried only for its old image identity and database container ID; it is not
restarted or modified. The old API is separately tested against the clone for
application rollback compatibility.

The image tags remain loaded in Docker after a successful rehearsal so the
operator can inspect them. No deployment command is run. A separate explicit
owner decision is required before migrations or application rollout on the
live database.

## Failure handling

- A Docker Hub 403, timeout, or package-registry failure on the hosted runner
  means **BLOCKED**. Preserve the log's failing host/status and arrange an
  approved registry-access path; do not retry the same inaccessible Windows or
  VPS pull paths.
- Missing base `RepoDigests`, non-`linux/amd64` images, mismatched source
  labels, extra image tags, secret files, archive checksum mismatch, or loaded
  image-ID mismatch all fail closed.
- Missing/invalid protected backup material or any database restore/migration
  mismatch stops the isolated rehearsal. Do not bypass a guard or run against
  the persistent database.
- Keep the live VPS at
  `5e2664fb51e18f52549aa37a8b5793e12ace09b2` until a separate rollout is
  explicitly approved.
