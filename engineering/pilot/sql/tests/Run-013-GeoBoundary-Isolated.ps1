<# Focused 0013 test. Creates only a new guarded tmpfs PG17 container and a
   private-test database inside it. Never targets an existing service. #>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..\..')).Path
$Runner = Join-Path $ProjectRoot 'engineering\database-prep\scripts\Start-Disposable-Mvp-E2E.ps1'
$container = $null
try {
    . $Runner -ProjectRoot $ProjectRoot
    $container = $env:AI_TOURISM_MVP_E2E_CONTAINER
    $sourceDb = $env:AUTH_TEST_DATABASE_NAME
    if ($container -notmatch '^ai-tourism-mvp-pg17-([a-f0-9]{12})$' -or
        $sourceDb -notmatch '^ai_tourism_auth_test_mvp_[a-f0-9]{12}$' -or
        $env:AUTH_TEST_DATABASE_HOST -ne '127.0.0.1' -or
        [int]$env:AUTH_TEST_DATABASE_PORT -eq 55433) { throw 'Disposable identity guard failed.' }
    $suffix = $Matches[1]
    # Extract the suffix again: the source-database regex above resets $Matches.
    $suffix = $container.Substring($container.Length - 12)
    $pilotDb = 'rahgard_pilot_qa_' + $suffix
    $labelJson = & docker inspect --format '{{json .Config.Labels}}' $container
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect disposable container label.' }
    $labels = ($labelJson | Out-String) | ConvertFrom-Json
    if ($labels.'ai-tourism.disposable-mvp-e2e' -ne 'true') { throw 'Disposable container label mismatch.' }

    & docker exec $container psql -X -v ON_ERROR_STOP=1 -q -U ai_tourism_owner -d postgres -c "CREATE DATABASE $pilotDb TEMPLATE $sourceDb"
    if ($LASTEXITCODE -ne 0) { throw 'Private-test database creation failed.' }
    $marker = $env:AUTH_TEST_DATABASE_MARKER
    $ddlPassword = Hex 24
    $publisherPassword = Hex 24
    $markerHash = [BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($marker))).Replace('-', '').ToLowerInvariant()
    $decisionHash = 'a' * 64
    $setup = @'
\set ON_ERROR_STOP on
\getenv marker RAHGARD_PILOT_DATABASE_MARKER
\getenv ddl_password GEO_TEST_DDL_PASSWORD
\getenv publisher_password GEO_TEST_PUBLISHER_PASSWORD
CREATE TABLE public.rahgard_private_pilot_marker(marker_value TEXT NOT NULL);
INSERT INTO public.rahgard_private_pilot_marker VALUES (:'marker');
CREATE ROLE rahgard_pilot_ddl_owner LOGIN PASSWORD :'ddl_password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_geo_publisher LOGIN PASSWORD :'publisher_password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_geo_executor NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT rahgard_pilot_geo_executor TO rahgard_pilot_ddl_owner;
GRANT USAGE ON SCHEMA knowledge, operations, system, public TO rahgard_pilot_ddl_owner;
GRANT USAGE ON SCHEMA knowledge, operations, public TO rahgard_pilot_geo_executor;
GRANT CREATE ON SCHEMA operations TO rahgard_pilot_ddl_owner;
GRANT CREATE ON SCHEMA operations TO rahgard_pilot_geo_executor;
GRANT SELECT ON knowledge.destinations, knowledge.destination_sources, knowledge.knowledge_sources,
    system.schema_migrations, public.rahgard_private_pilot_marker TO rahgard_pilot_ddl_owner;
GRANT SELECT ON knowledge.destinations, knowledge.destination_sources, knowledge.knowledge_sources,
    public.rahgard_private_pilot_marker TO rahgard_pilot_geo_executor;
