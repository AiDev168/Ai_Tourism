[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$StatePath)

$ErrorActionPreference = 'Stop'
$resolvedState = (Resolve-Path -LiteralPath $StatePath).Path
$state = Get-Content -LiteralPath $resolvedState -Raw -Encoding UTF8 | ConvertFrom-Json
if ($state.purpose -ne 'internal-loopback-only-test' -or
    $state.database_container -notmatch '^ai-tourism-mvp-pg17-[a-f0-9]{12}$' -or
    $state.https_url -notmatch '^https://localhost:[0-9]{4,5}/$' -or
    [string]$state.auth_enabled -ne 'False' -or [string]$state.rag_enabled -ne 'False' -or
    [string]$state.chat_enabled -ne 'False' -or [string]$state.migrations -ne '0000-0012') {
    throw 'State file is not a valid Issue 6 local pilot instance.'
}
$runtime = [IO.Path]::GetFullPath([string]$state.runtime_directory)
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
if (-not $runtime.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -or
    $runtime -notmatch 'rahgard-issue6-pilot-[0-9a-f]{32}$' -or
    $resolvedState -ne [IO.Path]::GetFullPath((Join-Path $runtime 'state.json'))) {
    throw 'State file is not in its recorded task-owned temporary folder.'
}

foreach ($field in @(
    @('api_listener_pid','api_listener_start_utc'),
    @('api_pid','api_start_utc'),
    @('proxy_pid','proxy_start_utc')
)) {
    $process = Get-Process -Id ([int]$state.($field[0])) -ErrorAction SilentlyContinue
    if ($process) {
        $started = $process.StartTime.ToUniversalTime().ToString('o')
        if ($started -eq [string]$state.($field[1])) {
            Stop-Process -Id $process.Id -Force
        }
    }
}

$existingNames = @(& docker container ls --all --format '{{.Names}}')
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect Docker container names for safe cleanup.' }
if ($existingNames -contains [string]$state.database_container) {
    $inspection = & docker inspect $state.database_container
    if ($LASTEXITCODE -ne 0) { throw 'Could not verify the task-owned database container.' }
    $container = ($inspection | Out-String) | ConvertFrom-Json
    if ($container[0].Name -ne "/$($state.database_container)" -or
        $container[0].Config.Labels.'ai-tourism.disposable-mvp-e2e' -ne 'true') {
        throw 'Refusing to stop a container without this runner’s disposable safety label.'
    }
    & docker stop $state.database_container | Out-Null
    $stopCode = $LASTEXITCODE
    $remainingNames = @(& docker container ls --all --format '{{.Names}}')
    if ($LASTEXITCODE -ne 0) { throw 'Could not verify database container cleanup.' }
    if ($remainingNames -contains [string]$state.database_container) {
        $remainingContainer = ($remaining | Out-String) | ConvertFrom-Json
        if ($remainingContainer[0].Name -ne "/$($state.database_container)" -or
            $remainingContainer[0].Config.Labels.'ai-tourism.disposable-mvp-e2e' -ne 'true') {
            throw 'Refusing explicit removal because the container identity changed.'
        }
        & docker rm $state.database_container | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Failed to remove the verified task-created database container.' }
    }
    elseif ($stopCode -ne 0) {
        throw 'Failed to stop or verify removal of the task-created disposable database.'
    }
}

if (Test-Path -LiteralPath $runtime) { Remove-Item -LiteralPath $runtime -Recurse -Force }
Write-Output 'STOPPED: only recorded Issue 6 loopback processes/container were stopped; task temp files removed.'
