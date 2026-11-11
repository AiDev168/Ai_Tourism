[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$modulePath = Join-Path $here 'Rahgard.LocalPilot.psm1'
$runnerPath = Join-Path $here 'Rahgard-LocalPilot.ps1'
$parseFailures = @()
foreach ($file in @($modulePath,$runnerPath,$PSCommandPath)) {
    $tokens = $null; $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($file,[ref]$tokens,[ref]$errors)
    foreach ($errorItem in $errors) { $parseFailures += "$([IO.Path]::GetFileName($file)):$($errorItem.Extent.StartLineNumber): $($errorItem.Message)" }
}
if ($parseFailures.Count) { throw ('PowerShell parse errors: ' + ($parseFailures -join '; ')) }

Import-Module $modulePath -Force
$paths = Get-LocalPilotPaths 'C:\RahgardStaticTest\private-data'
$expectedRepository = [IO.Path]::GetFullPath((Join-Path $here '..\..\..'))
if (-not [string]::Equals($paths.RepoRoot,$expectedRepository,[StringComparison]::OrdinalIgnoreCase)) {
    throw "Repository root calculation failed: $($paths.RepoRoot)"
}
if ($paths.Root -eq $expectedRepository -or $paths.Root.StartsWith($expectedRepository.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Allowed local data root overlaps the repository.'
}

$rejected = 0
$badRoots = @(
    $expectedRepository,
    (Join-Path $expectedRepository 'private-data'),
    [IO.Directory]::GetParent($expectedRepository).FullName,
    '\\example.invalid\share\rahgard',
    'relative\rahgard'
)
foreach ($badRoot in $badRoots) {
    $wasRejected = $false
    try { $null = Get-LocalPilotPaths $badRoot } catch { $wasRejected = $true }
    if (-not $wasRejected) { throw "Unsafe data root was accepted: $badRoot" }
    $rejected++
}

$runner = Get-Content -LiteralPath $runnerPath -Raw -Encoding UTF8
$module = Get-Content -LiteralPath $modulePath -Raw -Encoding UTF8
$requiredPatterns = @(
    'POSTGRES_DB=''?\s*\+\s*\$Paths\.Database',
    "--restart','unless-stopped",
    '127\.0\.0\.1:\$DatabasePort',
    'HostConfig\.AutoRemove',
    'GRANT USAGE, CREATE ON SCHEMA tiger, topology TO ai_tourism_restore',
    'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA tiger, topology TO ai_tourism_restore',
    'CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder',
    "ContainerInherit.*ObjectInherit",
    'PGSSLMODE=.verify-full.',
    'pg_isready -U ai_tourism_owner -d \$Paths\.Database',
    'Assert-LocalPilotDatabaseTls',
    '\$PSCmdlet\.ShouldProcess\('
)
foreach ($pattern in $requiredPatterns) {
    if (($runner + "`n" + $module) -notmatch $pattern) { throw "Required static safety invariant is absent: $pattern" }
}
if (($runner + "`n" + $module) -match "--rm|--volume|--tmpfs|55433\s*[:=]\s*5432") {
    throw 'Static review found an auto-remove, named/anonymous volume, tmpfs, or shared-port configuration.'
}
if (-not $runner.Contains("'BootstrapOwner'") -or -not $runner.Contains("'ResetOwner'") -or
    $runner -notmatch '\x27Restore\x27\s*\{\s*if\s*\(\$PSCmdlet\.ShouldProcess') {
    throw 'One or more mutating lifecycle actions lack a guarded dispatcher entry.'
}
if ($paths.Root -and (Test-Path -LiteralPath $paths.Root)) { throw 'Static path test unexpectedly created its proposed data root.' }

[pscustomobject]@{
    status='passed'; parsed_files=3; unsafe_data_roots_rejected=$rejected
    repository_root=$paths.RepoRoot; proposed_data_root_created=$false
    docker_contacted=$false; database_contacted=$false
}
