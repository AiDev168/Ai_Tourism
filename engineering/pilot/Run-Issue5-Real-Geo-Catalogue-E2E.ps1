# End-to-end real canonical POI acceptance in *disposable QA PostgreSQL 17 only*.
# This does not approve/publicly publish any destination or invoke Chat/RAG.
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$DatabaseRunner = Join-Path $ProjectRoot 'engineering\database-prep\scripts\Start-Disposable-Mvp-E2E.ps1'
$ContainerName = $null
$Result = 1

try {
    . $DatabaseRunner -ProjectRoot $ProjectRoot
    $ContainerName = $env:AI_TOURISM_MVP_E2E_CONTAINER
    if (-not $ContainerName -or $ContainerName -notmatch '^ai-tourism-mvp-pg17-[a-f0-9]{12}$') {
        throw 'Disposable PG17 did not return a task-owned container name.'
    }
    if (-not (Get-Command Stop-RemoveOwnedContainer -ErrorAction SilentlyContinue)) {
        throw 'Verified disposable database cleanup helper is unavailable.'
    }

    # Exercise actual canonical identities and the ordinary app-role read view.
    # The test writes ONLY to the newly created marker-validated disposable DB.
    $env:RAHGARD_RUN_GEO_QA = '1'
    $env:TOURISM_RAG_ENABLED = 'false'
    $env:ASSISTANT_INTEGRATION_TESTS = '1'
    Push-Location -LiteralPath (Join-Path $ProjectRoot 'backend')
    try {
        uv run pytest -p no:cacheprovider tests/test_rahgard_geo_visibility_db.py -q
        if ($LASTEXITCODE -ne 0) { throw 'The canonical POI QA publication test failed.' }
    }
    finally { Pop-Location }

    # Browser receives actual production view catalogue, not fake-identity
    # override or injected in-memory coordinates.
    $env:RAHGARD_REAL_GEO_E2E = '1'
    Push-Location -LiteralPath (Join-Path $ProjectRoot 'frontend')
    try {
        node scripts/traveler-e2e.mjs
        if ($LASTEXITCODE -ne 0) { throw 'Real-geo browser acceptance failed.' }
    }
    finally { Pop-Location }

    $Result = 0
    Write-Host 'PASS: canonical Fars POIs reached browser, FastAPI, PostgreSQL, and editable itinerary.' -ForegroundColor Green
}
catch {
    Write-Error 'Real-geo QA acceptance failed; see the individual guarded test output.'
    $Result = 1
}
finally {
    foreach ($key in @('RAHGARD_RUN_GEO_QA','RAHGARD_REAL_GEO_E2E','ASSISTANT_INTEGRATION_TESTS')) {
        Remove-Item -Path "Env:$key" -ErrorAction SilentlyContinue
    }
    if ($ContainerName -and (Get-Command Stop-RemoveOwnedContainer -ErrorAction SilentlyContinue)) {
        try {
            Stop-RemoveOwnedContainer $ContainerName
        }
        catch {
            # Docker --rm may have already deleted the verified exact container
            # after stop. Confirm actual absence before accepting this race.
            $names = & docker ps --all --filter "name=^$ContainerName$" --format '{{.Names}}' 2>$null
            if ($LASTEXITCODE -ne 0 -or @($names) -contains $ContainerName) {
                Write-Error 'Task-created disposable container remains or cleanup could not be verified.'
                $Result = 1
            }
        }
    }
}
exit $Result
