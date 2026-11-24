[CmdletBinding()]
param([string]$ContainerName='rahgard-owner-control-025-isolated')
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$m24=Join-Path $root 'engineering\pilot\sql\024_partner_review_audit_actions.sql'
$m25=Join-Path $root 'engineering\pilot\sql\025_owner_control_center.sql'
foreach($file in @($m24,$m25)){if(-not(Test-Path -LiteralPath $file -PathType Leaf)){throw 'Required migration source is missing.'}}
$existing=docker container ls -a --filter "name=^/$ContainerName$" --format '{{.ID}}'
if($LASTEXITCODE -ne 0 -or $existing){throw 'Refusing to reuse an existing container.'}
$image='ai-tourism-postgres:17-postgis36-vector087'
docker image inspect $image *> $null
if($LASTEXITCODE -ne 0){throw 'Pinned PostgreSQL 17/PostGIS rehearsal image is unavailable.'}
$hash24=(Get-FileHash -Algorithm SHA256 -LiteralPath $m24).Hash.ToLowerInvariant()
$hash25=(Get-FileHash -Algorithm SHA256 -LiteralPath $m25).Hash.ToLowerInvariant()
$marker=([Guid]::NewGuid().ToString('N')+[Guid]::NewGuid().ToString('N'))
$password='isolated-migration-025-only'
$started=$false
try {
  $id=docker run --rm -d --name $ContainerName --network none --tmpfs '/var/lib/postgresql/data:rw,noexec,nosuid,size=512m' -e 'POSTGRES_DB=rahgard_pilot_vps_staging' -e 'POSTGRES_USER=ai_tourism_owner' -e "POSTGRES_PASSWORD=$password" $image
  if($LASTEXITCODE -ne 0 -or -not $id){throw 'Disposable PostgreSQL did not start.'}; $started=$true
  if((docker inspect -f '{{.HostConfig.NetworkMode}}' $ContainerName).Trim() -ne 'none' -or (docker inspect -f '{{len .Mounts}}' $ContainerName).Trim() -ne '0'){throw 'Rehearsal container is not isolated and ephemeral.'}
  $ready=$false
  for($i=0;$i -lt 40;$i++){docker exec $ContainerName pg_isready -U ai_tourism_owner -d rahgard_pilot_vps_staging *> $null;if($LASTEXITCODE -eq 0){$ready=$true;break};Start-Sleep -Milliseconds 500}
  if(-not $ready){throw 'Disposable PostgreSQL did not become ready.'}
  @'
CREATE ROLE ai_tourism_app LOGIN;
CREATE SCHEMA system; CREATE SCHEMA partner; CREATE SCHEMA identity;
CREATE TABLE system.schema_migrations(migration_id text primary key,sha256 text not null);
CREATE TABLE public.rahgard_private_pilot_marker(marker_value text not null);
CREATE TABLE identity.users(user_id uuid primary key);
CREATE TABLE identity.catalogue_review_grants(user_id uuid,capability text,granted_by uuid,reason text,granted_at timestamptz default now(),revoked_at timestamptz);
CREATE TABLE partner.platform_grants(user_id uuid,capability text not null,granted_by uuid,reason text,granted_at timestamptz default now(),revoked_at timestamptz,
 CONSTRAINT platform_grants_capability_check CHECK(capability IN ('organization_review','service_review','offer_review')));
GRANT SELECT,INSERT,UPDATE ON partner.platform_grants TO ai_tourism_app;
CREATE FUNCTION partner.current_actor_id() RETURNS uuid LANGUAGE sql STABLE AS $$ SELECT NULLIF(current_setting('app.actor_id',true),'')::uuid $$;
CREATE FUNCTION partner.has_platform_capability(uuid,text) RETURNS boolean LANGUAGE sql STABLE AS $$ SELECT false $$;
'@ | docker exec -i -e "PGPASSWORD=$password" $ContainerName psql -X -q -v ON_ERROR_STOP=1 -U ai_tourism_owner -d rahgard_pilot_vps_staging
  if($LASTEXITCODE -ne 0){throw 'Isolated migration fixture setup failed.'}
  $ids=@('0000_legacy_tourism_points_baseline','0001_core_schema','0002_synthetic_knowledge_seed','0003_synthetic_e2e_seed','0004_app_role_grants','0005_verified_unesco_destination_seed','0006_verified_unesco_destination_seed_batch2','0007_shiraz_dalahoo_wikipedia_dataset_v1','0008_authentication_foundation','0009_traveler_core','0010_task31_content_privacy_full_itinerary','0011_internal_chat_turns','0012_task5_published_claim_evidence','0013_private_pilot_geo_audit','0016_staging_invitation_auth','0017_provisional_itineraries','0018_national_catalogue_ingestion','0019_partner_workspace','0020_archive_candidate_publication','0021_postgis_security_definer_publication','0022_traveler_company_requests','0023_partner_trip_responses')
  $ledger=($ids|ForEach-Object{"('$($_)',repeat('a',64))"}) -join ','
  $seed="INSERT INTO system.schema_migrations VALUES $ledger; INSERT INTO system.schema_migrations VALUES ('0024_partner_review_audit_actions','$hash24'); INSERT INTO public.rahgard_private_pilot_marker VALUES ('$marker'); REVOKE INSERT,UPDATE ON partner.platform_grants FROM ai_tourism_app;"
  $seed | docker exec -i -e "PGPASSWORD=$password" $ContainerName psql -X -q -v ON_ERROR_STOP=1 -U ai_tourism_owner -d rahgard_pilot_vps_staging
  if($LASTEXITCODE -ne 0){throw 'Migration ledger fixture setup failed.'}
  Get-Content -Raw -Encoding UTF8 -LiteralPath $m25 | docker exec -i -e "PGPASSWORD=$password" -e "RAHGARD_PILOT_DATABASE_MARKER=$marker" -e "RAHGARD_PILOT_MIGRATION_0024_SHA256=$hash24" -e "RAHGARD_PILOT_MIGRATION_0025_SHA256=$hash25" $ContainerName psql -X -v ON_ERROR_STOP=1 -U ai_tourism_owner -d rahgard_pilot_vps_staging
  if($LASTEXITCODE -ne 0){throw 'Migration 0025 failed in disposable PG17.'}
  $check=docker exec -e "PGPASSWORD=$password" $ContainerName psql -X -A -t -U ai_tourism_owner -d rahgard_pilot_vps_staging -c @'
SELECT (SELECT count(*) FROM system.schema_migrations WHERE migration_id='0025_owner_control_center')=1
 AND (SELECT count(*) FROM system.schema_migrations)=24
 AND (SELECT pg_get_constraintdef(oid) ILIKE '%admin_overview_read%' FROM pg_constraint WHERE conrelid='partner.platform_grants'::regclass AND conname='platform_grants_capability_check')
 AND NOT has_table_privilege('ai_tourism_app','partner.platform_grant_events','SELECT')
 AND NOT has_table_privilege('ai_tourism_app','partner.platform_grant_events','INSERT')
 AND NOT has_table_privilege('ai_tourism_app','partner.platform_grants','INSERT')
 AND NOT has_table_privilege('ai_tourism_app','partner.platform_grants','UPDATE');
'@
  if($LASTEXITCODE -ne 0 -or $check.Trim() -ne 't'){throw 'Migration 0025 postconditions failed.'}
  Write-Output "PASS isolated PostgreSQL 17 migration 0025; ledger=24; application role cannot directly mutate grants or read grant audit; sha256=$hash25"
} finally { if($started){docker stop $ContainerName *> $null;if($LASTEXITCODE -ne 0){Write-Warning 'Cleanup stop did not confirm; inspect only the named temporary container.'}} }
