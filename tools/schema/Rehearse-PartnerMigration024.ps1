[CmdletBinding()]
param(
    [string]$ContainerName = 'rahgard-partner-024-isolated-rehearsal'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Migration23 = Join-Path $RepoRoot 'engineering\pilot\sql\023_partner_trip_responses.sql'
$Migration24 = Join-Path $RepoRoot 'engineering\pilot\sql\024_partner_review_audit_actions.sql'
foreach ($path in @($Migration23, $Migration24)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required migration file is missing: $path" }
}

$existing = docker container ls -a --filter "name=^/$ContainerName$" --format '{{.ID}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker container inventory failed.' }
if ($existing) { throw "Refusing to use an existing container named $ContainerName." }
$image = 'ai-tourism-postgres:17-postgis36-vector087'
docker image inspect $image *> $null
if ($LASTEXITCODE -ne 0) { throw "Required local PostgreSQL 17 test image is unavailable: $image" }

$marker = ([Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N'))
$hash23 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Migration23).Hash.ToLowerInvariant()
$hash24 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Migration24).Hash.ToLowerInvariant()
$testPassword = 'isolated-migration-test-only'
$started = $false
try {
    $containerId = docker run --rm -d --name $ContainerName --network none `
        --tmpfs '/var/lib/postgresql/data:rw,noexec,nosuid,size=1g' `
        -e 'POSTGRES_DB=rahgard_pilot_vps_staging' `
        -e 'POSTGRES_USER=ai_tourism_owner' `
        -e "POSTGRES_PASSWORD=$testPassword" $image
    if ($LASTEXITCODE -ne 0 -or -not $containerId) { throw 'Disposable PostgreSQL container did not start.' }
    $started = $true
    $networkMode = docker inspect -f '{{.HostConfig.NetworkMode}}' $ContainerName
    $tmpfsConfig = docker inspect -f '{{json .HostConfig.Tmpfs}}' $ContainerName
    $mountCount = docker inspect -f '{{len .Mounts}}' $ContainerName
    if ($LASTEXITCODE -ne 0 -or $networkMode.Trim() -ne 'none' -or
        $tmpfsConfig -notmatch '"/var/lib/postgresql/data"' -or $mountCount.Trim() -ne '0') {
        throw 'Disposable database isolation check failed; no SQL was run.'
    }

    $ready = $false
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        docker exec $ContainerName pg_isready -U ai_tourism_owner -d rahgard_pilot_vps_staging *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw 'Disposable PostgreSQL did not become ready.' }

    $fixture = @'
CREATE ROLE ai_tourism_app LOGIN PASSWORD 'isolated-app-role-only';
CREATE SCHEMA system;
CREATE TABLE system.schema_migrations (migration_id text PRIMARY KEY, sha256 text NOT NULL);
CREATE SCHEMA partner;
CREATE TABLE public.rahgard_private_pilot_marker (marker_value text NOT NULL);
CREATE TABLE partner.platform_grants (user_id uuid, capability text);
CREATE TABLE partner.review_events (
  decision text NOT NULL,
  entity_type text NOT NULL,
  reviewer_user_id uuid NOT NULL,
  CONSTRAINT review_events_decision_check
    CHECK (decision IN ('approve','reject','request_changes','suspend','reinstate'))
);
GRANT SELECT, INSERT, UPDATE ON partner.platform_grants TO ai_tourism_app;
CREATE FUNCTION partner.current_actor_id() RETURNS uuid LANGUAGE sql STABLE AS $$ SELECT NULL::uuid $$;
CREATE FUNCTION partner.has_platform_capability(uuid,text) RETURNS boolean LANGUAGE sql STABLE AS $$ SELECT false $$;
ALTER TABLE partner.review_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY review_events_platform_insert ON partner.review_events FOR INSERT
WITH CHECK (reviewer_user_id=partner.current_actor_id()
    AND ((entity_type='organization' AND partner.has_platform_capability(partner.current_actor_id(),'organization_review'))
      OR (entity_type IN ('service','branch') AND partner.has_platform_capability(partner.current_actor_id(),'service_review'))
      OR (entity_type IN ('offer','price','schedule','availability') AND partner.has_platform_capability(partner.current_actor_id(),'offer_review'))));
