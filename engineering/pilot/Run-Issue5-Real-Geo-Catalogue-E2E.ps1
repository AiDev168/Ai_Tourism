# Real canonical Fars POI acceptance in an isolated disposable PostgreSQL 17.
# Does NOT authorize owner publication or call external Chat/RAG services.
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$DatabaseRunner = Join-Path $ProjectRoot 'engineering\database-prep\scripts\Start-Disposable-Mvp-E2E.ps1'
$ContainerName = $null
$Result = 1

# The dot-sourced disposable DB helper exports session variables. Restore ALL
# touched keys, including owner password and marker, even on failures. Keeping
# stale AUTH_TEST_DATABASE_* in the user's session causes unrelated pytest
# integration cases to connect to a now-deleted PostgreSQL container.
$EnvironmentKeys = @(
    'AUTH_INTEGRATION_TESTS',
    'AUTH_TEST_DATABASE_HOST', 'AUTH_TEST_DATABASE_PORT', 'AUTH_TEST_DATABASE_NAME',
    'AUTH_TEST_DATABASE_USER', 'AUTH_TEST_DATABASE_PASSWORD',
    'AUTH_TEST_DATABASE_OWNER_PASSWORD', 'AUTH_TEST_DATABASE_MARKER',
    'AI_TOURISM_MVP_E2E_CONTAINER',
    'RAHGARD_RUN_GEO_QA', 'RAHGARD_REAL_GEO_E2E',
    'ASSISTANT_INTEGRATION_TESTS', 'TOURISM_RAG_ENABLED'
)
$OriginalEnvironment = @{}
foreach ($Key in $EnvironmentKeys) {
    $OriginalEnvironment[$Key] = [Environment]::GetEnvironmentVariable($Key, 'Process')
}

try {
    . $DatabaseRunner -ProjectRoot $ProjectRoot
    $ContainerName = $env:AI_TOURISM_MVP_E2E_CONTAINER
    if (-not $ContainerName -or $ContainerName -notmatch '^ai-tourism-mvp-pg17-[a-f0-9]{12}$') {
        throw 'Disposable PostgreSQL did not return a task-owned container.'
    }
    if (-not (Get-Command Stop-RemoveOwnedContainer -ErrorAction SilentlyContinue)) {
        throw 'Verified disposable PostgreSQL cleanup helper is missing.'
    }

    # QA-only activation: exact seeded destination identities, NOT real owner
    # approval for a persistent catalogue.
    $env:RAHGARD_RUN_GEO_QA = '1'
    $env:TOURISM_RAG_ENABLED = 'false'
    $env:ASSISTANT_INTEGRATION_TESTS = '1'

    Push-Location -LiteralPath (Join-Path $ProjectRoot 'backend')
    try {
        uv run pytest -p no:cacheprovider tests/test_rahgard_geo_visibility_db.py -q
        if ($LASTEXITCODE -ne 0) {
            throw 'Canonical Fars POI disposable PG17 integration failed.'
        }
    }
    finally { Pop-Location }

    # The browser sees real canonical production-view identities and
    # coordinate roles from the SAME temporary PostgreSQL, not fake aliases.
    $env:RAHGARD_REAL_GEO_E2E = '1'
    Push-Location -LiteralPath (Join-Path $ProjectRoot 'frontend')
    try {
        node scripts/traveler-e2e.mjs
        if ($LASTEXITCODE -ne 0) {
            throw 'Real-catalogue browser acceptance failed.'
        }
    }
    finally { Pop-Location }

    $Result = 0
    Write-Host 'PASS: canonical geo POIs reached PWA, FastAPI, PostgreSQL and editable itinerary.' -ForegroundColor Green
}
catch {
    # Write-Error with ErrorActionPreference=Stop aborts before exit $Result,
    # leaving LASTEXITCODE from docker stop (often 0). Use a warning instead.
    $Result = 1
    Write-Warning 'FAIL: isolated geo browser acceptance did not complete; see the preceding process result.'
}
finally {
    if ($ContainerName) {
        if ($ContainerName -notmatch '^ai-tourism-mvp-pg17-[a-f0-9]{12}$') {
            $Result = 1
            Write-Warning 'FAIL: refusing to clean a container outside the exact disposable QA contract.'
        }
        elseif (-not (Get-Command Stop-RemoveOwnedContainer -ErrorAction SilentlyContinue)) {
            $Result = 1
            Write-Warning 'FAIL: cannot verify cleanup helper availability.'
        }
        else {
            try {
                Stop-RemoveOwnedContainer $ContainerName
            }
            catch {
                # Docker --rm may remove the validated exact container before
                # the cleanup helper can inspect it. Verify absence below.
            }
            try {
                $Remaining = @(& docker ps --all --filter "name=^$ContainerName$" --format '{{.Names}}' 2>$null)
                if ($LASTEXITCODE -ne 0 -or $Remaining -contains $ContainerName) {
                    $Result = 1
                    Write-Warning 'FAIL: disposable QA container still exists or Docker verification failed.'
                }
            }
            catch {
                $Result = 1
                Write-Warning 'FAIL: Docker cleanup verification could not run.'
            }
        }
    }

    foreach ($Key in $EnvironmentKeys) {
        [Environment]::SetEnvironmentVariable($Key, $OriginalEnvironment[$Key], 'Process')
    }
}
# Always reached on normal test failures; failed E2E returns exit code 1.
exit $Result
