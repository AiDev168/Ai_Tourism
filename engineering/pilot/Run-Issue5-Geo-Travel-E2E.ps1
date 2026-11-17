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
    if (-not $ContainerName) { throw 'Guarded disposable PostgreSQL did not provide its task container name.' }
    if (-not (Get-Command Stop-RemoveOwnedContainer -ErrorAction SilentlyContinue)) {
        throw 'Guarded database runner did not expose its verified cleanup function.'
    }

    $env:ASSISTANT_INTEGRATION_TESTS = '1'
    $env:TOURISM_RAG_ENABLED = 'false'
    Push-Location -LiteralPath (Join-Path $ProjectRoot 'frontend')
    try {
        node scripts/traveler-e2e.mjs
        $Result = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}
catch {
    Write-Error 'Issue 5 geographic traveler E2E could not complete. See the safe runner output above.'
    $Result = 1
}
finally {
    if ($ContainerName -and (Get-Command Stop-RemoveOwnedContainer -ErrorAction SilentlyContinue)) {
        try {
            # The database helper validates the exact generated name and safety
            # label. It also handles Docker --rm deleting the container first.
            Stop-RemoveOwnedContainer $ContainerName
        }
        catch {
            # Docker may remove the container between the helper's inspect and
            # stop/rm calls because the runner uses --rm. Treat only a confirmed
            # missing exact task container as cleanup success; a live container
            # or unavailable Docker daemon remains a hard failure.
            if ($ContainerName -notmatch '^ai-tourism-mvp-pg17-[a-f0-9]{12}$') {
                Write-Error 'Refusing cleanup verification for an unexpected container name.'
                $Result = 1
            }
            try {
                $remainingNames = & docker ps --all --filter "name=^$ContainerName$" --format '{{.Names}}'
                $dockerCheckCode = $LASTEXITCODE
            }
            catch {
                $remainingNames = @()
                $dockerCheckCode = 1
            }
            if ($dockerCheckCode -ne 0) {
                Write-Error 'Docker could not verify removal of the task-created database container.'
                $Result = 1
            }
            elseif (@($remainingNames) -contains $ContainerName) {
                Write-Error 'The task-created disposable database container still exists after cleanup.'
                $Result = 1
            }
            else {
                Write-Host 'Disposable database container was already removed by Docker --rm.'
            }
        }
    }
}

exit $Result
