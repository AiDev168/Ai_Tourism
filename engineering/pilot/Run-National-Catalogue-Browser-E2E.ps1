# Full application-schema acceptance against a new tmpfs PostgreSQL 17 container.
# The container is created and removed by the guarded MVP runner; never targets shared or live DBs.
[CmdletBinding()]
param(
  [string]$ArchivePath,
  [ValidateSet('simulated','lm_studio','remote_vllm','forced_outage')][string]$ChatProvider = 'simulated',
  [string]$ChatEndpoint,
  [string]$ChatModel,
  [ValidateRange(1024,65535)][int]$ChatLoopbackPort = 1234
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Runner = Join-Path $ProjectRoot 'engineering\database-prep\scripts\Start-Disposable-Mvp-E2E.ps1'
$container = $null
$keys = @('AUTH_INTEGRATION_TESTS','AUTH_TEST_DATABASE_HOST','AUTH_TEST_DATABASE_PORT','AUTH_TEST_DATABASE_NAME','AUTH_TEST_DATABASE_USER','AUTH_TEST_DATABASE_PASSWORD','AUTH_TEST_DATABASE_OWNER_PASSWORD','AUTH_TEST_DATABASE_MARKER','AI_TOURISM_MVP_E2E_CONTAINER','RAHGARD_NATIONAL_CATALOGUE_E2E','RAHGARD_OWNER_ARCHIVE_PATH','RAHGARD_REAL_CHAT_PROVIDER','RAHGARD_REAL_CHAT_ENDPOINT','RAHGARD_REAL_CHAT_MODEL','RAHGARD_REAL_CHAT_TOKEN','RAHGARD_REAL_CHAT_LOOPBACK_HTTP_PORT','ASSISTANT_INTEGRATION_TESTS','TOURISM_RAG_ENABLED')
$before = @{}; foreach ($key in $keys) { $before[$key] = [Environment]::GetEnvironmentVariable($key,'Process') }
if ($ChatProvider -eq 'simulated') {
  if (-not $ArchivePath) { throw 'Simulated national-catalogue mode requires the audited archive path.' }
  if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) { throw 'Owner archive file was not found.' }
  $archiveHash = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($archiveHash -ne '7e9a27654535590f593aeea8e9f7ba9422fb128ca2c4fc93129061c544aff397') {
    throw 'Owner archive checksum does not match the audited input.'
  }
}
else {
  if ($ChatProvider -eq 'lm_studio') {
    if (-not $ChatEndpoint) { $ChatEndpoint = "http://127.0.0.1:$ChatLoopbackPort/v1/chat/completions" }
    if (-not $ChatModel) { $ChatModel = 'qwen3-8b-abliterated' }
    # LM Studio's local endpoint does not require a provider secret. The
    # adapter requires a non-empty bearer field; this sentinel is not secret.
    $realChatToken = 'lm-studio-loopback-development'
  }
  elseif ($ChatProvider -eq 'remote_vllm') {
    if (-not $ChatEndpoint) { $ChatEndpoint = 'https://llm.hinaa.ir/v1/chat/completions' }
    if (-not $ChatModel) { $ChatModel = 'TaHa1_VL' }
    $realChatToken = [Environment]::GetEnvironmentVariable('RAHGARD_REAL_CHAT_TOKEN','Process')
    if (-not $realChatToken) { $realChatToken = [Environment]::GetEnvironmentVariable('INTERNAL_CHAT_TOKEN','Process') }
    if (-not $realChatToken) { throw 'Remote vLLM acceptance is blocked: no authorized provider token is configured in the process environment.' }
  }
  else {
    if ($ChatLoopbackPort -eq 1234) { $ChatLoopbackPort = 1235 }
    $probe = New-Object System.Net.Sockets.TcpClient
    try {
      $connect = $probe.BeginConnect('127.0.0.1',$ChatLoopbackPort,$null,$null)
      if ($connect.AsyncWaitHandle.WaitOne(500) -and $probe.Connected) {
        throw 'Forced-outage acceptance requires the selected loopback port to be closed.'
      }
    } finally { $probe.Dispose() }
    $ChatEndpoint = "http://127.0.0.1:$ChatLoopbackPort/v1/chat/completions"
    $ChatModel = 'forced-unavailable-test'
    $realChatToken = 'local-fallback-test-sentinel'
  }
  [Environment]::SetEnvironmentVariable('RAHGARD_REAL_CHAT_PROVIDER',$ChatProvider,'Process')
  [Environment]::SetEnvironmentVariable('RAHGARD_REAL_CHAT_ENDPOINT',$ChatEndpoint,'Process')
  [Environment]::SetEnvironmentVariable('RAHGARD_REAL_CHAT_MODEL',$ChatModel,'Process')
  [Environment]::SetEnvironmentVariable('RAHGARD_REAL_CHAT_TOKEN',$realChatToken,'Process')
  if ($ChatProvider -in @('lm_studio','forced_outage')) {
    [Environment]::SetEnvironmentVariable('RAHGARD_REAL_CHAT_LOOPBACK_HTTP_PORT',[string]$ChatLoopbackPort,'Process')
  }
}
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
  # Check syntax BEFORE creating the disposable PostgreSQL container or
  # running its migrations. This catches duplicate lexical declarations
  # and other Node parser failures without touching any database.
  $e2eScript = Join-Path $ProjectRoot 'frontend\scripts\traveler-e2e.mjs'
  & node --check $e2eScript
  if ($LASTEXITCODE -ne 0) { throw 'Traveler Chromium E2E JavaScript syntax validation failed; database was not started.' }
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
  $h23File = Join-Path $ProjectRoot 'engineering/pilot/sql/023_partner_trip_responses.sql'
  $h23Expected = (Get-FileHash -LiteralPath $h23File -Algorithm SHA256).Hash.ToLowerInvariant()
  $h23 = Apply '023_partner_trip_responses' 'engineering/pilot/sql/023_partner_trip_responses.sql' 'ai_tourism_owner' $env:AUTH_TEST_DATABASE_OWNER_PASSWORD @{ RAHGARD_PILOT_MIGRATION_0022_SHA256=$h22; RAHGARD_PILOT_MIGRATION_0023_SHA256=$h23Expected }
  $migration23Assertions = (Psql $migrationTarget "SELECT (SELECT sha256 FROM system.schema_migrations WHERE migration_id='0023_partner_trip_responses')='$h23Expected', (SELECT relrowsecurity FROM pg_class WHERE oid='partner.trip_company_responses'::regclass), has_table_privilege('ai_tourism_app','partner.trip_company_responses','SELECT'), has_table_privilege('ai_tourism_app','partner.trip_company_responses','INSERT'), has_column_privilege('ai_tourism_app','partner.trip_company_responses','traveler_decision','UPDATE')") | Out-String
  if (($migration23Assertions -join '').Trim() -ne 't|t|t|t|t') { throw "Migration 0023 assertions failed (checksum, RLS, grants): $migration23Assertions" }
  $h24File = Join-Path $ProjectRoot 'engineering/pilot/sql/024_partner_review_audit_actions.sql'
  $h24Expected = (Get-FileHash -LiteralPath $h24File -Algorithm SHA256).Hash.ToLowerInvariant()
  $h24 = Apply '024_partner_review_audit_actions' 'engineering/pilot/sql/024_partner_review_audit_actions.sql' 'ai_tourism_owner' $env:AUTH_TEST_DATABASE_OWNER_PASSWORD @{ RAHGARD_PILOT_MIGRATION_0023_SHA256=$h23; RAHGARD_PILOT_MIGRATION_0024_SHA256=$h24Expected }
  $migration24Assertions = (Psql $migrationTarget "SELECT (SELECT sha256 FROM system.schema_migrations WHERE migration_id='0024_partner_review_audit_actions')='$h24Expected', NOT has_table_privilege('ai_tourism_app','partner.platform_grants','INSERT'), NOT has_table_privilege('ai_tourism_app','partner.platform_grants','UPDATE'), (SELECT pg_get_constraintdef(oid) LIKE '%activate%' AND pg_get_constraintdef(oid) LIKE '%deactivate%' FROM pg_constraint WHERE conrelid='partner.review_events'::regclass AND conname='review_events_decision_check'), EXISTS(SELECT 1 FROM pg_policy WHERE polrelid='partner.review_events'::regclass AND polname='review_events_platform_insert' AND pg_get_expr(polwithcheck,polrelid) ILIKE '%verification_case%' AND pg_get_expr(polwithcheck,polrelid) ILIKE '%organization_review%')") | Out-String
  if (($migration24Assertions -join '').Trim() -ne 't|t|t|t|t') { throw "Migration 0024 assertions failed (ledger, least privilege, audit vocabulary, reviewer audit RLS): $migration24Assertions" }
  $h25File = Join-Path $ProjectRoot 'engineering/pilot/sql/025_owner_control_center.sql'
  $h25Expected = (Get-FileHash -LiteralPath $h25File -Algorithm SHA256).Hash.ToLowerInvariant()
  $h25 = Apply '025_owner_control_center' 'engineering/pilot/sql/025_owner_control_center.sql' 'ai_tourism_owner' $env:AUTH_TEST_DATABASE_OWNER_PASSWORD @{ RAHGARD_PILOT_MIGRATION_0024_SHA256=$h24Expected; RAHGARD_PILOT_MIGRATION_0025_SHA256=$h25Expected }
  $migration25Assertions = (Psql $migrationTarget "SELECT (SELECT sha256 FROM system.schema_migrations WHERE migration_id='0025_owner_control_center')='$h25Expected', (SELECT count(*) IN (24,26) FROM system.schema_migrations), (SELECT max(migration_id)='0025_owner_control_center' FROM system.schema_migrations), (SELECT pg_get_constraintdef(oid) ILIKE '%admin_overview_read%' FROM pg_constraint WHERE conrelid='partner.platform_grants'::regclass AND conname='platform_grants_capability_check'), NOT has_table_privilege('ai_tourism_app','partner.platform_grant_events','SELECT'), NOT has_table_privilege('ai_tourism_app','partner.platform_grant_events','INSERT'), NOT has_table_privilege('ai_tourism_app','partner.platform_grants','INSERT'), NOT has_table_privilege('ai_tourism_app','partner.platform_grants','UPDATE'), has_function_privilege('ai_tourism_app','partner.admin_grant_counts()','EXECUTE'), (SELECT prosecdef FROM pg_proc WHERE oid='partner.admin_grant_counts()'::regprocedure)") | Out-String
  if (($migration25Assertions -join '').Trim() -ne 't|t|t|t|t|t|t|t|t|t') { throw "Migration 0025 assertions failed (ledger, capability vocabulary, operator-only grant audit, guarded aggregate function): $migration25Assertions" }
  $migrationCount = (Psql $migrationTarget 'SELECT count(*) FROM system.schema_migrations').Trim()
  $testDb = $env:AUTH_TEST_DATABASE_NAME
  Psql 'postgres' "ALTER DATABASE $migrationTarget RENAME TO $testDb;" | Out-Null
  $env:AUTH_TEST_DATABASE_NAME = $testDb
  $env:ASSISTANT_INTEGRATION_TESTS = '1'
  $env:TOURISM_RAG_ENABLED = 'false'
  if ($ChatProvider -eq 'simulated') {
    $env:RAHGARD_NATIONAL_CATALOGUE_E2E = '1'
    $env:RAHGARD_OWNER_ARCHIVE_PATH = (Resolve-Path -LiteralPath $ArchivePath).Path
  }
  else {
    $env:RAHGARD_REAL_CHAT_PROVIDER = $ChatProvider
  }
  Push-Location (Join-Path $ProjectRoot 'frontend')
  try { node scripts/traveler-e2e.mjs; if ($LASTEXITCODE -ne 0) { throw 'National-catalogue browser acceptance failed.' } }
  finally { Pop-Location }
  if ($ChatProvider -eq 'simulated') {
    Write-Host "PASS: full app migrations 0013-0025 (ledger rows=$migrationCount) and authenticated national-catalogue Chromium journey completed in isolated PG17." -ForegroundColor Green
  }
  elseif ($ChatProvider -eq 'forced_outage') {
    Write-Host "PASS: production Chat adapter failure and deterministic fallback were exercised through authenticated Chromium/FastAPI on disposable PG17 with migrations through 0025 (ledger rows=$migrationCount)." -ForegroundColor Green
  }
  else {
    Write-Host "PASS: authenticated real-provider Chromium journey via $ChatProvider completed on disposable PG17 (ledger rows=$migrationCount); no persistent database or VPS was used." -ForegroundColor Green
  }
}
finally {
  if ($container -and $container -match '^ai-tourism-mvp-pg17-[a-f0-9]{12}$') {
    if (Get-Command Stop-RemoveOwnedContainer -ErrorAction SilentlyContinue) {
      Stop-RemoveOwnedContainer $container
    }
  }
  foreach ($key in $keys) { [Environment]::SetEnvironmentVariable($key,$before[$key],'Process') }
}
