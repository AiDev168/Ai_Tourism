# Full application-schema acceptance against a new tmpfs PostgreSQL 17 container.
# The container is created and removed by the guarded MVP runner; never targets shared or live DBs.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ArchivePath)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Runner = Join-Path $ProjectRoot 'engineering\database-prep\scripts\Start-Disposable-Mvp-E2E.ps1'
$container = $null
$keys = @('AUTH_INTEGRATION_TESTS','AUTH_TEST_DATABASE_HOST','AUTH_TEST_DATABASE_PORT','AUTH_TEST_DATABASE_NAME','AUTH_TEST_DATABASE_USER','AUTH_TEST_DATABASE_PASSWORD','AUTH_TEST_DATABASE_OWNER_PASSWORD','AUTH_TEST_DATABASE_MARKER','AI_TOURISM_MVP_E2E_CONTAINER','RAHGARD_NATIONAL_CATALOGUE_E2E','RAHGARD_OWNER_ARCHIVE_PATH','ASSISTANT_INTEGRATION_TESTS','TOURISM_RAG_ENABLED')
$before = @{}; foreach ($key in $keys) { $before[$key] = [Environment]::GetEnvironmentVariable($key,'Process') }
function Hex([int]$Length) {
  $buffer = New-Object byte[] $Length; $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
  return [BitConverter]::ToString($buffer).Replace('-','').ToLowerInvariant()
}
function Psql([string]$Db,[string]$Sql,[string]$User='ai_tourism_owner',[string]$Password=$env:AUTH_TEST_DATABASE_OWNER_PASSWORD) {
  $out = $Sql | & docker exec -i -e "PGPASSWORD=$Password" $container psql -X -q -A -t -v ON_ERROR_STOP=1 -U $User -d $Db
  if ($LASTEXITCODE -ne 0) { throw "Isolated PostgreSQL operation failed for $Db." }
  return $out
}
function Apply([string]$Id,[string]$File,[string]$User,[string]$Password,[hashtable]$Vars=@{}) {
  $path = Join-Path $ProjectRoot $File; $hash = (Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant()
  $remote = "/tmp/$Id.sql"; & docker cp $path "$($container):$remote" | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Could not stage isolated migration $Id." }
  $args = @('exec','-e',"PGPASSWORD=$Password",'-e',"RAHGARD_PILOT_DATABASE_MARKER=$marker")
  foreach ($entry in $Vars.GetEnumerator()) { $args += @('-e',"$($entry.Key)=$($entry.Value)") }
  $args += @($container,'psql','-h','127.0.0.1','-X','-q','-v','ON_ERROR_STOP=1','-v',"migration_hash=$hash",'-U',$User,'-d','rahgard_pilot_vps_staging')
  foreach ($entry in $Vars.GetEnumerator()) { $args += @('-v',"$($entry.Key)=$($entry.Value)") }
  $args += @('-f',$remote); & docker @args | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Isolated migration $Id failed." }
  return $hash
}
try {
  if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) { throw 'Owner archive file was not found.' }
  $archiveHash = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($archiveHash -ne '7e9a27654535590f593aeea8e9f7ba9422fb128ca2c4fc93129061c544aff397') {
    throw 'Owner archive checksum does not match the audited input.'
  }
  . $Runner -ProjectRoot $ProjectRoot
  $container = $env:AI_TOURISM_MVP_E2E_CONTAINER
  if ($container -notmatch '^ai-tourism-mvp-pg17-[a-f0-9]{12}$' -or $env:AUTH_TEST_DATABASE_HOST -ne '127.0.0.1' -or [int]$env:AUTH_TEST_DATABASE_PORT -eq 55433) { throw 'Disposable database identity guard failed.' }
  $suffix = $container.Substring($container.Length - 12)
  $sourceDb = $env:AUTH_TEST_DATABASE_NAME
  $baseDb = "ai_tourism_auth_test_base_$suffix"
  $migrationTarget = 'rahgard_pilot_vps_staging'
  $marker = $env:AUTH_TEST_DATABASE_MARKER
  Psql 'postgres' "ALTER DATABASE $sourceDb RENAME TO $baseDb;" | Out-Null
  Psql 'postgres' "CREATE DATABASE $migrationTarget TEMPLATE $baseDb;" | Out-Null
  $ddlPassword = Hex 24
  $publisherPassword = Hex 24
  $setup = @'
\set ON_ERROR_STOP on
\getenv marker RAHGARD_PILOT_DATABASE_MARKER
\getenv ddl_password RAHGARD_TEST_DDL_PASSWORD
\getenv publisher_password RAHGARD_TEST_PUBLISHER_PASSWORD
CREATE TABLE public.rahgard_private_pilot_marker(marker_value text NOT NULL);
INSERT INTO public.rahgard_private_pilot_marker VALUES (:'marker');
GRANT USAGE ON SCHEMA public TO ai_tourism_app;
GRANT SELECT ON public.rahgard_private_pilot_marker TO ai_tourism_app;
GRANT USAGE ON SCHEMA system TO ai_tourism_app;
GRANT SELECT ON system.schema_migrations TO ai_tourism_app;
CREATE ROLE rahgard_pilot_geo_executor NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_geo_publisher LOGIN PASSWORD :'publisher_password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_ddl_owner LOGIN PASSWORD :'ddl_password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT rahgard_pilot_geo_executor TO rahgard_pilot_ddl_owner;
GRANT USAGE ON SCHEMA identity, knowledge, operations, system, public TO rahgard_pilot_ddl_owner;
GRANT CREATE ON SCHEMA identity, operations TO rahgard_pilot_ddl_owner;
GRANT REFERENCES ON identity.users, identity.web_sessions TO rahgard_pilot_ddl_owner;
GRANT CREATE ON DATABASE rahgard_pilot_vps_staging TO rahgard_pilot_ddl_owner;
GRANT USAGE ON SCHEMA knowledge, operations, public TO rahgard_pilot_geo_executor;
GRANT CREATE ON SCHEMA operations TO rahgard_pilot_geo_executor;
GRANT USAGE ON SCHEMA operations, knowledge TO rahgard_pilot_geo_publisher;
GRANT SELECT ON knowledge.destinations, knowledge.destination_sources, knowledge.knowledge_sources,
    system.schema_migrations, public.rahgard_private_pilot_marker TO rahgard_pilot_ddl_owner;
GRANT SELECT ON knowledge.production_destinations TO rahgard_pilot_ddl_owner;
GRANT SELECT ON knowledge.destinations, knowledge.destination_sources, knowledge.knowledge_sources,
    public.rahgard_private_pilot_marker TO rahgard_pilot_geo_executor;
GRANT INSERT ON system.schema_migrations TO rahgard_pilot_ddl_owner;
GRANT UPDATE(status,updated_at), REFERENCES(destination_key) ON knowledge.destinations TO rahgard_pilot_ddl_owner;
GRANT UPDATE(status,updated_at) ON knowledge.destinations TO rahgard_pilot_geo_executor;
'@
  $setup | & docker exec -i -e "RAHGARD_PILOT_DATABASE_MARKER=$marker" -e "RAHGARD_TEST_DDL_PASSWORD=$ddlPassword" -e "RAHGARD_TEST_PUBLISHER_PASSWORD=$publisherPassword" $container psql -X -v ON_ERROR_STOP=1 -q -U ai_tourism_owner -d $migrationTarget
  if ($LASTEXITCODE -ne 0) { throw 'Could not prepare least-privilege migration roles in isolated PostgreSQL.' }
  $prior12 = (Get-FileHash (Join-Path $ProjectRoot 'engineering/database-prep/sql/012_task5_published_claim_evidence.sql') -Algorithm SHA256).Hash.ToLowerInvariant()
  $h13 = Apply '013_private_pilot_geo_audit' 'engineering/pilot/sql/013_private_pilot_geo_audit.sql' 'rahgard_pilot_ddl_owner' $ddlPassword @{ RAHGARD_PILOT_MIGRATION_0012_SHA256=$prior12 }
  $markerHasher = [Security.Cryptography.SHA256]::Create()
  try { $markerHash = [BitConverter]::ToString($markerHasher.ComputeHash([Text.Encoding]::ASCII.GetBytes($marker))).Replace('-','').ToLowerInvariant() }
  finally { $markerHasher.Dispose() }
  $qaDecisionHash = 'a' * 64
  $authorizeGeo = @'
\set ON_ERROR_STOP on
\getenv marker_hash RAHGARD_TEST_MARKER_HASH
\getenv decision_hash RAHGARD_TEST_DECISION_HASH
GRANT EXECUTE ON FUNCTION operations.apply_private_geo_approval(TEXT,TEXT,TEXT,TEXT,TEXT,TIMESTAMPTZ) TO rahgard_pilot_geo_publisher;
INSERT INTO operations.private_pilot_geo_authorizations
    (destination_key, decision_sha256, marker_sha256, canonical_name, destination_type,
     province_name, city_name, latitude, longitude, coordinate_role, source_url,
     reviewer, approval_reference, reviewed_at, expires_at)
SELECT destination_key, :'decision_hash', :'marker_hash', canonical_name, destination_type,
       province_name, city_name, latitude, longitude, 'property_reference',
       'https://whc.unesco.org/en/list/114/maps/', 'QA_ONLY', 'ISOLATED_TEST_ONLY',
       '2000-01-01T00:00:00Z'::timestamptz, now() + interval '30 minutes'
FROM knowledge.destinations WHERE destination_key='unesco-persepolis-v1';
'@
  $authorizeGeo | & docker exec -i -e "PGPASSWORD=$ddlPassword" -e "RAHGARD_TEST_MARKER_HASH=$markerHash" -e "RAHGARD_TEST_DECISION_HASH=$qaDecisionHash" $container psql -h 127.0.0.1 -X -v ON_ERROR_STOP=1 -q -U rahgard_pilot_ddl_owner -d $migrationTarget
  if ($LASTEXITCODE -ne 0) { throw 'Could not establish the isolated QA-only owner-approved Persepolis prerequisite.' }
  $publishGeo = @'
\set ON_ERROR_STOP on
\getenv marker_hash RAHGARD_TEST_MARKER_HASH
\getenv decision_hash RAHGARD_TEST_DECISION_HASH
SELECT operations.apply_private_geo_approval('unesco-persepolis-v1', :'decision_hash', :'marker_hash',
    'QA_ONLY', 'ISOLATED_TEST_ONLY', '2000-01-01T00:00:00Z'::timestamptz);
'@
  $publishedBase = $publishGeo | & docker exec -i -e "PGPASSWORD=$publisherPassword" -e "RAHGARD_TEST_MARKER_HASH=$markerHash" -e "RAHGARD_TEST_DECISION_HASH=$qaDecisionHash" $container psql -h 127.0.0.1 -X -q -A -t -v ON_ERROR_STOP=1 -U rahgard_pilot_geo_publisher -d $migrationTarget
  if ($LASTEXITCODE -ne 0 -or ($publishedBase | Out-String).Trim() -ne 't') { throw 'Isolated owner-approved Persepolis activation failed.' }
  $h14File = Join-Path $ProjectRoot 'engineering/pilot/sql/014_local_owner_login.sql'
  $h14File = Join-Path $ProjectRoot 'engineering/pilot/sql/014_local_owner_login.sql'
  $h14Expected = (Get-FileHash -LiteralPath $h14File -Algorithm SHA256).Hash.ToLowerInvariant()
  $h14 = Apply '014_local_owner_login' 'engineering/pilot/sql/014_local_owner_login.sql' 'rahgard_pilot_ddl_owner' $ddlPassword @{ RAHGARD_PILOT_MIGRATION_0013_SHA256=$h13; RAHGARD_PILOT_MIGRATION_0014_SHA256=$h14Expected }
  $h15File = Join-Path $ProjectRoot 'engineering/pilot/sql/015_ai_provider_admin.sql'
  $h15Expected = (Get-FileHash -LiteralPath $h15File -Algorithm SHA256).Hash.ToLowerInvariant()
  $h15 = Apply '015_ai_provider_admin' 'engineering/pilot/sql/015_ai_provider_admin.sql' 'rahgard_pilot_ddl_owner' $ddlPassword @{ RAHGARD_PILOT_MIGRATION_0014_SHA256=$h14; RAHGARD_PILOT_MIGRATION_0015_SHA256=$h15Expected }
  $h16File = Join-Path $ProjectRoot 'engineering/pilot/sql/016_staging_invitation_auth.sql'
  $h16Expected = (Get-FileHash -LiteralPath $h16File -Algorithm SHA256).Hash.ToLowerInvariant()
  $h16 = Apply '016_staging_invitation_auth' 'engineering/pilot/sql/016_staging_invitation_auth.sql' 'ai_tourism_owner' $env:AUTH_TEST_DATABASE_OWNER_PASSWORD @{ RAHGARD_PILOT_MIGRATION_0013_SHA256=$h13; RAHGARD_PILOT_MIGRATION_0016_SHA256=$h16Expected }
  $h17File = Join-Path $ProjectRoot 'engineering/pilot/sql/017_provisional_itineraries.sql'
  $h17Expected = (Get-FileHash -LiteralPath $h17File -Algorithm SHA256).Hash.ToLowerInvariant()
  $h17 = Apply '017_provisional_itineraries' 'engineering/pilot/sql/017_provisional_itineraries.sql' 'ai_tourism_owner' $env:AUTH_TEST_DATABASE_OWNER_PASSWORD @{ RAHGARD_PILOT_MIGRATION_0016_SHA256=$h16; RAHGARD_PILOT_MIGRATION_0017_SHA256=$h17Expected }
  $h18File = Join-Path $ProjectRoot 'engineering/pilot/sql/018_national_catalogue_ingestion.sql'
  $h18Expected = (Get-FileHash -LiteralPath $h18File -Algorithm SHA256).Hash.ToLowerInvariant()
  $h18 = Apply '018_national_catalogue_ingestion' 'engineering/pilot/sql/018_national_catalogue_ingestion.sql' 'ai_tourism_owner' $env:AUTH_TEST_DATABASE_OWNER_PASSWORD @{ RAHGARD_PILOT_MIGRATION_0017_SHA256=$h17; RAHGARD_PILOT_MIGRATION_0018_SHA256=$h18Expected }
  $h19File = Join-Path $ProjectRoot 'engineering/pilot/sql/019_partner_workspace.sql'
  $h19Expected = (Get-FileHash -LiteralPath $h19File -Algorithm SHA256).Hash.ToLowerInvariant()
  $h19 = Apply '019_partner_workspace' 'engineering/pilot/sql/019_partner_workspace.sql' 'ai_tourism_owner' $env:AUTH_TEST_DATABASE_OWNER_PASSWORD @{ RAHGARD_PILOT_MIGRATION_0018_SHA256=$h18; RAHGARD_PILOT_MIGRATION_0019_SHA256=$h19Expected }
  $h20File = Join-Path $ProjectRoot 'engineering/pilot/sql/020_archive_candidate_publication.sql'
  $h20Expected = (Get-FileHash -LiteralPath $h20File -Algorithm SHA256).Hash.ToLowerInvariant()
  $h20 = Apply '020_archive_candidate_publication' 'engineering/pilot/sql/020_archive_candidate_publication.sql' 'ai_tourism_owner' $env:AUTH_TEST_DATABASE_OWNER_PASSWORD @{ RAHGARD_PILOT_MIGRATION_0019_SHA256=$h19; RAHGARD_PILOT_MIGRATION_0020_SHA256=$h20Expected }
  $h21File = Join-Path $ProjectRoot 'engineering/pilot/sql/021_postgis_security_definer_publication.sql'
  $h21Expected = (Get-FileHash -LiteralPath $h21File -Algorithm SHA256).Hash.ToLowerInvariant()
  $h21 = Apply '021_postgis_security_definer_publication' 'engineering/pilot/sql/021_postgis_security_definer_publication.sql' 'ai_tourism_owner' $env:AUTH_TEST_DATABASE_OWNER_PASSWORD @{ RAHGARD_PILOT_MIGRATION_0020_SHA256=$h20; RAHGARD_PILOT_MIGRATION_0021_SHA256=$h21Expected }
  $h22File = Join-Path $ProjectRoot 'engineering/pilot/sql/022_traveler_company_requests.sql'
  $h22Expected = (Get-FileHash -LiteralPath $h22File -Algorithm SHA256).Hash.ToLowerInvariant()
  $h22 = Apply '022_traveler_company_requests' 'engineering/pilot/sql/022_traveler_company_requests.sql' 'ai_tourism_owner' $env:AUTH_TEST_DATABASE_OWNER_PASSWORD @{ RAHGARD_PILOT_MIGRATION_0021_SHA256=$h21; RAHGARD_PILOT_MIGRATION_0022_SHA256=$h22Expected }
  $migration22Assertions = (Psql $migrationTarget "SELECT (SELECT sha256 FROM system.schema_migrations WHERE migration_id='0022_traveler_company_requests')='$h22Expected', (SELECT relrowsecurity FROM pg_class WHERE oid='partner.traveler_request_shares'::regclass), (SELECT relrowsecurity FROM pg_class WHERE oid='partner.traveler_request_revisions'::regclass), (SELECT count(*) FROM information_schema.columns WHERE table_schema='partner' AND table_name='share_eligible_organizations'), has_table_privilege('ai_tourism_app','partner.traveler_request_revisions','INSERT'), has_table_privilege('ai_tourism_app','partner.traveler_request_inbox','INSERT')") | Out-String
  if (($migration22Assertions -join '').Trim() -ne 't|t|t|3|f|f') { throw "Migration 0022 assertions failed (checksum, RLS, view columns, unexpected write grants): $migration22Assertions" }
  $testDb = $env:AUTH_TEST_DATABASE_NAME
  Psql 'postgres' "ALTER DATABASE $migrationTarget RENAME TO $testDb;" | Out-Null
  $env:AUTH_TEST_DATABASE_NAME = $testDb
  $env:RAHGARD_NATIONAL_CATALOGUE_E2E = '1'
  $env:RAHGARD_OWNER_ARCHIVE_PATH = (Resolve-Path -LiteralPath $ArchivePath).Path
  $env:ASSISTANT_INTEGRATION_TESTS = '1'
  $env:TOURISM_RAG_ENABLED = 'false'
  Push-Location (Join-Path $ProjectRoot 'frontend')
  try { node scripts/traveler-e2e.mjs; if ($LASTEXITCODE -ne 0) { throw 'National-catalogue browser acceptance failed.' } }
  finally { Pop-Location }
  Write-Host 'PASS: full app migrations 0013-0022 and authenticated national-catalogue Chromium journey completed in isolated PG17.' -ForegroundColor Green
}
finally {
  if ($container -and $container -match '^ai-tourism-mvp-pg17-[a-f0-9]{12}$') {
    if (Get-Command Stop-RemoveOwnedContainer -ErrorAction SilentlyContinue) {
      Stop-RemoveOwnedContainer $container
    }
  }
  foreach ($key in $keys) { [Environment]::SetEnvironmentVariable($key,$before[$key],'Process') }
}
