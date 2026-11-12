<#
.SYNOPSIS
    Exercise Migration 0015 in a fresh, labelled, loopback-only PG17 tmpfs container.
.DESCRIPTION
    Does not connect to the persistent local pilot or any pre-existing container.
    The only container this script may stop/remove is the random task-created
    container bearing the exact `rahgard.p15.disposable=true` label.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..\..')).Path
$Migration = Join-Path $ProjectRoot 'engineering\pilot\sql\015_ai_provider_admin.sql'
$PriorMigration = Join-Path $ProjectRoot 'engineering\pilot\sql\014_local_owner_login.sql'
$Image = 'ai-tourism-postgres:17-postgis36-vector087'
$Suffix = [guid]::NewGuid().ToString('N').Substring(0,12)
$Container = "rahgard-p15-isolated-$Suffix"
$Database = "rahgard_pilot_test_015_$Suffix"
$Marker = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
$PostgresPassword = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
$Label = 'rahgard.p15.disposable=true'
$Created = $false

function Assert-Exit([string]$Message) {
    if ($LASTEXITCODE -ne 0) { throw $Message }
}
function Invoke-Psql([string]$Sql, [string]$DatabaseName = $Database, [string]$Role = 'postgres', [string]$Password = $PostgresPassword, [switch]$AsFile) {
    $psqlArgs = @('exec','-i','-e',"PGPASSWORD=$Password")
    foreach ($name in @('RAHGARD_PILOT_DATABASE_MARKER','RAHGARD_PILOT_MIGRATION_0014_SHA256','RAHGARD_PILOT_MIGRATION_0015_SHA256')) {
        $value = [Environment]::GetEnvironmentVariable($name,'Process')
        if ($value) { $psqlArgs += @('-e',"$name=$value") }
    }
    $psqlArgs += @($Container,'psql','-h','127.0.0.1','-X','-v','ON_ERROR_STOP=1','-q','-U',$Role,'-d',$DatabaseName)
    if ($AsFile) { $Sql | & docker @psqlArgs } else { & docker @psqlArgs '-c' $Sql }
    Assert-Exit "Isolated psql command failed against '$DatabaseName'."
}
function Get-Scalar([string]$Sql, [string]$DatabaseName = $Database) {
    $value = & docker exec -e "PGPASSWORD=$PostgresPassword" $Container psql -h 127.0.0.1 -X -A -t -v ON_ERROR_STOP=1 -U postgres -d $DatabaseName -c $Sql
    Assert-Exit "Isolated SQL verification failed against '$DatabaseName'."
    return (($value | Out-String).Trim())
}
function Assert-OwnedContainer {
    $raw = & docker inspect $Container 2>$null
    if ($LASTEXITCODE -ne 0) { return $false }
    $object = @($raw | ConvertFrom-Json)[0]
    if ($object.Name -ne "/$Container" -or $object.Config.Labels.'rahgard.p15.disposable' -ne 'true') {
        throw 'Container identity or disposable label changed; refusing cleanup.'
    }
    return $true
}

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker CLI is unavailable.' }
    if (-not (Test-Path -LiteralPath $Migration) -or -not (Test-Path -LiteralPath $PriorMigration)) {
        throw 'Migration 0014 or 0015 source file is missing.'
    }
    $imageId = (& docker image inspect $Image --format '{{.Id}}' 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $imageId) { throw 'Required PostgreSQL 17 image is not already present; this test does not pull images.' }
    $existing = & docker container ls --all --quiet --filter "name=^/$Container$"
    Assert-Exit 'Could not check the generated exact container name.'
    if ($existing) { throw 'Generated disposable container name already exists; refusing to touch it.' }

    & docker run --detach --rm --name $Container --label $Label --publish '127.0.0.1::5432' `
        --tmpfs '/var/lib/postgresql/data:rw,noexec,nosuid,size=512m' `
        --env 'POSTGRES_DB=postgres' --env 'POSTGRES_USER=postgres' --env "POSTGRES_PASSWORD=$PostgresPassword" $Image | Out-Null
    Assert-Exit 'Could not start isolated disposable PostgreSQL.'
    $Created = $true
    if (-not (Assert-OwnedContainer)) { throw 'Created disposable container could not be verified.' }
    $portText = (& docker port $Container 5432/tcp | Out-String).Trim()
    Assert-Exit 'Could not discover loopback port for the disposable database.'
    if ($portText -notmatch '^127\.0\.0\.1:([0-9]{1,5})$') {
        throw 'Disposable database port is not a unique loopback port or conflicts with the forbidden shared port.'
    }
    $Port = [int]$Matches[1]
    if ($Port -eq 55433) { throw 'Disposable database port conflicts with the forbidden shared port.' }
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        & docker exec $Container pg_isready -h 127.0.0.1 -U postgres -d postgres | Out-Null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw 'Disposable PostgreSQL did not become ready.' }
    $version = [int](Get-Scalar "SELECT current_setting('server_version_num')" 'postgres')
    if ($version -lt 170000 -or $version -ge 180000) { throw 'Disposable server is not PostgreSQL 17.' }
    Invoke-Psql "CREATE DATABASE $Database;" 'postgres'

    $setup = @'