GRANT INSERT ON system.schema_migrations TO rahgard_pilot_ddl_owner;
GRANT UPDATE(status,updated_at), REFERENCES(destination_key) ON knowledge.destinations TO rahgard_pilot_ddl_owner;
GRANT UPDATE(status,updated_at) ON knowledge.destinations TO rahgard_pilot_geo_executor;
GRANT USAGE ON SCHEMA operations TO rahgard_pilot_geo_publisher;
GRANT USAGE ON SCHEMA knowledge TO rahgard_pilot_geo_publisher;
'@
    $setup | & docker exec -i -e "RAHGARD_PILOT_DATABASE_MARKER=$marker" -e "GEO_TEST_DDL_PASSWORD=$ddlPassword" -e "GEO_TEST_PUBLISHER_PASSWORD=$publisherPassword" $container psql -X -v ON_ERROR_STOP=1 -q -U ai_tourism_owner -d $pilotDb
    if ($LASTEXITCODE -ne 0) { throw 'Private-test roles or marker setup failed.' }
    $migration = Join-Path $ProjectRoot 'engineering\pilot\sql\013_private_pilot_geo_audit.sql'
    $prior = Join-Path $ProjectRoot 'engineering\database-prep\sql\012_task5_published_claim_evidence.sql'
    $migrationHash = (Get-FileHash -LiteralPath $migration -Algorithm SHA256).Hash.ToLowerInvariant()
    $priorHash = (Get-FileHash -LiteralPath $prior -Algorithm SHA256).Hash.ToLowerInvariant()
    Get-Content -LiteralPath $migration -Raw -Encoding UTF8 | & docker exec -i -e "PGPASSWORD=$ddlPassword" -e "RAHGARD_PILOT_DATABASE_MARKER=$marker" -e "RAHGARD_PILOT_MIGRATION_0012_SHA256=$priorHash" $container psql -h 127.0.0.1 -X -v ON_ERROR_STOP=1 -v "migration_hash=$migrationHash" -q -U rahgard_pilot_ddl_owner -d $pilotDb
    if ($LASTEXITCODE -ne 0) { throw 'Private-test migration failed.' }
    & docker exec $container psql -X -v ON_ERROR_STOP=1 -q -U ai_tourism_owner -d $pilotDb -c 'REVOKE CREATE ON SCHEMA operations FROM rahgard_pilot_geo_executor'
    if ($LASTEXITCODE -ne 0) { throw 'Could not remove temporary function-owner schema CREATE privilege.' }

    $authorize = @'
\set ON_ERROR_STOP on
\getenv marker_hash GEO_TEST_MARKER_HASH
\getenv decision_hash GEO_TEST_DECISION_HASH
GRANT EXECUTE ON FUNCTION operations.apply_private_geo_approval(TEXT,TEXT,TEXT,TEXT,TEXT,TIMESTAMPTZ) TO rahgard_pilot_geo_publisher;
INSERT INTO operations.private_pilot_geo_authorizations
    (destination_key, decision_sha256, marker_sha256, canonical_name, destination_type,
     province_name, city_name, latitude, longitude, coordinate_role, source_url,
     reviewer, approval_reference, reviewed_at, expires_at)
SELECT destination_key, :'decision_hash', :'marker_hash', canonical_name, destination_type,
       province_name, city_name, latitude, longitude, coordinate_role,
       'https://whc.unesco.org/en/list/114/maps/', 'QA_ONLY', 'ISOLATED_TEST_ONLY',
       '2000-01-01T00:00:00Z'::timestamptz, now() + interval '30 minutes'
FROM knowledge.destinations WHERE destination_key='unesco-persepolis-v1';
'@
    $authorize | & docker exec -i -e "PGPASSWORD=$ddlPassword" -e "GEO_TEST_MARKER_HASH=$markerHash" -e "GEO_TEST_DECISION_HASH=$decisionHash" $container psql -h 127.0.0.1 -X -v ON_ERROR_STOP=1 -q -U rahgard_pilot_ddl_owner -d $pilotDb
    if ($LASTEXITCODE -ne 0) { throw 'QA-only authorization setup failed.' }
    $privileges = & docker exec -e "PGPASSWORD=$publisherPassword" $container psql -h 127.0.0.1 -X -q -A -t -F '|' -U rahgard_pilot_geo_publisher -d $pilotDb -c "SELECT has_any_column_privilege(current_user,'knowledge.destinations','UPDATE'),has_any_column_privilege(current_user,'operations.private_pilot_geo_authorizations','INSERT'),has_any_column_privilege(current_user,'operations.private_pilot_geo_approvals','INSERT')"
    if ($LASTEXITCODE -ne 0 -or ($privileges | Out-String).Trim() -ne 'f|f|f') { throw 'Publisher has unexpected direct write privileges.' }
    $invoke = @'
