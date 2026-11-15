<#
.SYNOPSIS
  Read-only machine-readable release identity and runtime manifest.
.DESCRIPTION
  Checks a clean local checkout, a synchronized named Git remote, and the
  running VPS source/configuration/container/migration identities. Does not
  deploy or modify data. This is not a backup, restore test, data-equivalence
  proof, or traveler acceptance test.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidatePattern('^[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+$')]
  [string]$VpsSshTarget,
  [string]$Remote = 'origin',
  [ValidatePattern('^/[A-Za-z0-9/_-]+$')]
  [string]$ReleaseMarker = '/opt/rahgard-staging/current/RELEASE_COMMIT',
  [string]$ManifestPath
)
$ErrorActionPreference = 'Stop'
function Invoke-Checked {
  param([string]$Program, [string[]]$Arguments)
  $output = & $Program @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$Program failed (exit=$LASTEXITCODE)" }
  return (($output | Out-String).Trim())
}
$dirty = Invoke-Checked 'git' @('status', '--porcelain', '--untracked-files=normal')
if ($dirty) { throw 'Local worktree is not clean. Commit or stash before release verification.' }
$localSha = Invoke-Checked 'git' @('rev-parse', 'HEAD')
$branchName = Invoke-Checked 'git' @('branch', '--show-current')
if ($branchName -notmatch '^[A-Za-z0-9._/-]+$' -or -not $branchName) {
  throw "Invalid or detached local branch: $branchName"
}
$remoteText = Invoke-Checked 'git' @('remote')
$remotes = @($remoteText -split "`r?`n" | ForEach-Object { $_.Trim() })
if ($Remote -notmatch '^[A-Za-z0-9_.-]+$' -or $Remote -notin $remotes) {
  throw "Remote must be an existing local remote name (got: $Remote)."
}
$upstream = Invoke-Checked 'git' @('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}')
if ($upstream -ne "$Remote/$branchName") { throw "Tracking branch mismatch: expected $Remote/$branchName, found $upstream." }
$divergence = Invoke-Checked 'git' @('rev-list', '--left-right', '--count', "$upstream...HEAD")
if ($divergence -notmatch '^0\s+0$') { throw "Local branch is not synchronized with upstream (behind/ahead: $divergence)." }
$remoteLine = Invoke-Checked 'git' @('ls-remote', $Remote, "refs/heads/$branchName")
if ($remoteLine -notmatch '^([0-9a-f]{40})\s+refs/heads/') { throw "Remote branch missing/unparseable: $Remote/$branchName" }
$remoteSha = $Matches[1]
if ($localSha -notmatch '^[0-9a-f]{40}$') { throw 'Local HEAD is not a full Git SHA.' }

# Static read-only VPS probe; only the marker path is parameterized and it is
# constrained to safe POSIX path characters before single-quote embedding.
$remoteScript = @(
  'set -Eeuo pipefail'
  'root=/opt/rahgard-staging'
  "sha=`$(cat -- '$ReleaseMarker')"
  'printf ''release_sha=%s\n'' "$sha"'
  'config_sha=$(sha256sum "$root/current/deploy/staging/compose.yaml" | cut -d '' '' -f 1)'
  'printf ''deploy_config_sha256=%s\n'' "$config_sha"'
  'compose=(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml")'
  'for service in api web db; do id=$("${compose[@]}" ps -q "$service"); test -n "$id"; docker inspect --format ''{{.Config.Image}}|{{.Image}}|{{.State.Status}}'' "$id" | sed "s/^/container_${service}=/"; done'
  '"${compose[@]}" exec -T db psql -X -q -A -t -U ai_tourism_owner -d rahgard_pilot_vps_staging -c "SELECT migration_id||''|''||rtrim(sha256) FROM system.schema_migrations ORDER BY migration_id" | sed ''s/^/migration=/'''
) -join "`n"
$remoteEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remoteScript))
$remoteCommand = "printf '%s' '$remoteEncoded' | base64 -d | bash"
$snapshot = Invoke-Checked 'ssh' @('-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes', $VpsSshTarget, $remoteCommand)

