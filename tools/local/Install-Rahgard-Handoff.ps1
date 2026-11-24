#Requires -Version 5.1
<#
.SYNOPSIS
  Safely imports the reviewed Rahgard V3 docs/forms/schema tooling into the SAME
  Windows checkout. Private issue24 artifacts are recovered locally, NOT pushed.
.EXAMPLE
  .\Install-Rahgard-Handoff.ps1 -RepoRoot 'C:\Projects\Ai_Tourism' -BundleZip '.\rahgard_v3_safe_handoff.zip'
.EXAMPLE
  .\Install-Rahgard-Handoff.ps1 -RepoRoot 'C:\Projects\Ai_Tourism' -BundleZip '.\rahgard_v3_safe_handoff.zip' -CommitAndPush
.NOTES
  - Never force-pushes or resets/cleans the checkout.
  - Never stages *.local.mjs or the original private screenshot.
  - Refuses overwrites of differing existing files; ask Codex to resolve conflicts.
  - Does not connect to PostgreSQL, VPS or provider APIs.
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = 'C:\Projects\Ai_Tourism',
    [string]$BundleZip = (Join-Path $PSScriptRoot 'rahgard_v3_safe_handoff.zip'),
    [switch]$CommitAndPush
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
# Resolve the native executable once. PowerShell command names are case-insensitive;
# a function named Git shadows git.exe and would recurse on '& git'.
$script:GitExecutable = (Get-Command -Name 'git.exe' -CommandType Application -ErrorAction Stop).Source
if (-not (Test-Path -LiteralPath $script:GitExecutable -PathType Leaf)) {
    throw 'Native git.exe could not be resolved; no files or Git state have been changed.'
}
$ExpectedBranch = 'feat/rahgard-unified-travel-v2'
$PrivatePaths = @(
    'docs/operations/evidence/issue24/live-v2-mobile-390.png',
    'frontend/scripts/.issue24-live-apex-interactive.local.mjs'
)
function Invoke-RahgardGit([string[]]$GitArgs) {
    $output = & $script:GitExecutable -C $RepoRoot @GitArgs 2>&1
    if ($LASTEXITCODE -ne 0) { throw ("git {0} failed (exit {1}): {2}" -f ($GitArgs -join ' '), $LASTEXITCODE, ($output -join "`n")) }
    return $output
}
function Repo-Path([string]$Relative) {
    if ([string]::IsNullOrWhiteSpace($Relative) -or $Relative.StartsWith('/') -or
        $Relative.StartsWith('\\') -or $Relative.Contains('\\') -or
        $Relative.Contains(':') -or @($Relative.Split('/')) -contains '..' -or
        @($Relative.Split('/')) -contains '.' -or $Relative -notmatch '^[A-Za-z0-9._/-]+$') {
        throw "Unsafe handoff path: $Relative"
    }
    return (Join-Path $RepoRoot ($Relative.Replace('/', [IO.Path]::DirectorySeparatorChar)))
}
function Hash([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
if (-not (Test-Path -LiteralPath $RepoRoot -PathType Container)) { throw "RepoRoot does not exist: $RepoRoot" }
if (-not (Test-Path -LiteralPath $BundleZip -PathType Leaf)) { throw "Bundle not found: $BundleZip" }
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$BundleZip = (Resolve-Path -LiteralPath $BundleZip).Path
$branch = ((Invoke-RahgardGit @('branch','--show-current')) | Out-String).Trim()
if ($branch -ne $ExpectedBranch) { throw "Wrong branch: $branch. Expected $ExpectedBranch. No checkout changes made." }
$remote = ((Invoke-RahgardGit @('remote','get-url','origin')) | Out-String).Trim()
if ($remote -notmatch '(?i)AiDev168[/\\:]Ai_Tourism(\.git)?$') { throw "Unexpected git origin. Refuse to push to a different repository." }
& $script:GitExecutable -C $RepoRoot diff --quiet
if ($LASTEXITCODE -ne 0) { throw 'Tracked working-tree changes exist. Review/commit them separately before this handoff.' }
& $script:GitExecutable -C $RepoRoot diff --cached --quiet
if ($LASTEXITCODE -ne 0) { throw 'Existing staged changes found; refuse to mix them with this handoff.' }
$head = ((Invoke-RahgardGit @('rev-parse','HEAD')) | Out-String).Trim()
if ($CommitAndPush) {
    $remoteLine = ((Invoke-RahgardGit @('ls-remote','origin',("refs/heads/" + $ExpectedBranch))) | Out-String).Trim()
    $remoteSha = (($remoteLine -split '\s+')[0]).Trim()
    if ($remoteSha -notmatch '^[0-9a-fA-F]{40}$') {
        throw 'Could not verify the remote feature branch SHA; refusing commit/push.'
    }
    if ($head -ne $remoteSha) { throw "Local HEAD $head differs from origin $remoteSha; no force push. Ask Codex to reconcile." }
}
$temp = Join-Path ([IO.Path]::GetTempPath()) ('rahgard-handoff-' + [Guid]::NewGuid().ToString('N'))
New-Item -Path $temp -ItemType Directory | Out-Null
try {
    Expand-Archive -LiteralPath $BundleZip -DestinationPath $temp -Force
    $manifestPath = Join-Path $temp 'HANDOFF_MANIFEST.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) { throw 'Missing HANDOFF_MANIFEST.json' }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.schema -ne 'rahgard.local-handoff.v3' -or -not $manifest.files) { throw 'Unexpected handoff manifest schema' }
    $paths = New-Object 'System.Collections.Generic.List[string]'
    $copyPlan = New-Object System.Collections.ArrayList
    foreach ($file in $manifest.files) {
        $rel = [string]$file.path
        if ($PrivatePaths -contains $rel) { throw "Private source in manifest, refusing: $rel" }
        $destination = Repo-Path $rel
        $source = Join-Path $temp ($rel.Replace('/', [IO.Path]::DirectorySeparatorChar))
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Manifest source missing: $rel" }
        $expectedHash = ([string]$file.sha256).ToLowerInvariant()
        if ((Hash $source) -ne $expectedHash) { throw "Bundle SHA256 mismatch: $rel" }
        if (Test-Path -LiteralPath $destination -PathType Leaf) {
            if ((Hash $destination) -ne $expectedHash) {
                throw "Existing DIFFERENT repo file: $rel. Refusing overwrite; review and merge with Codex."
            }
        } else {
            [void]$copyPlan.Add(@{source=$source;destination=$destination;relative=$rel})
        }
        $paths.Add($rel)
    }
    if ($paths.Count -ne @($paths | Select-Object -Unique).Count) { throw 'Duplicate path in handoff manifest' }
    Write-Host ("Verified {0} manifest hashes; {1} new files to copy." -f $paths.Count, $copyPlan.Count)

    # Keep originals outside Git and preserve private checksums without viewing contents.
    $localAppData = $env:LOCALAPPDATA
    if (-not $localAppData) { throw 'LOCALAPPDATA is unavailable; cannot securely preserve local artifacts' }
    $recovery = Join-Path $localAppData ('Rahgard-Private-Handoff-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Path $recovery -Force | Out-Null
    $privateAudit = New-Object System.Collections.ArrayList
    foreach ($rel in $PrivatePaths) {
        $original = Repo-Path $rel
        if (-not (Test-Path -LiteralPath $original -PathType Leaf)) { continue }
        $safeName = ($rel -replace '[^A-Za-z0-9.-]', '_')
        $backup = Join-Path $recovery $safeName
        Copy-Item -LiteralPath $original -Destination $backup -ErrorAction Stop
        if ((Hash $original) -ne (Hash $backup)) { throw "Private backup verification failed: $rel" }
        [void]$privateAudit.Add(@{path=$rel;sha256=(Hash $original);backup_name=$safeName;published=$false})
    }
    $privateAudit | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $recovery 'PRIVATE_AUDIT.json') -Encoding UTF8
    Write-Host "Private artifacts backed up outside Git: $recovery"

    # Workspace-local ignore only, not .gitignore; the real files remain intact.
    $exclude = Join-Path $RepoRoot '.git/info/exclude'
    if (-not (Test-Path -LiteralPath $exclude -PathType Leaf)) { throw 'Expected .git/info/exclude missing' }
    $previous = Get-Content -LiteralPath $exclude -ErrorAction Stop
    foreach ($rel in $PrivatePaths) {
        if ($previous -notcontains $rel) { Add-Content -LiteralPath $exclude -Value $rel -Encoding UTF8 }
    }

    foreach ($item in $copyPlan) {
        $parent = Split-Path -Path $item.destination -Parent
        if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
            New-Item -Path $parent -ItemType Directory -Force | Out-Null
        }
        Copy-Item -LiteralPath $item.source -Destination $item.destination -ErrorAction Stop
    }
    foreach ($file in $manifest.files) {
        $destination = Repo-Path ([string]$file.path)
        if ((Hash $destination) -ne ([string]$file.sha256).ToLowerInvariant()) { throw "Installed hash verification failed: $($file.path)" }
    }
    Write-Host ('Installed/verified files: ' + $paths.Count)
    Write-Host 'Original screenshot and *.local.mjs were NOT staged, deleted or published.'
    if ($CommitAndPush) {
        # Git stages only the manifest allowlist, never user screenshots or other work.
        [void](Invoke-RahgardGit (@('add','--') + @($paths.ToArray())))
        [void](Invoke-RahgardGit @('diff','--cached','--check'))
        $staged = @(Invoke-RahgardGit @('diff','--cached','--name-only'))
        $unexpected = @($staged | Where-Object { $_ -and ($paths -notcontains $_) })
        if ($unexpected.Count -gt 0) { throw ('Unexpected staged files: ' + ($unexpected -join ', ')) }
        if (@($staged | Where-Object { $_ }).Count -eq 0) { Write-Host 'No new changes: everything already committed.' }
        else {
            [void](Invoke-RahgardGit @('commit','-m','docs(rahgard): add native-style partner forms and read-only schema documentation handoff'))
            [void](Invoke-RahgardGit @('push','origin',("HEAD:refs/heads/" + $ExpectedBranch)))
            Write-Host ('Pushed commit ' + ((Invoke-RahgardGit @('rev-parse','HEAD')) | Out-String).Trim())
        }
    } else { Write-Host 'Files installed. Review changes, then re-run with -CommitAndPush.' }
    Invoke-RahgardGit @('status','--short') | ForEach-Object { Write-Host $_ }
} finally {
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force }
}