CREATE ROLE ai_tourism_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE p15_migrator NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT CREATE ON DATABASE __DATABASE__ TO p15_migrator;
CREATE SCHEMA system;
CREATE TABLE system.schema_migrations(migration_id TEXT PRIMARY KEY, sha256 CHAR(64) NOT NULL);
CREATE SCHEMA identity;
CREATE TABLE identity.users(user_id UUID PRIMARY KEY);
CREATE TABLE identity.web_sessions(session_id UUID PRIMARY KEY);
CREATE TABLE public.rahgard_private_pilot_marker(marker_value TEXT NOT NULL);
INSERT INTO public.rahgard_private_pilot_marker VALUES ('__MARKER__');
GRANT USAGE ON SCHEMA system TO p15_migrator;
GRANT SELECT,INSERT ON system.schema_migrations TO p15_migrator;
GRANT USAGE,CREATE ON SCHEMA identity TO p15_migrator;
GRANT SELECT ON identity.users,identity.web_sessions TO p15_migrator;
GRANT REFERENCES(user_id) ON identity.users TO p15_migrator;
GRANT REFERENCES(session_id) ON identity.web_sessions TO p15_migrator;
GRANT SELECT ON public.rahgard_private_pilot_marker TO p15_migrator;
'@.Replace('__DATABASE__',$Database).Replace('__MARKER__',$Marker)
    Invoke-Psql $setup $Database -AsFile
    $priorHash = (Get-FileHash -LiteralPath $PriorMigration -Algorithm SHA256).Hash.ToLowerInvariant()
    Invoke-Psql "INSERT INTO system.schema_migrations(migration_id,sha256) VALUES ('0014_local_owner_login','$priorHash')" $Database

    $migrationHash = (Get-FileHash -LiteralPath $Migration -Algorithm SHA256).Hash.ToLowerInvariant()
    $migrationText = Get-Content -LiteralPath $Migration -Raw -Encoding UTF8
    # SET ROLE leaves the migration guard's current_user as the least-privilege migrator.
    $wrapper = "\set ON_ERROR_STOP on`nSET ROLE p15_migrator;`n" + $migrationText + "`nRESET ROLE;`n"
    $env:RAHGARD_PILOT_DATABASE_MARKER = $Marker
    $env:RAHGARD_PILOT_MIGRATION_0014_SHA256 = $priorHash
    $env:RAHGARD_PILOT_MIGRATION_0015_SHA256 = $migrationHash
    try { Invoke-Psql $wrapper $Database -AsFile }
    finally {
        Remove-Item Env:\RAHGARD_PILOT_DATABASE_MARKER,Env:\RAHGARD_PILOT_MIGRATION_0014_SHA256,Env:\RAHGARD_PILOT_MIGRATION_0015_SHA256 -ErrorAction SilentlyContinue
    }

    $integrity = Get-Scalar "SELECT (SELECT count(*) FROM ai_provider.active_routes),(SELECT count(*) FROM ai_provider.fallback_policy WHERE enabled),(SELECT has_table_privilege('ai_tourism_app','identity.ai_provider_admin_grants','INSERT')),(SELECT count(*) FROM information_schema.columns WHERE table_schema='ai_provider' AND column_name ILIKE '%secret%value%'),(SELECT sha256 FROM system.schema_migrations WHERE migration_id='0015_ai_provider_admin')"
    $expected = "4|0|f|0|$migrationHash"
    if ($integrity -ne $expected) { throw "Migration invariants failed (observed: $integrity)." }
    $appChecks = & docker exec -e "PGPASSWORD=$PostgresPassword" $Container psql -h 127.0.0.1 -X -A -t -v ON_ERROR_STOP=1 -U postgres -d $Database -c "SELECT has_table_privilege('ai_tourism_app','ai_provider.active_routes','SELECT'),has_table_privilege('ai_tourism_app','identity.ai_provider_admin_grants','SELECT'),has_table_privilege('ai_tourism_app','ai_provider.audit_events','UPDATE')"
    Assert-Exit 'Application-role privilege query failed.'
    if (($appChecks | Out-String).Trim() -ne 't|t|f') { throw 'Least-privilege assertions failed.' }
    Write-Host "PASS: PG17=$version; database=$Database; loopback_port=$Port; marker_guard=passed; migration_sha256=$migrationHash; active_routes=4; fallback_enabled=0; app_cannot_grant_admin=passed." -ForegroundColor Green
}
finally {
    Remove-Item Env:\RAHGARD_PILOT_DATABASE_MARKER,Env:\RAHGARD_PILOT_MIGRATION_0014_SHA256,Env:\RAHGARD_PILOT_MIGRATION_0015_SHA256 -ErrorAction SilentlyContinue
    if ($Created -and (Assert-OwnedContainer)) {
        & docker stop $Container | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Failed to stop task-created isolated test container.' }
        $present = & docker container ls --all --quiet --filter "name=^/$Container$"
        Assert-Exit 'Could not verify isolated test cleanup.'
        if ($present) {
            if (-not (Assert-OwnedContainer)) { throw 'Container changed identity during cleanup; refusing removal.' }
            & docker rm $Container | Out-Null
            Assert-Exit 'Could not remove task-created isolated test container.'
        }
    }
}
if ((& docker container ls --all --quiet --filter "name=^/$Container$").Count -ne 0) {
    throw 'Task-created disposable container remains after cleanup.'
}
Write-Host 'PASS: disposable container cleanup verified.' -ForegroundColor Green
