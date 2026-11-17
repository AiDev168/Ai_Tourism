param(
    [string]$Image = 'postgres:17-alpine'
)
$ErrorActionPreference = 'Stop'
$Container = 'rahgard-016-test-' + [Guid]::NewGuid().ToString('N').Substring(0,12)
$Marker = [Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N').Substring(0,16)
$Hash0013 = 'a' * 64
$MigrationHash = (Get-FileHash -Algorithm SHA256 (Join-Path $PSScriptRoot '..\..\..\engineering\pilot\sql\016_staging_invitation_auth.sql')).Hash.ToLowerInvariant()
$Migration = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\engineering\pilot\sql\016_staging_invitation_auth.sql')).Path
$created = $false
try {
    $id = & docker run -d --name $Container --network none `
        --tmpfs '/var/lib/postgresql/data:rw,noexec,nosuid,size=512m' `
        -e POSTGRES_DB=rahgard_pilot_vps_staging -e POSTGRES_USER=rahgard_db_owner `
        -e POSTGRES_PASSWORD=isolated-test-only postgres:17-alpine
    if ($LASTEXITCODE -ne 0) { throw 'Could not start the task-isolated, network-disabled PostgreSQL container.' }
    $created = $true
    $ready = $false
    for ($i=0; $i -lt 60; $i++) {
        & docker exec $Container pg_isready -U rahgard_db_owner -d rahgard_pilot_vps_staging *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'Isolated PostgreSQL did not become ready.' }
    $pre = @'
CREATE ROLE ai_tourism_app LOGIN;
CREATE SCHEMA system;
CREATE TABLE system.schema_migrations(migration_id text primary key, sha256 text not null);
CREATE SCHEMA identity;
CREATE TABLE identity.users(
 user_id uuid primary key default gen_random_uuid(), auth_subject text unique,
 email text, account_status text not null, is_synthetic boolean not null default false
);
CREATE TABLE identity.web_sessions(session_id uuid primary key default gen_random_uuid());
CREATE TABLE public.rahgard_private_pilot_marker(marker_value text primary key);
INSERT INTO public.rahgard_private_pilot_marker VALUES ('__MARKER__');
INSERT INTO system.schema_migrations VALUES ('0013_private_pilot_geo_audit', repeat('a',64));
'@.Replace('__MARKER__', $Marker)
    $pre | & docker exec -i -e PGPASSWORD=isolated-test-only $Container psql -X -h 127.0.0.1 -v ON_ERROR_STOP=1 -U rahgard_db_owner -d rahgard_pilot_vps_staging
    if ($LASTEXITCODE -ne 0) { throw 'Could not create isolated migration precondition fixture.' }
    $env:RAHGARD_PILOT_DATABASE_MARKER = $Marker
    $env:RAHGARD_PILOT_MIGRATION_0016_SHA256 = $MigrationHash
    Get-Content -Raw -Encoding UTF8 $Migration | & docker exec -i `
        -e "RAHGARD_PILOT_DATABASE_MARKER=$Marker" `
        -e "RAHGARD_PILOT_MIGRATION_0013_SHA256=$Hash0013" `
        -e "RAHGARD_PILOT_MIGRATION_0016_SHA256=$MigrationHash" `
        -e PGPASSWORD=isolated-test-only $Container psql -X -h 127.0.0.1 -v ON_ERROR_STOP=1 -U rahgard_db_owner -d rahgard_pilot_vps_staging
    if ($LASTEXITCODE -ne 0) { throw 'Migration 0016 failed in isolated PostgreSQL 17.' }
    $check = @'
SELECT CASE WHEN
 (SELECT count(*) FROM system.schema_migrations WHERE migration_id='0016_staging_invitation_auth')=1
 AND has_table_privilege('ai_tourism_app','identity.staging_invites','INSERT')
 AND NOT EXISTS (SELECT 1 FROM aclexplode((SELECT relacl FROM pg_class WHERE oid='identity.staging_password_credentials'::regclass)) a WHERE a.grantee=0 AND a.privilege_type='SELECT')
 AND pg_get_constraintdef((SELECT oid FROM pg_constraint WHERE conrelid='identity.staging_password_credentials'::regclass AND contype='c' LIMIT 1)) IS NOT NULL
 THEN 'PASS: migration row, invitation credential tables, restricted public access, and app inserts verified'
 ELSE 'FAIL' END;
'@
    $result = $check | & docker exec -i -e PGPASSWORD=isolated-test-only $Container psql -X -h 127.0.0.1 -A -t -U rahgard_db_owner -d rahgard_pilot_vps_staging
    if ($LASTEXITCODE -ne 0 -or $result -notmatch '^PASS:') { throw "Migration assertions failed: $result" }
    Write-Output $result
    Write-Output "Container: isolated, network=none, tmpfs only; PostgreSQL version:"
    & docker exec -e PGPASSWORD=isolated-test-only $Container psql -X -h 127.0.0.1 -A -t -U rahgard_db_owner -d rahgard_pilot_vps_staging -c 'SHOW server_version;'
}
finally {
    Remove-Item Env:RAHGARD_PILOT_DATABASE_MARKER -ErrorAction SilentlyContinue
    Remove-Item Env:RAHGARD_PILOT_MIGRATION_0016_SHA256 -ErrorAction SilentlyContinue
    if ($created) { & docker rm -f $Container *> $null }
}