$serverSha = $null
$serverConfigSha = $null
$containers = @{}
$migrations = @()
foreach ($line in ($snapshot -split "`r?`n")) {
  if ($line -match '^release_sha=([0-9a-f]{40})$') { $serverSha = $Matches[1]; continue }
  if ($line -match '^deploy_config_sha256=([0-9a-f]{64})$') { $serverConfigSha = $Matches[1]; continue }
  if ($line -match '^container_(api|web|db)=(.+)\|(sha256:[0-9a-f]{64})\|(running)$') {
    $containers[$Matches[1]] = [ordered]@{ image = $Matches[2]; image_id = $Matches[3]; state = $Matches[4] }
    continue
  }
  if ($line -match '^migration=([A-Za-z0-9_-]+)\|([0-9a-f]{64})$') {
    $migrations += [ordered]@{ migration_id = $Matches[1]; sha256 = $Matches[2] }
    continue
  }
  if ($line) { throw "Unexpected or malformed VPS evidence line: $line" }
}
if (-not $serverSha -or -not $serverConfigSha) { throw 'VPS release/config marker is missing.' }
if ($containers.Count -ne 3 -or -not $containers.ContainsKey('api') -or -not $containers.ContainsKey('web') -or -not $containers.ContainsKey('db')) { throw 'Expected running api, web, and db containers were not all observed.' }
if ($containers.api.image -ne "rahgard-api:$serverSha" -or $containers.web.image -ne "rahgard-web:$serverSha") { throw 'API/PWA image tags do not match the VPS release SHA.' }
if ($containers.db.image -ne 'rahgard-postgres:17-postgis36-vector087') { throw 'Unexpected PostgreSQL image tag.' }
if ($migrations.Count -eq 0) { throw 'VPS migration ledger is empty or unreadable.' }
$configPath = Join-Path (Get-Location) 'deploy/staging/compose.yaml'
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) { throw 'Local deployment Compose file is missing.' }
$localConfigSha = (Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash.ToLowerInvariant()

$manifest = [ordered]@{
  schema_version = 1
  captured_at_utc = [DateTime]::UtcNow.ToString('o')
  application_version = $localSha
  git = [ordered]@{ branch = $branchName; local_sha = $localSha; remote = $Remote; remote_sha = $remoteSha; upstream = $upstream; behind = 0; ahead = 0; worktree_clean = $true }
  deployment = [ordered]@{ vps_release_sha = $serverSha; local_compose_sha256 = $localConfigSha; vps_compose_sha256 = $serverConfigSha; compose_matches = ($localConfigSha -eq $serverConfigSha) }
  runtime_images = $containers
  database = [ordered]@{ name = 'rahgard_pilot_vps_staging'; migration_count = $migrations.Count; migration_ledger = $migrations }
  scope_note = 'Identity/config/runtime snapshot only; does not prove backup restore, row equivalence, or traveler acceptance.'
}
$json = $manifest | ConvertTo-Json -Depth 8
if ($ManifestPath) {
  $fullManifestPath = [IO.Path]::GetFullPath($ManifestPath)
  $manifestParent = Split-Path -Parent $fullManifestPath
  if ($manifestParent -and -not (Test-Path -LiteralPath $manifestParent -PathType Container)) { throw 'Manifest output directory does not exist.' }
  Set-Content -LiteralPath $fullManifestPath -Value $json -Encoding utf8
}
Write-Output $json
if ($localSha -ne $remoteSha -or $localSha -ne $serverSha) { throw 'NOT SYNCHRONIZED: local, GitHub, and VPS source SHAs differ.' }
if (-not $manifest.deployment.compose_matches) { throw 'Deployment Compose digest mismatch.' }
Write-Host 'PASS: source SHAs, Compose digest, running image identities, and migration ledger were recorded.'
Write-Host 'This is not proof of restored data equivalence or traveler acceptance.'