'@
    $fixture | docker exec -i -e "PGPASSWORD=$testPassword" $ContainerName `
        psql -X -q -v ON_ERROR_STOP=1 -U ai_tourism_owner -d rahgard_pilot_vps_staging
    if ($LASTEXITCODE -ne 0) { throw 'Isolated baseline fixture setup failed.' }
    $knownIds = @(
        '0000_legacy_tourism_points_baseline','0001_core_schema','0002_synthetic_knowledge_seed',
        '0003_synthetic_e2e_seed','0004_app_role_grants','0005_verified_unesco_destination_seed',
        '0006_verified_unesco_destination_seed_batch2','0007_shiraz_dalahoo_wikipedia_dataset_v1',
        '0008_authentication_foundation','0009_traveler_core','0010_task31_content_privacy_full_itinerary',
        '0011_internal_chat_turns','0012_task5_published_claim_evidence','0013_private_pilot_geo_audit',
        '0016_staging_invitation_auth','0017_provisional_itineraries','0018_national_catalogue_ingestion',
        '0019_partner_workspace','0020_archive_candidate_publication',
        '0021_postgis_security_definer_publication','0022_traveler_company_requests',
        '0023_partner_trip_responses'
    )
    $ledgerValues = ($knownIds | ForEach-Object { "('$($_)',repeat('a',64))" }) -join ','
    $migration23Row = "INSERT INTO system.schema_migrations VALUES $ledgerValues ON CONFLICT DO NOTHING; UPDATE system.schema_migrations SET sha256='$hash23' WHERE migration_id='0023_partner_trip_responses'; INSERT INTO public.rahgard_private_pilot_marker VALUES ('$marker');"
    $migration23Row | docker exec -i -e "PGPASSWORD=$testPassword" $ContainerName `
        psql -X -q -v ON_ERROR_STOP=1 -U ai_tourism_owner -d rahgard_pilot_vps_staging
    if ($LASTEXITCODE -ne 0) { throw 'Isolated migration 0023 marker setup failed.' }

    Get-Content -Raw -Encoding UTF8 -LiteralPath $Migration24 |
        docker exec -i -e "PGPASSWORD=$testPassword" -e "RAHGARD_PILOT_DATABASE_MARKER=$marker" `
            -e "RAHGARD_PILOT_MIGRATION_0023_SHA256=$hash23" -e "RAHGARD_PILOT_MIGRATION_0024_SHA256=$hash24" `
            $ContainerName psql -X -v ON_ERROR_STOP=1 -U ai_tourism_owner -d rahgard_pilot_vps_staging
    if ($LASTEXITCODE -ne 0) { throw 'Migration 0024 failed in the isolated PostgreSQL rehearsal.' }

    $checks = docker exec -e "PGPASSWORD=$testPassword" $ContainerName psql -X -A -t `
        -U ai_tourism_owner -d rahgard_pilot_vps_staging -c @'
SELECT (SELECT count(*) FROM system.schema_migrations WHERE migration_id='0024_partner_review_audit_actions')=1
   AND NOT has_table_privilege('ai_tourism_app','partner.platform_grants','SELECT')
   AND NOT has_table_privilege('ai_tourism_app','partner.platform_grants','INSERT')
   AND NOT has_table_privilege('ai_tourism_app','partner.platform_grants','UPDATE')
   AND EXISTS (SELECT 1 FROM pg_catalog.pg_constraint
               WHERE conrelid='partner.review_events'::regclass
                 AND pg_catalog.pg_get_constraintdef(oid) LIKE '%activate%deactivate%')
   AND EXISTS (SELECT 1 FROM pg_catalog.pg_policy
               WHERE polrelid='partner.review_events'::regclass
                 AND polname='review_events_platform_insert'
                 AND pg_get_expr(polwithcheck,polrelid) ILIKE '%verification_case%'
                 AND pg_get_expr(polwithcheck,polrelid) ILIKE '%organization_review%');
'@
    if ($LASTEXITCODE -ne 0 -or $checks.Trim() -ne 't') {
        $state = docker inspect -f '{{.State.Status}}|{{.State.ExitCode}}' $ContainerName 2>$null
        $safeLogs = docker logs --tail 12 $ContainerName 2>&1
        Write-Output "Isolated postcondition diagnostic: state=$state; postgres logs follow."
        Write-Output $safeLogs
        throw 'Migration 0024 postconditions failed.'
    }
    Write-Output "PASS: Migration 0024 applied only in temporary PG17; ledger registered; platform_grants privileges revoked; app-role negative access denied; verification_case reviewer audit policy present; migrations SHA-256 0023=$hash23 0024=$hash24."
}
finally {
    if ($started) {
        docker stop $ContainerName *> $null
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Temporary test container cleanup did not confirm stop; inspect only this named rehearsal container.' }
    }
}