\set ON_ERROR_STOP on
\getenv marker_hash GEO_TEST_MARKER_HASH
\getenv decision_hash GEO_TEST_DECISION_HASH
SELECT operations.apply_private_geo_approval('unesco-persepolis-v1', :'decision_hash', :'marker_hash',
    'QA_ONLY', 'ISOLATED_TEST_ONLY', '2000-01-01T00:00:00Z'::timestamptz);
'@
    $result = $invoke | & docker exec -i -e "PGPASSWORD=$publisherPassword" -e "GEO_TEST_MARKER_HASH=$markerHash" -e "GEO_TEST_DECISION_HASH=$decisionHash" $container psql -h 127.0.0.1 -X -q -A -t -U rahgard_pilot_geo_publisher -d $pilotDb
    if ($LASTEXITCODE -ne 0 -or ($result | Out-String).Trim() -ne 't') { throw 'QA-only function activation failed.' }
    $repeat = $invoke | & docker exec -i -e "PGPASSWORD=$publisherPassword" -e "GEO_TEST_MARKER_HASH=$markerHash" -e "GEO_TEST_DECISION_HASH=$decisionHash" $container psql -h 127.0.0.1 -X -q -A -t -U rahgard_pilot_geo_publisher -d $pilotDb
    if ($LASTEXITCODE -ne 0 -or ($repeat | Out-String).Trim() -ne 'f') { throw 'Consumed authorization retry was not idempotent.' }
    $state = & docker exec $container psql -X -q -A -t -F '|' -U ai_tourism_owner -d $pilotDb -c "SELECT (SELECT count(*) FROM knowledge.production_destinations WHERE destination_key='unesco-persepolis-v1'),(SELECT count(*) FROM operations.private_pilot_geo_approvals WHERE destination_key='unesco-persepolis-v1'),(SELECT count(*) FROM knowledge.production_destinations WHERE destination_key LIKE 'qa-%')"
    if ($LASTEXITCODE -ne 0 -or ($state | Out-String).Trim() -ne '1|1|0') { throw 'Private-test view or audit invariant failed.' }
    Write-Host 'PASS: isolated PG17 0013 role boundary, exact QA-only activation, audit, view, and idempotent retry.'
}
finally {
    if ($container -and $container -match '^ai-tourism-mvp-pg17-[a-f0-9]{12}$') {
        $present = & docker ps -a --filter "name=^$container$" --format '{{.Names}}'
        if ($LASTEXITCODE -ne 0) { throw 'Cannot verify disposable container cleanup.' }
        if ($present -eq $container) {
            $labelJson = & docker inspect --format '{{json .Config.Labels}}' $container
            if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect disposable container label during cleanup.' }
            $labels = ($labelJson | Out-String) | ConvertFrom-Json
            if ($labels.'ai-tourism.disposable-mvp-e2e' -ne 'true') { throw 'Refusing cleanup of an unverified container.' }
            & docker stop $container | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'Could not stop task-created container.' }
            $remaining = & docker ps -a --filter "name=^$container$" --format '{{.Names}}'
            if ($LASTEXITCODE -ne 0) { throw 'Could not verify disposable container removal.' }
            if ($remaining -eq $container) {
                $labelJson = & docker inspect --format '{{json .Config.Labels}}' $container
                if ($LASTEXITCODE -ne 0) { throw 'Could not reverify disposable container label.' }
                $labels = ($labelJson | Out-String) | ConvertFrom-Json
                if ($labels.'ai-tourism.disposable-mvp-e2e' -ne 'true') { throw 'Refusing removal of an unverified container.' }
                & docker rm $container | Out-Null
                if ($LASTEXITCODE -ne 0) { throw 'Could not remove verified disposable container.' }
            }
        }
    }
}
