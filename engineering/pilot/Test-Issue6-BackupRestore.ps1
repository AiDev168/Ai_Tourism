[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$StatePath)

$ErrorActionPreference = 'Stop'
$state = Get-Content -LiteralPath (Resolve-Path -LiteralPath $StatePath) -Raw -Encoding UTF8 | ConvertFrom-Json
if ($state.purpose -ne 'internal-loopback-only-test' -or
    $state.database_container -notmatch '^ai-tourism-mvp-pg17-[a-f0-9]{12}$' -or
    $state.database_name -notmatch '^ai_tourism_auth_test_mvp_[a-f0-9]{12}$') {
    throw 'Refusing backup/restore outside the task-created disposable PostgreSQL instance.'
}
$runtime = [IO.Path]::GetFullPath([string]$state.runtime_directory)
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
if (-not $runtime.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -or
    $runtime -notmatch 'rahgard-issue6-pilot-[0-9a-f]{32}$') {
    throw 'State runtime is outside the task-owned temporary directory.'
}
$inspect = & docker inspect $state.database_container 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Task-created disposable database is not running.' }
$container = ($inspect | Out-String) | ConvertFrom-Json
if ($container[0].Config.Labels.'ai-tourism.disposable-mvp-e2e' -ne 'true') {
    throw 'Disposable database safety label does not match.'
}

$restoreDb = '{0}_restore' -f [string]$state.database_name
if ($restoreDb.Length -gt 63 -or $restoreDb -notmatch '^ai_tourism_auth_test_mvp_[a-f0-9]{12}_restore$') {
    throw 'Derived restore database name failed its safety check.'
}
$restoreExists = & docker exec $state.database_container psql -X -A -t -U ai_tourism_owner -d postgres `
    -c "SELECT COUNT(*) FROM pg_database WHERE datname='$restoreDb';"
if ($LASTEXITCODE -ne 0 -or ($restoreExists | Out-String).Trim() -ne '0') {
    throw 'Restore target already exists or could not be verified.'
}
$dumpName = 'issue6_pilot_' + [Guid]::NewGuid().ToString('N') + '.dump'
$containerDump = "/tmp/$dumpName"
$localDump = Join-Path $runtime $dumpName
$created = $false
try {
    & docker exec $state.database_container pg_dump -U ai_tourism_owner -d $state.database_name -Fc -f $containerDump
    if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed for the isolated pilot database.' }
    & docker cp "$($state.database_container):$containerDump" $localDump | Out-Null
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $localDump)) { throw 'Could not copy isolated backup into task temp.' }

    & docker exec $state.database_container createdb -U ai_tourism_owner -O ai_tourism_owner $restoreDb
    if ($LASTEXITCODE -ne 0) { throw 'Could not create exact isolated restore target.' }
    $created = $true
    & docker cp $localDump "$($state.database_container):$containerDump" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy backup into task-created database container.' }
    & docker exec $state.database_container pg_restore -U ai_tourism_owner -d $restoreDb --no-owner $containerDump
    if ($LASTEXITCODE -ne 0) { throw 'pg_restore failed on the exact disposable restore database.' }

    $check = & docker exec $state.database_container psql -X -A -t -U ai_tourism_owner -d $restoreDb `
        -c "SELECT (SELECT COUNT(*) FROM system.schema_migrations)=13 AND (SELECT COUNT(*) FROM public.ai_tourism_auth_test_marker)=1;"
    if ($LASTEXITCODE -ne 0 -or ($check | Out-String).Trim() -ne 't') {
        throw 'Restored database failed migration-ledger/test-marker validation.'
    }
    Write-Output 'PASS: pg_dump/pg_restore round trip preserved 13 migrations and the isolated safety marker.'
    Write-Output 'The temporary dump was removed after verification; no backup artifact was retained.'
}
finally {
    if ($created) {
        & docker exec $state.database_container dropdb --if-exists -U ai_tourism_owner $restoreDb | Out-Null
    }
    & docker exec $state.database_container rm -f $containerDump 2>$null | Out-Null
    if (Test-Path -LiteralPath $localDump) { Remove-Item -LiteralPath $localDump -Force }
}
