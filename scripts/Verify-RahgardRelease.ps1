<#
.SYNOPSIS
  Read-only three-way release identity check for Rahgard.
.DESCRIPTION
  Checks a clean local Windows checkout, the remote branch commit and the
  release source SHA on the live Ubuntu host. Does not deploy or modify data.
.EXAMPLE
  ./scripts/Verify-RahgardRelease.ps1 -VpsSshTarget operator@rahgard-vps
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidatePattern('^[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+$')]
  [string]$VpsSshTarget,
  [string]$Remote = 'origin',
  [string]$ReleaseMarker = '/opt/rahgard-staging/current/RELEASE_COMMIT'
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
$remoteLine = Invoke-Checked 'git' @('ls-remote', $Remote, "refs/heads/$branchName")
if ($remoteLine -notmatch '^([0-9a-f]{40})\s+refs/heads/') {
  throw "Remote branch is missing or unparseable: $Remote/$branchName"
}
$remoteSha = $Matches[1]
$serverSha = Invoke-Checked 'ssh' @('-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', $VpsSshTarget, "cat $ReleaseMarker")
if ($localSha -notmatch '^[0-9a-f]{40}$' -or $serverSha -notmatch '^[0-9a-f]{40}$') {
  throw 'One of the release markers was not a valid commit SHA.'
}
Write-Host "Local Windows: $localSha"
Write-Host "GitHub/$Remote: $remoteSha"
Write-Host "VPS release:   $serverSha"
if ($localSha -ne $remoteSha -or $localSha -ne $serverSha) {
  throw 'NOT SYNCHRONIZED. Do not declare three-way deployment complete.'
}
Write-Host "PASS: all three code release SHAs match ($localSha)."
Write-Host 'Data integrity is separate: verify the PostgreSQL ledger and off-host restore evidence.'
