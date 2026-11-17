param([string]$Image = 'postgres:17-alpine')
$ErrorActionPreference = 'Stop'
$Container = 'rahgard-017-test-' + [Guid]::NewGuid().ToString('N').Substring(0,12)
$Marker = [Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N').Substring(0,16)
$Migration = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\engineering\pilot\sql\017_provisional_itineraries.sql')).Path
$MigrationHash = (Get-FileHash -Algorithm SHA256 $Migration).Hash.ToLowerInvariant()
$Migration0016 = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\engineering\pilot\sql\016_staging_invitation_auth.sql')).Path
$Hash0016 = (Get-FileHash -Algorithm SHA256 $Migration0016).Hash.ToLowerInvariant()
$created = $false
try {
    $id = & docker run -d --name $Container --network none `
        --tmpfs '/var/lib/postgresql/data:rw,noexec,nosuid,size=512m' `
        -e POSTGRES_DB=rahgard_pilot_vps_staging -e POSTGRES_USER=rahgard_db_owner `
        -e POSTGRES_PASSWORD=isolated-test-only $Image
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
CREATE TABLE identity.users(user_id uuid primary key);
CREATE SCHEMA travel;
CREATE TABLE travel.trips(
  trip_id uuid primary key,
  user_id uuid not null references identity.users(user_id) on delete cascade,
  duration_days integer
);
CREATE TABLE public.rahgard_private_pilot_marker(marker_value text primary key);
INSERT INTO public.rahgard_private_pilot_marker VALUES ('__MARKER__');
INSERT INTO system.schema_migrations VALUES ('0016_staging_invitation_auth','__HASH0016__');
INSERT INTO identity.users(user_id) VALUES
 ('11111111-1111-4111-8111-111111111111'),
 ('22222222-2222-4222-8222-222222222222');
INSERT INTO travel.trips(trip_id,user_id,duration_days) VALUES
 ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','11111111-1111-4111-8111-111111111111',15),
 ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','22222222-2222-4222-8222-222222222222',4);
'@.Replace('__MARKER__', $Marker).Replace('__HASH0016__', $Hash0016)
    $pre | & docker exec -i -e PGPASSWORD=isolated-test-only $Container psql -X -h 127.0.0.1 -v ON_ERROR_STOP=1 -U rahgard_db_owner -d rahgard_pilot_vps_staging
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the isolated migration precondition fixture.' }
    Get-Content -Raw -Encoding UTF8 $Migration | & docker exec -i `
        -e "RAHGARD_PILOT_DATABASE_MARKER=$Marker" `
        -e "RAHGARD_PILOT_MIGRATION_0016_SHA256=$Hash0016" `
        -e "RAHGARD_PILOT_MIGRATION_0017_SHA256=$MigrationHash" `
        -e PGPASSWORD=isolated-test-only $Container psql -X -h 127.0.0.1 -v ON_ERROR_STOP=1 -U rahgard_db_owner -d rahgard_pilot_vps_staging
    if ($LASTEXITCODE -ne 0) { throw 'Migration 0017 failed in isolated PostgreSQL 17.' }
    $check = @'
INSERT INTO travel.provisional_itineraries(trip_id,user_id,day_count,locale,days)
VALUES ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','11111111-1111-4111-8111-111111111111',15,'fa-IR','[]');
SELECT CASE WHEN
 (SELECT count(*) FROM system.schema_migrations WHERE migration_id='0017_provisional_itineraries')=1
 AND has_table_privilege('ai_tourism_app','travel.provisional_itineraries','INSERT')
 AND NOT EXISTS (SELECT 1 FROM aclexplode((SELECT relacl FROM pg_class
     WHERE oid='travel.provisional_itineraries'::regclass)) a
     WHERE a.grantee=0 AND a.privilege_type='SELECT')
 AND (SELECT count(*) FROM travel.provisional_itineraries)=1
 THEN 'PASS: additive migration, app grants, public isolation, and draft persistence verified'
 ELSE 'FAIL' END;
DELETE FROM travel.trips WHERE trip_id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
SELECT CASE WHEN (SELECT count(*) FROM travel.provisional_itineraries)=0
 THEN 'PASS: trip deletion cascades provisional draft'
 ELSE 'FAIL: draft survived trip deletion' END;
'@
    $result = $check | & docker exec -i -e PGPASSWORD=isolated-test-only $Container psql -X -h 127.0.0.1 -A -t -U rahgard_db_owner -d rahgard_pilot_vps_staging
    $resultText = $result -join [Environment]::NewLine
    if ($LASTEXITCODE -ne 0 -or -not $resultText.Contains('PASS: additive migration') -or -not $resultText.Contains('PASS: trip deletion')) {
        throw "Migration assertions failed: $result"
    }
    Write-Output $resultText
    Write-Output 'Container: isolated, network=none, PostgreSQL data on tmpfs only.'
    & docker exec -e PGPASSWORD=isolated-test-only $Container psql -X -h 127.0.0.1 -A -t -U rahgard_db_owner -d rahgard_pilot_vps_staging -c 'SHOW server_version;'
}
finally {
    if ($created) { & docker rm -f $Container *> $null }
}
