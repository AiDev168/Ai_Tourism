# Disposable PostgreSQL 17 for the guarded Rahgard browser E2E.
# Runs ONLY inside a new container with tmpfs data, never the shared database.
[CmdletBinding()]
param([string]$ProjectRoot = (Get-Location).Path, [ValidateRange(1024,65535)][int]$Port = 55434)
$ErrorActionPreference = 'Stop'
if ($Port -eq 55433) { throw 'Shared port 55433 is forbidden.' }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker CLI not found.' }
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$SqlDir = Join-Path $ProjectRoot 'engineering\database-prep\sql'
$Legacy = Join-Path $ProjectRoot 'database\tourism_points.sql'
$Migration11 = Join-Path $SqlDir '011_internal_chat_turns.sql'
foreach ($file in @($SqlDir,$Legacy,$Migration11)) {
    if (-not (Test-Path -LiteralPath $file)) { throw "Required input missing: $file" }
}
if ((Get-Content -LiteralPath $Migration11 -Raw) -notmatch 'assistant_message_id\s+UUID\s+REFERENCES\s+conversation\.messages\(message_id\)\s+ON\s+DELETE\s+CASCADE') {
    throw 'Refusing obsolete migration 0011; assistant cascade fix required.'
}
$Image = 'ai-tourism-postgres:17-postgis36-vector087'
$ImageId = (& docker images --quiet $Image | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $ImageId) {
    throw 'Build image only: docker build -t ai-tourism-postgres:17-postgis36-vector087 -f engineering/database-prep/Dockerfile engineering/database-prep'
}
function Hex([int]$Length) {
    # Windows PowerShell 5.1 runs on .NET Framework: neither the static
    # RandomNumberGenerator.Fill nor Convert.ToHexString exists there.
    $buffer = New-Object byte[] $Length
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return [BitConverter]::ToString($buffer).Replace('-', '').ToLowerInvariant()
}
$Suffix = Hex 6
$Name = "ai-tourism-mvp-pg17-$Suffix"
$TestDb = "ai_tourism_auth_test_mvp_$Suffix"
$Owner = 'ai_tourism_owner'
$AppUser = 'ai_tourism_app'
$OwnerPassword = Hex 24
$AppPassword = Hex 24
$Marker = Hex 24
function Sql([string[]]$Options) {
    & docker exec $Name psql @Options | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Isolated psql command failed.' }
}
function Scalar([string]$Statement, [string]$Db = 'ai_tourism_dev') {
    $value = & docker exec $Name psql -X -A -t -v ON_ERROR_STOP=1 -U $Owner -d $Db -c $Statement
    if ($LASTEXITCODE -ne 0) { throw 'Isolated psql verification failed.' }
    return (($value | Out-String).Trim())
}
$Created = $false
try {
    $Publish = '127.0.0.1:' + $Port + ':5432'
    $SqlMount = 'type=bind,source=' + $SqlDir + ',target=/opt/ai-tourism/sql,readonly'
    $LegacyMount = 'type=bind,source=' + $Legacy + ',target=/opt/ai-tourism/legacy/tourism_points.sql,readonly'
    & docker run --detach --rm --name $Name --label 'ai-tourism.disposable-mvp-e2e=true' --publish $Publish --tmpfs '/var/lib/postgresql/data:rw,size=1024m' --mount $SqlMount --mount $LegacyMount --env 'POSTGRES_DB=ai_tourism_dev' --env ('POSTGRES_USER=' + $Owner) --env ('POSTGRES_PASSWORD=' + $OwnerPassword) $Image | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Disposable Docker container did not start.' }
    $Created = $true
    $Ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        & docker exec $Name pg_isready -U $Owner -d ai_tourism_dev | Out-Null
        if ($LASTEXITCODE -eq 0) { $Ready = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $Ready) { throw 'Disposable database is not ready.' }
    $Pg = [int](Scalar "SELECT current_setting('server_version_num');")
    if ($Pg -lt 170000 -or $Pg -ge 180000) { throw 'Expected PostgreSQL 17.' }
    Sql -Options @('-X','-v','ON_ERROR_STOP=1','-v',"app_user=$AppUser",'-v',"app_password=$AppPassword",'-U',$Owner,'-d','ai_tourism_dev','-f','/opt/ai-tourism/sql/000_bootstrap.sql')
    Sql -Options @('-X','-v','ON_ERROR_STOP=1','-U',$Owner,'-d','ai_tourism_dev','-f','/opt/ai-tourism/legacy/tourism_points.sql')
    $LegacyHash = (Get-FileHash -LiteralPath $Legacy -Algorithm SHA256).Hash.ToLowerInvariant()
    Sql -Options @('-X','-v','ON_ERROR_STOP=1','-U',$Owner,'-d','ai_tourism_dev','-c',"INSERT INTO system.schema_migrations (migration_id,sha256) VALUES ('0000_legacy_tourism_points_baseline','$LegacyHash');")
    $Migrations = @(
        '0001_core_schema|001_core_schema.sql',
        '0002_synthetic_knowledge_seed|002_synthetic_knowledge_seed.sql',
        '0003_synthetic_e2e_seed|003_synthetic_e2e_seed.sql',
        '0004_app_role_grants|004_app_role_grants.sql',
        '0005_verified_unesco_destination_seed|005_verified_unesco_destination_seed.sql',
        '0006_verified_unesco_destination_seed_batch2|006_verified_unesco_destination_seed_batch2.sql',
        '0007_shiraz_dalahoo_wikipedia_dataset_v1|007_shiraz_dalahoo_wikipedia_dataset_v1.sql',
        '0008_authentication_foundation|008_authentication_foundation.sql',
        '0009_traveler_core|009_traveler_core.sql',
        '0010_task31_content_privacy_full_itinerary|010_task31_content_privacy_full_itinerary.sql',
        '0011_internal_chat_turns|011_internal_chat_turns.sql'
    )
    foreach ($entry in $Migrations) {
        $parts = $entry.Split('|')
        $file = Join-Path $SqlDir $parts[1]
        if (-not (Test-Path -LiteralPath $file)) { throw "Migration not found: $file" }
        $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        $opts = @('-X','-v','ON_ERROR_STOP=1','-v',"migration_hash=$hash",'-U',$Owner,'-d','ai_tourism_dev')
        if ($parts[0] -eq '0004_app_role_grants') { $opts += @('-v',"app_user=$AppUser") }
        $opts += @('-f',"/opt/ai-tourism/sql/$($parts[1])")
        Sql -Options $opts
        if ((Scalar "SELECT sha256 FROM system.schema_migrations WHERE migration_id='$($parts[0])';") -ne $hash) {
            throw "Migration checksum mismatch: $($parts[0])"
        }
    }
    Sql -Options @('-X','-v','ON_ERROR_STOP=1','-U',$Owner,'-d','ai_tourism_dev','-c',"UPDATE operations.dataset_import_batches SET source_checksum='$LegacyHash' WHERE batch_key='legacy-user-supplied-destinations-v1';")
    if ((Scalar "SELECT source_checksum FROM operations.dataset_import_batches WHERE batch_key='legacy-user-supplied-destinations-v1';") -ne $LegacyHash) { throw 'Legacy checksum mismatch.' }
    $MarkerSql = "CREATE TABLE public.ai_tourism_auth_test_marker (marker_value TEXT NOT NULL); INSERT INTO public.ai_tourism_auth_test_marker (marker_value) VALUES ('$Marker'); GRANT USAGE ON SCHEMA public TO $AppUser; GRANT SELECT ON public.ai_tourism_auth_test_marker TO $AppUser; GRANT USAGE ON SCHEMA system TO $AppUser; GRANT SELECT ON system.schema_migrations TO $AppUser;"
    Sql -Options @('-X','-v','ON_ERROR_STOP=1','-U',$Owner,'-d','ai_tourism_dev','-c',$MarkerSql)
    # Rename only within this new disposable container to preserve historic migration 0004.
    Sql -Options @('-X','-v','ON_ERROR_STOP=1','-U',$Owner,'-d','postgres','-c',"ALTER DATABASE ai_tourism_dev RENAME TO $TestDb;")
    # Validate the same application role and marker the E2E harness will use.
    # Do not publish AUTH_TEST_DATABASE_* until the disposable target is proven.
    $MarkerCheckSql = "SELECT CASE WHEN current_database()='$TestDb' AND current_user='$AppUser' AND (SELECT COUNT(*) FROM public.ai_tourism_auth_test_marker)=1 AND (SELECT marker_value FROM public.ai_tourism_auth_test_marker LIMIT 1)='$Marker' AND (SELECT COUNT(*) FROM system.schema_migrations)=12 THEN 'ok' ELSE 'bad' END;"
    $MarkerCheck = & docker exec -e ("PGPASSWORD=" + $AppPassword) $Name psql -h 127.0.0.1 -X -A -t -v ON_ERROR_STOP=1 -U $AppUser -d $TestDb -c $MarkerCheckSql
    if ($LASTEXITCODE -ne 0 -or (($MarkerCheck | Out-String).Trim()) -ne 'ok') {
        throw 'Disposable application-role/marker/migration verification failed.'
    }
    $env:AUTH_INTEGRATION_TESTS = '1'
    $env:AUTH_TEST_DATABASE_HOST = '127.0.0.1'
    $env:AUTH_TEST_DATABASE_PORT = [string]$Port
    $env:AUTH_TEST_DATABASE_NAME = $TestDb
    $env:AUTH_TEST_DATABASE_USER = $AppUser
    $env:AUTH_TEST_DATABASE_PASSWORD = $AppPassword
    $env:AUTH_TEST_DATABASE_MARKER = $Marker
    $env:AI_TOURISM_MVP_E2E_CONTAINER = $Name
    Write-Host 'READY: isolated PostgreSQL 17 with migrations 0000-0011.' -ForegroundColor Green
    Write-Host 'AUTH_TEST_DATABASE_* and AUTH_INTEGRATION_TESTS set in current PowerShell.'
    Write-Host 'Run: node frontend/scripts/traveler-e2e.mjs'
    Write-Host 'After tests: docker stop $env:AI_TOURISM_MVP_E2E_CONTAINER'
} catch {
    if ($Created) { & docker stop $Name | Out-Null }
    throw
}
