[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('Start','Stop','Status','Backup','Restore','Upgrade','ProvisionProviderAdmin','RevokeProviderAdmin','Rollback','TrustCertificate','UntrustCertificate','BootstrapOwner','ResetOwner')]
    [string]$Action,
    [string]$DataRoot = (Join-Path $env:LOCALAPPDATA 'Rahgard\Issue6Pilot'),
    [switch]$InitializeDatabase,
    [switch]$ResumeInitialization,
    [switch]$ConfirmPrivatePilot,
    [switch]$PublishApprovedGeo,
    [switch]$ConfirmRestoreRehearsal,
    [switch]$ApplyProviderAdminMigration,
    [string]$ConfirmProviderAdminTarget,
    [string]$ProviderAdminUserId,
    [string]$ProviderAdminReason,
    [string]$Archive,
    [string]$RestoreTarget
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'Rahgard.LocalPilot.psm1') -Force
$Paths = Get-LocalPilotPaths $DataRoot
$ProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$BackendRoot = Join-Path $ProjectRoot 'backend'
$FrontendRoot = Join-Path $ProjectRoot 'frontend'
$SqlDir = Join-Path $ProjectRoot 'engineering\database-prep\sql'
$LegacySql = Join-Path $ProjectRoot 'database\tourism_points.sql'
$LocalSql = Join-Path $ProjectRoot 'engineering\pilot\sql'
$ApiPort = 8800
$HttpsPort = 8443
$DatabasePort = 55439
$ApiPidPath = Join-Path $Paths.Root 'api-process.json'
$ProxyPidPath = Join-Path $Paths.Root 'proxy-process.json'

function Invoke-LocalPilotDockerSql([string]$Sql, [string]$Database = $Paths.Database,
                                    [string]$User = 'ai_tourism_owner', [string[]]$PsqlArgs = @(),
                                    [string[]]$DockerArgs = @()) {
    $Sql | & docker exec @DockerArgs -i $Paths.Container psql -X -v ON_ERROR_STOP=1 @PsqlArgs -U $User -d $Database
    if ($LASTEXITCODE -ne 0) { throw 'Private local PostgreSQL command failed; no secrets or SQL output were recorded.' }
}

function Invoke-LocalPilotGuardedTcpSql([string]$Sql, [string]$Database = $Paths.Database,
                                        [string]$User = 'ai_tourism_owner', [string[]]$PsqlArgs = @(),
                                        [string[]]$DockerArgs = @()) {
    $suffix = [Guid]::NewGuid().ToString('N')
    $localPassFile = Join-Path $Paths.Secrets ('.pgpass-' + $suffix)
    $containerPassFile = '/tmp/rahgard-pgpass-' + $suffix
    $password = Get-Content -LiteralPath $Paths.OwnerPassword -Raw -Encoding ASCII
    if ($password -notmatch '^[a-f0-9]{80}$' -or $Database -notmatch '^rahgard_pilot_[a-z0-9_]{3,40}$') {
        throw 'Guarded TCP migration identity is invalid.'
    }
    try {
        [IO.File]::WriteAllText($localPassFile, "127.0.0.1:5432:${Database}:${User}:${password}`n", [Text.Encoding]::ASCII)
        Set-LocalPilotAcl $localPassFile
        & docker cp $localPassFile "$($Paths.Container):$containerPassFile" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Could not stage an ACL-protected temporary database authentication file.' }
        & docker exec $Paths.Container chmod 600 $containerPassFile | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Could not restrict the temporary database authentication file.' }
        $tcpArgs = @('-e',('PGPASSFILE=' + $containerPassFile),'-e','PGSSLMODE=prefer') + $DockerArgs
        $Sql | & docker exec @tcpArgs -i $Paths.Container psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 `
            @PsqlArgs -U $User -d $Database
        if ($LASTEXITCODE -ne 0) { throw 'Guarded loopback TCP PostgreSQL command failed; SQL output was not recorded.' }
    } finally {
        & docker exec $Paths.Container rm -f $containerPassFile 2>$null | Out-Null
        if (Test-Path -LiteralPath $localPassFile) { Remove-Item -LiteralPath $localPassFile -Force }
    }
}

function Get-LocalPilotMarker {
    $value = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database `
        -c 'SELECT marker_value FROM public.rahgard_private_pilot_marker'
    if ($LASTEXITCODE -ne 0 -or ($value | Measure-Object -Line).Lines -ne 1 -or
        (($value | Out-String).Trim() -notmatch '^[a-fA-F0-9]{32,128}$')) {
        throw 'Private-pilot safety marker did not verify.'
    }
    return ($value | Out-String).Trim()
}

function Assert-LocalPilotReady($State) {
    $container = Get-LocalPilotContainer $Paths
    if (-not $container -or $container.State.Status -ne 'running') { throw 'Persistent local PostgreSQL container is not running.' }
    if ([int]$container.HostConfig.PortBindings.'5432/tcp'[0].HostPort -ne [int]$State.database_port) {
        throw 'Persistent database port differs from recorded pilot state.'
    }
    if ([int]$State.migration_count -notin @(15,16)) { throw 'Local pilot migration ledger is not at a reviewed migration baseline.' }
    $marker = Get-LocalPilotMarker
    if (-not [string]::Equals($marker, [string]$State.marker, [StringComparison]::Ordinal)) {
        throw 'Persistent local-pilot marker changed.'
    }
    $actual = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database `
        -c 'SELECT count(*) FROM system.schema_migrations'
    if ($LASTEXITCODE -ne 0 -or [int](($actual | Out-String).Trim()) -ne [int]$State.migration_count) {
        throw 'Persistent migration ledger does not match local-pilot state.'
    }
    if ([int]$State.migration_count -eq 16) {
        $migration = Join-Path $LocalSql '015_ai_provider_admin.sql'
        if (-not (Test-Path -LiteralPath $migration) -or
            (Get-FileHash -LiteralPath $migration -Algorithm SHA256).Hash.ToLowerInvariant() -ne [string]$State.migration_0015_sha256) {
            throw 'Provider-admin migration hash does not match the reviewed local-pilot state.'
        }
    }
    return $container
}

function Assert-LocalPilotDatabaseTls($State) {
    if (-not (Test-Path -LiteralPath $Paths.DatabaseCertificate)) { throw 'PostgreSQL trust certificate is missing.' }
    Assert-LocalPilotAcl $Paths.DatabaseCertificate
    $certHash = (Get-FileHash -LiteralPath $Paths.DatabaseCertificate -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($State.database_certificate_sha256 -and $State.database_certificate_sha256 -ne $certHash) {
        throw 'PostgreSQL trust certificate checksum differs from the initialized pilot state.'
    }
    $python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw 'Repository-local Python is unavailable for verify-full TLS validation.' }
    $probeScript = Join-Path $PSScriptRoot 'check_postgres_tls.py'
    if (-not (Test-Path -LiteralPath $probeScript)) { throw 'Local PostgreSQL TLS probe script is missing.' }
    $envMap = @{
        DATABASE_HOST='127.0.0.1'; DATABASE_PORT=[string]$State.database_port; DATABASE_NAME=$Paths.Database
        DATABASE_USER='ai_tourism_app'; DATABASE_PASSWORD=(Read-LocalPilotSecret $Paths.AppPassword)
        RAHGARD_PILOT_DATABASE_MARKER=$State.marker; PGSSLMODE='verify-full'; PGSSLROOTCERT=$Paths.DatabaseCertificate
    }
    $stdout = Join-Path $Paths.Logs 'postgres-tls-check.log'; $stderr = Join-Path $Paths.Logs 'postgres-tls-check-error.log'
    foreach ($logFile in @($stdout,$stderr)) {
        if (Test-Path -LiteralPath $logFile) { Assert-LocalPilotAcl $logFile }
        [IO.File]::WriteAllText($logFile,'',[Text.Encoding]::UTF8)
        Set-LocalPilotAcl $logFile
    }
    $proc = Start-LocalPilotProcess -File $python -Arguments @($probeScript) -WorkingDirectory $BackendRoot `
        -Environment $envMap -Stdout $stdout -Stderr $stderr
    $tlsExitCode = [int]$proc.ExitCode
    if ($tlsExitCode -ne 0 -or -not (Get-Content -LiteralPath $stdout -Raw -ErrorAction SilentlyContinue).Contains('LOCAL_PILOT_VERIFY_FULL_TLS_OK')) {
        throw 'Local PostgreSQL verify-full TLS identity check failed; inspect ACL-protected diagnostics.'
    }
    return $certHash
}

function Apply-LocalPilotBaseMigrations([string]$AppPassword) {
    if (Test-Path -LiteralPath (Join-Path $BackendRoot '.env')) {
        throw 'Refusing local startup because backend/.env exists. This runner does not read dotenv files.'
    }
    if (-not (Test-Path -LiteralPath $LegacySql) -or -not (Test-Path -LiteralPath (Join-Path $SqlDir '012_task5_published_claim_evidence.sql'))) {
        throw 'Required repository migration inputs are missing.'
    }
    $bootstrap = @"
\set ON_ERROR_STOP on
\set app_user ai_tourism_app
\set app_password '$AppPassword'
\i /opt/rahgard/sql/000_bootstrap.sql
"@
    Invoke-LocalPilotDockerSql $bootstrap -Database $Paths.Database
    $legacyHash = (Get-FileHash -LiteralPath $LegacySql -Algorithm SHA256).Hash.ToLowerInvariant()
    & docker exec $Paths.Container psql -X -v ON_ERROR_STOP=1 -U ai_tourism_owner -d $Paths.Database `
        -f /opt/rahgard/legacy/tourism_points.sql | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'The local pilot baseline import failed.' }
    Invoke-LocalPilotDockerSql "INSERT INTO system.schema_migrations(migration_id,sha256) VALUES ('0000_legacy_tourism_points_baseline','$legacyHash')" -Database $Paths.Database

    $entries = @(
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
        '0011_internal_chat_turns|011_internal_chat_turns.sql',
        '0012_task5_published_claim_evidence|012_task5_published_claim_evidence.sql'
    )
    foreach ($entry in $entries) {
        $parts = $entry.Split('|')
        $file = Join-Path $SqlDir $parts[1]
        if (-not (Test-Path -LiteralPath $file)) { throw "Required migration missing: $($parts[1])" }
        $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        $wrapper = "\set ON_ERROR_STOP on`n\set migration_hash $hash`n"
        if ($parts[0] -eq '0004_app_role_grants') { $wrapper += "\set app_user ai_tourism_app`n" }
        if ($parts[0] -eq '0004_app_role_grants') {
            # The immutable legacy migration names the shared development DB.
            # Execute only an in-memory, exact one-token local-pilot adaptation;
            # the recorded checksum remains the hash of the original file.
            $migrationText = Get-Content -LiteralPath $file -Raw -Encoding UTF8
            $needle = 'GRANT CONNECT ON DATABASE ai_tourism_dev TO :"app_user";'
            if (-not $migrationText.Contains($needle) -or ([regex]::Matches($migrationText,[regex]::Escape('ai_tourism_dev'))).Count -ne 1) {
                throw 'The immutable app-role migration no longer matches the reviewed local-pilot adaptation.'
            }
            $migrationText = $migrationText.Replace($needle, "GRANT CONNECT ON DATABASE $($Paths.Database) TO :`"app_user`";")
            $wrapper += $migrationText
            Invoke-LocalPilotDockerSql $wrapper -Database $Paths.Database
        } else {
            $wrapper += "\i /opt/rahgard/sql/$($parts[1])`n"
            Invoke-LocalPilotDockerSql $wrapper -Database $Paths.Database
        }
        $savedHash = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database `
            -c "SELECT sha256 FROM system.schema_migrations WHERE migration_id='$($parts[0])'"
        if ($LASTEXITCODE -ne 0 -or ($savedHash | Out-String).Trim() -ne $hash) {
            throw "Migration checksum did not verify for $($parts[0])."
        }
    }
    $marker = New-LocalPilotRandomHex 24
    Invoke-LocalPilotDockerSql "GRANT CONNECT ON DATABASE $($Paths.Database) TO ai_tourism_app; CREATE TABLE public.rahgard_private_pilot_marker(marker_value TEXT NOT NULL); INSERT INTO public.rahgard_private_pilot_marker VALUES ('$marker'); GRANT SELECT ON public.rahgard_private_pilot_marker TO ai_tourism_app" -Database $Paths.Database
    return @{ marker = $marker; migration_0012_hash = (Get-FileHash -LiteralPath (Join-Path $SqlDir '012_task5_published_claim_evidence.sql') -Algorithm SHA256).Hash.ToLowerInvariant() }
}

function Install-LocalPilotGeoRoles($MigrationInfo) {
    $roleState = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database -c @'
SELECT CASE
  WHEN count(*)=0 THEN 'absent'
  WHEN count(*)=4 AND bool_and(NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolbypassrls)
       AND bool_and(rolcanlogin = (rolname IN ('rahgard_pilot_geo_authorizer','rahgard_pilot_geo_publisher')))
       AND pg_has_role('rahgard_pilot_geo_migrator','rahgard_pilot_geo_executor','MEMBER') THEN 'setup_ready'
  WHEN count(*)=4 AND bool_and(NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolbypassrls)
       AND bool_and(rolcanlogin = (rolname IN ('rahgard_pilot_geo_authorizer','rahgard_pilot_geo_publisher')))
       AND NOT pg_has_role('rahgard_pilot_geo_migrator','rahgard_pilot_geo_executor','MEMBER') THEN 'migration_complete'
  ELSE 'conflict' END
FROM pg_catalog.pg_roles
WHERE rolname IN ('rahgard_pilot_geo_executor','rahgard_pilot_geo_migrator',
                  'rahgard_pilot_geo_authorizer','rahgard_pilot_geo_publisher')
'@ 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Could not verify private geo migration roles.' }
    $roleState = ($roleState | Out-String).Trim()
    if ($roleState -eq 'conflict') { throw 'Existing private geo roles differ from the reviewed local-pilot contract.' }
    $migration13 = Join-Path $LocalSql '013_private_pilot_geo_audit.sql'
    $hash13 = (Get-FileHash -LiteralPath $migration13 -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($roleState -eq 'migration_complete') {
        $appliedHash = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database `
            -c "SELECT sha256 FROM system.schema_migrations WHERE migration_id='0013_private_pilot_geo_audit'" 2>$null
        if ($LASTEXITCODE -ne 0 -or ($appliedHash | Out-String).Trim() -ne $hash13) {
            throw 'Completed geo migration roles do not match the recorded 0013 checksum.'
        }
        foreach ($secret in @($Paths.GeoMigratorPassword,$Paths.GeoAuthorizerPassword,$Paths.GeoPublisherPassword)) { $null = Read-LocalPilotSecret $secret }
        return @{ hash_0013 = $hash13 }
    }
    if ($roleState -eq 'absent') {
        foreach ($secret in @($Paths.GeoMigratorPassword,$Paths.GeoAuthorizerPassword,$Paths.GeoPublisherPassword)) {
            if (Test-Path -LiteralPath $secret) { throw 'Geo role secrets exist without corresponding database roles; refusing credential replacement.' }
        }
        $geoMigrator = New-LocalPilotRandomHex 32
        $authenticator = New-LocalPilotRandomHex 32
        $publisher = New-LocalPilotRandomHex 32
        Save-LocalPilotSecret $Paths.GeoMigratorPassword $geoMigrator
        Save-LocalPilotSecret $Paths.GeoAuthorizerPassword $authenticator
        Save-LocalPilotSecret $Paths.GeoPublisherPassword $publisher
        $setup = "\set ON_ERROR_STOP on`n\set migrator_pw '$geoMigrator'`n\set authorizer_pw '$authenticator'`n\set publisher_pw '$publisher'`n" + @'
\set ON_ERROR_STOP on
BEGIN;
CREATE ROLE rahgard_pilot_geo_executor NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_geo_migrator NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT rahgard_pilot_geo_executor TO rahgard_pilot_geo_migrator;
CREATE ROLE rahgard_pilot_geo_authorizer LOGIN PASSWORD :'authorizer_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_geo_publisher LOGIN PASSWORD :'publisher_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT USAGE ON SCHEMA knowledge, operations, system, public TO rahgard_pilot_geo_migrator;
GRANT CREATE ON SCHEMA operations TO rahgard_pilot_geo_migrator, rahgard_pilot_geo_executor;
GRANT SELECT ON knowledge.destinations, knowledge.destination_sources, knowledge.knowledge_sources,
    system.schema_migrations, public.rahgard_private_pilot_marker TO rahgard_pilot_geo_migrator, rahgard_pilot_geo_executor;
GRANT INSERT ON system.schema_migrations TO rahgard_pilot_geo_migrator;
GRANT UPDATE(status,updated_at), REFERENCES(destination_key) ON knowledge.destinations TO rahgard_pilot_geo_migrator;
GRANT UPDATE(status,updated_at) ON knowledge.destinations TO rahgard_pilot_geo_executor;
COMMIT;
'@
        Invoke-LocalPilotDockerSql $setup -Database $Paths.Database
    } else {
        foreach ($secret in @($Paths.GeoMigratorPassword,$Paths.GeoAuthorizerPassword,$Paths.GeoPublisherPassword)) {
            if (-not (Test-Path -LiteralPath $secret)) { throw 'A private geo database role is present without its protected credential.' }
            $null = Read-LocalPilotSecret $secret
        }
    }
    if ($roleState -eq 'setup_ready') {
        foreach ($secret in @($Paths.GeoMigratorPassword,$Paths.GeoAuthorizerPassword,$Paths.GeoPublisherPassword)) { $null = Read-LocalPilotSecret $secret }
    }
    $migration13Sql = "\set ON_ERROR_STOP on`n\set migration_hash $hash13`nSET ROLE rahgard_pilot_geo_migrator;`n\i /opt/rahgard/pilot-sql/013_private_pilot_geo_audit.sql`nRESET ROLE;`n"
    $dockerArgs = @('-e', ('RAHGARD_PILOT_DATABASE_MARKER=' + $MigrationInfo.marker),
                    '-e', ('RAHGARD_PILOT_MIGRATION_0012_SHA256=' + $MigrationInfo.migration_0012_hash))
    Invoke-LocalPilotGuardedTcpSql $migration13Sql -Database $Paths.Database -DockerArgs $dockerArgs
    try {
        Invoke-LocalPilotDockerSql @'
REVOKE CREATE ON SCHEMA operations FROM rahgard_pilot_geo_migrator, rahgard_pilot_geo_executor;
REVOKE rahgard_pilot_geo_executor FROM rahgard_pilot_geo_migrator;
GRANT USAGE ON SCHEMA operations,knowledge,public,system TO rahgard_pilot_geo_authorizer,rahgard_pilot_geo_publisher;
GRANT SELECT ON system.schema_migrations, public.rahgard_private_pilot_marker,
    knowledge.destinations,knowledge.destination_sources,knowledge.knowledge_sources TO rahgard_pilot_geo_authorizer;
GRANT INSERT ON operations.private_pilot_geo_authorizations TO rahgard_pilot_geo_authorizer;
GRANT EXECUTE ON FUNCTION operations.apply_private_geo_approval(TEXT,TEXT,TEXT,TEXT,TEXT,TIMESTAMPTZ)
    TO rahgard_pilot_geo_publisher;
'@ -Database $Paths.Database
        return @{ hash_0013 = $hash13 }
    } catch {
        throw
    }
}

function Start-LocalPilotProcess([string]$File, [string[]]$Arguments, [string]$WorkingDirectory,
                                 [hashtable]$Environment, [string]$Stdout, [string]$Stderr) {
    $preserve = @('PATH','SystemRoot','SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE','LOCALAPPDATA','APPDATA','COMSPEC')
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = $File
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.EnvironmentVariables.Clear()
    foreach ($name in $preserve) {
        $value = [Environment]::GetEnvironmentVariable($name,'Process')
        if ($null -ne $value) { $psi.EnvironmentVariables[$name] = $value }
    }
    foreach ($name in $Environment.Keys) { $psi.EnvironmentVariables[[string]$name] = [string]$Environment[$name] }
    $psi.Arguments = (($Arguments | ForEach-Object { ConvertTo-LocalPilotCommandArgument ([string]$_) }) -join ' ')
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $psi
    if (-not $process.Start()) { throw 'Local pilot child process could not be started.' }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $outText = $stdoutTask.Result
    $errText = $stderrTask.Result
    if ($outText) { [IO.File]::AppendAllText($Stdout,$outText,[Text.Encoding]::UTF8) }
    if ($errText) { [IO.File]::AppendAllText($Stderr,$errText,[Text.Encoding]::UTF8) }
    foreach ($logFile in @($Stdout,$Stderr)) {
        if (Test-Path -LiteralPath $logFile) {
            $logAcl = Get-Acl -LiteralPath $logFile
            if (-not $logAcl.AreAccessRulesProtected) { Set-LocalPilotAcl $logFile }
            else { Assert-LocalPilotAcl $logFile }
        }
    }
    $exitCode = $process.ExitCode
    $process.Dispose()
    return [pscustomobject]@{ ExitCode=[int]$exitCode }
}

function Start-LocalPilotBackgroundProcess([string]$File, [string[]]$Arguments, [string]$WorkingDirectory,
                                           [hashtable]$Environment, [string]$Stdout, [string]$Stderr) {
    $preserve = @('PATH','SystemRoot','SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE','LOCALAPPDATA','APPDATA','COMSPEC')
    $names = @([Environment]::GetEnvironmentVariables().Keys | ForEach-Object { [string]$_ } |
        Where-Object { $_ -notin $preserve }) + @($Environment.Keys)
    $names = @($names | Select-Object -Unique)
    $saved = @{}
    foreach ($name in $names) {
        $old = Get-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
        if ($old) { $saved[$name] = [string]$old.Value }
    }
    try {
        foreach ($name in $names) {
            if ($Environment.ContainsKey($name)) { Set-Item -LiteralPath "Env:$name" -Value ([string]$Environment[$name]) }
            else { Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue }
        }
        $argumentLine = ($Arguments | ForEach-Object { ConvertTo-LocalPilotCommandArgument ([string]$_) }) -join ' '
        $process = Start-Process -FilePath $File -ArgumentList $argumentLine -WorkingDirectory $WorkingDirectory `
            -WindowStyle Hidden -PassThru -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr
        foreach ($logFile in @($Stdout,$Stderr)) { if (Test-Path -LiteralPath $logFile) { Set-LocalPilotAcl $logFile } }
        return $process
    } finally {
        foreach ($name in $names) {
            if ($saved.ContainsKey($name)) { Set-Item -LiteralPath "Env:$name" -Value $saved[$name] }
            else { Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue }
        }
    }
}

function ConvertTo-LocalPilotCommandArgument([string]$Value) {
    if ($Value.Length -gt 0 -and $Value -notmatch '[\s"]') { return $Value }
    $builder = New-Object System.Text.StringBuilder
    [void]$builder.Append('"')
    $slashes = 0
    foreach ($character in $Value.ToCharArray()) {
        if ($character -eq '\') { $slashes++; continue }
        if ($character -eq '"') {
            [void]$builder.Append(('\' * (2 * $slashes + 1)))
            [void]$builder.Append('"')
            $slashes = 0
            continue
        }
        if ($slashes) { [void]$builder.Append(('\' * $slashes)); $slashes = 0 }
        [void]$builder.Append($character)
    }
    if ($slashes) { [void]$builder.Append(('\' * (2 * $slashes))) }
    [void]$builder.Append('"')
    return $builder.ToString()
}


function Enable-LocalPilotDatabaseTls {
    $certExists = & docker exec $Paths.Container sh -lc 'test -s /var/lib/postgresql/data/server.crt' 2>$null
    $certCode = $LASTEXITCODE
    $keyExists = & docker exec $Paths.Container sh -lc 'test -s /var/lib/postgresql/data/server.key' 2>$null
    $keyCode = $LASTEXITCODE
    if ($certCode -gt 1 -or $keyCode -gt 1) { throw 'Could not inspect PostgreSQL TLS files in the exact local-pilot container.' }
    if (($certCode -eq 0) -xor ($keyCode -eq 0)) { throw 'PostgreSQL TLS files are only partially present; refusing replacement.' }
    $needsRestart = $false
    if ($certCode -ne 0) {
        $command = "openssl req -new -x509 -nodes -days 730 -newkey rsa:3072 -keyout /var/lib/postgresql/data/server.key -out /var/lib/postgresql/data/server.crt -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1' && chmod 600 /var/lib/postgresql/data/server.key && chown postgres:postgres /var/lib/postgresql/data/server.key /var/lib/postgresql/data/server.crt"
        & docker exec $Paths.Container sh -lc $command | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Could not create private PostgreSQL localhost TLS material.' }
        $needsRestart = $true
    }
    $san = & docker exec $Paths.Container openssl x509 -in /var/lib/postgresql/data/server.crt -noout -ext subjectAltName 2>$null
    if ($LASTEXITCODE -ne 0 -or ($san | Out-String) -notmatch 'DNS:localhost' -or ($san | Out-String) -notmatch '127\.0\.0\.1') {
        throw 'Persistent PostgreSQL TLS certificate does not have both localhost DNS and loopback IP SANs.'
    }
    $settings = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d postgres `
        -c "SELECT current_setting('ssl')||'|'||current_setting('ssl_cert_file')||'|'||current_setting('ssl_key_file')" 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Could not verify PostgreSQL TLS configuration.' }
    if (($settings | Out-String).Trim() -ne 'on|server.crt|server.key') {
        foreach ($setting in @("ALTER SYSTEM SET ssl='on'", "ALTER SYSTEM SET ssl_cert_file='server.crt'", "ALTER SYSTEM SET ssl_key_file='server.key'")) {
            & docker exec $Paths.Container psql -X -v ON_ERROR_STOP=1 -U ai_tourism_owner -d postgres -c $setting | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'Could not configure PostgreSQL TLS.' }
        }
        $needsRestart = $true
    }
    if ($needsRestart) {
        & docker restart $Paths.Container | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Could not restart PostgreSQL to enable TLS.' }
        $ready = $false
        for ($attempt=0; $attempt -lt 60; $attempt++) {
            & docker exec $Paths.Container pg_isready -U ai_tourism_owner -d $Paths.Database | Out-Null
            if ($LASTEXITCODE -eq 0) { $ready = $true; break }
            Start-Sleep -Seconds 1
        }
        if (-not $ready) { throw 'PostgreSQL did not become ready after TLS configuration.' }
    }
    $temporaryCertificate = Join-Path $Paths.Secrets ('postgres-root-' + [Guid]::NewGuid().ToString('N') + '.crt')
    & docker cp "$($Paths.Container):/var/lib/postgresql/data/server.crt" $temporaryCertificate | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not read the PostgreSQL public root certificate.' }
    Set-LocalPilotAcl $temporaryCertificate
    try {
        if (Test-Path -LiteralPath $Paths.DatabaseCertificate) {
            Assert-LocalPilotAcl $Paths.DatabaseCertificate
            if ((Get-FileHash -LiteralPath $Paths.DatabaseCertificate -Algorithm SHA256).Hash -ne
                (Get-FileHash -LiteralPath $temporaryCertificate -Algorithm SHA256).Hash) {
                throw 'The stored PostgreSQL trust certificate differs from the bound data directory.'
            }
        } else {
            Move-Item -LiteralPath $temporaryCertificate -Destination $Paths.DatabaseCertificate
        }
    } finally {
        if (Test-Path -LiteralPath $temporaryCertificate) { Remove-Item -LiteralPath $temporaryCertificate -Force }
    }
    Assert-LocalPilotAcl $Paths.DatabaseCertificate
}

function New-LocalPilotContainer($ImageId, [string]$OwnerPassword) {
    $initialState = Read-LocalPilotState $Paths
    if (-not $initialState -or $initialState.lifecycle -ne 'initializing') { throw 'A matching initializing state is required before creating the persistent database.' }
    $items = @(Get-ChildItem -LiteralPath $Paths.Db -Force)
    if ($items.Count) { throw 'PostgreSQL data directory is not empty; refusing to overwrite existing data.' }
    $sqlDirectory = [IO.Path]::GetFullPath($SqlDir)
    $legacyPath = [IO.Path]::GetFullPath($LegacySql)
    $pilotSql = [IO.Path]::GetFullPath($LocalSql)
    $geoBatch = [IO.Path]::GetFullPath((Join-Path $ProjectRoot 'engineering\pilot\geo-visibility-approved-localpilot-2026-11-11.json'))
    $mounts = @(
        ('type=bind,source=' + $Paths.Db + ',target=/var/lib/postgresql/data'),
        ('type=bind,source=' + $sqlDirectory + ',target=/opt/rahgard/sql,readonly'),
        ('type=bind,source=' + $legacyPath + ',target=/opt/rahgard/legacy/tourism_points.sql,readonly'),
        ('type=bind,source=' + $pilotSql + ',target=/opt/rahgard/pilot-sql,readonly'),
        ('type=bind,source=' + $geoBatch + ',target=/opt/rahgard/pilot/geo-visibility-approved-localpilot-2026-11-11.json,readonly'),
        ('type=bind,source=' + $Paths.OwnerPassword + ',target=/run/secrets/postgres-owner-password,readonly')
    )
    foreach ($sourcePath in @($Paths.Db,$Paths.SqlDirectory,$Paths.LegacySql,$Paths.PilotSql,$geoBatch,$Paths.OwnerPassword)) {
        if ([string]$sourcePath -match '[,\r\n]') { throw 'Pilot bind mount path contains an unsupported delimiter.' }
    }
    if (-not (Test-Path -LiteralPath $geoBatch)) { throw 'Owner-approved local geographic batch is missing.' }
    $all = @('--detach','--name',$Paths.Container,'--label','rahgard.local-pilot=true',
        '--label',('rahgard.local-pilot-root=' + $Paths.RootHash),'--restart','unless-stopped',
        '--publish',"127.0.0.1:$DatabasePort`:5432",'--shm-size','128m')
    foreach ($mount in $mounts) { $all += @('--mount',$mount) }
    $all += @('--env',('POSTGRES_DB=' + $Paths.Database),'--env','POSTGRES_USER=ai_tourism_owner',
        '--env','POSTGRES_PASSWORD_FILE=/run/secrets/postgres-owner-password',
        '--env','POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256',$Paths.Image)
    & docker run @all | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Persistent PostgreSQL container did not start; the bind-mounted data remains for inspection.' }
    $container = Get-LocalPilotContainer $Paths
    if (-not $container -or $container.State.Status -ne 'running') { throw 'New persistent PostgreSQL container identity did not verify.' }
    $ready = $false
    for ($attempt=0; $attempt -lt 90; $attempt++) {
        $probe = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database -c 'SELECT 1' 2>$null
        if ($LASTEXITCODE -eq 0 -and ($probe | Out-String).Trim() -eq '1') { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'PostgreSQL did not complete initialization of the local pilot database.' }
}

function Publish-ApprovedLocalGeo($Paths, $MigrationInfo, [bool]$Confirmed) {
    if (-not $Confirmed) { throw 'Explicit target-bound approval is required before local geographic publication.' }
    $packet = Join-Path $ProjectRoot 'engineering\pilot\geo-visibility-approved-localpilot-2026-11-11.json'
    $hmacPath = Join-Path $Paths.Secrets 'geo-owner-authorization-key.dpapi'
    if (-not (Test-Path -LiteralPath $hmacPath)) { Save-LocalPilotSecret $hmacPath (New-LocalPilotRandomHex 32) }
    $ownerKey = Read-LocalPilotSecret $hmacPath
    $marker = $MigrationInfo.marker
    $targetAuth = Join-Path $Paths.Secrets 'geo-target-authorization.json'
    if (Test-Path -LiteralPath $targetAuth) {
        Assert-LocalPilotAcl $targetAuth
        try { $priorAuth = Get-Content -LiteralPath $targetAuth -Raw -Encoding UTF8 | ConvertFrom-Json }
        catch { throw 'Existing target authorization is malformed; preserving it for manual review.' }
        if ($priorAuth.host -ne '127.0.0.1' -or [int]$priorAuth.port -ne $DatabasePort -or $priorAuth.database -ne $Paths.Database) {
            throw 'Existing target authorization is bound to a different local target; preserving it.'
        }
        if ([DateTimeOffset]::Parse([string]$priorAuth.expires_at).ToUniversalTime() -le [DateTimeOffset]::UtcNow) {
            $targetAuth = Join-Path $Paths.Secrets ('geo-target-authorization-' + [Guid]::NewGuid().ToString('N') + '.json')
        }
    }
    $python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw 'Repository-local Python environment is not available.' }
    if (Test-Path -LiteralPath $targetAuth) {
        Assert-LocalPilotAcl $targetAuth
    } else {
        $signEnv = @{
            RAHGARD_PILOT_OWNER_AUTHORIZATION_KEY=$ownerKey
            RAHGARD_PILOT_DATABASE_MARKER=$marker
        }
        $signer = Join-Path $BackendRoot 'scripts\rahgard_sign_pilot_geo_authorization.py'
        $signProcess = Start-LocalPilotProcess -File $python -Arguments @($signer,'--decisions',$packet,
            '--host','127.0.0.1','--port',[string]$DatabasePort,'--database',$Paths.Database,
            '--output',$targetAuth,'--owner-authorizes-target') -WorkingDirectory $BackendRoot -Environment $signEnv `
            -Stdout (Join-Path $Paths.Logs 'geo-sign.log') -Stderr (Join-Path $Paths.Logs 'geo-sign-error.log')
        $signExitCode = [int]$signProcess.ExitCode
        if ($signExitCode -ne 0) { throw 'Target-bound owner geographic authorization signing failed.' }
        if (-not (Test-Path -LiteralPath $targetAuth)) { throw 'Owner authorization file was not produced.' }
        Set-LocalPilotAcl $targetAuth
    }

    $runtimeEnv = @{
        RAHGARD_PILOT_PGHOST='127.0.0.1'; RAHGARD_PILOT_PGPORT=[string]$DatabasePort
        RAHGARD_PILOT_DATABASE=$Paths.Database; RAHGARD_PILOT_DATABASE_MARKER=$marker
        RAHGARD_PILOT_OWNER_AUTHORIZATION_KEY=$ownerKey
        PGSSLROOTCERT=$Paths.DatabaseCertificate
        RAHGARD_PILOT_GEO_AUTHORIZER_PASSWORD=(Read-LocalPilotSecret $Paths.GeoAuthorizerPassword)
        RAHGARD_PILOT_GEO_PUBLISHER_PASSWORD=(Read-LocalPilotSecret $Paths.GeoPublisherPassword)
    }
    $packetData = Get-Content -LiteralPath $packet -Raw -Encoding UTF8 | ConvertFrom-Json
    $keys = @($packetData.records | ForEach-Object { [string]$_.destination_key } | Sort-Object)
    if ($keys.Count -ne 4 -or @($keys | Where-Object { $_ -notmatch '^[a-z0-9][a-z0-9-]{2,100}$' }).Count) {
        throw 'Approved geographic packet does not contain four valid canonical keys.'
    }
    $decisionHash = (Get-FileHash -LiteralPath $packet -Algorithm SHA256).Hash.ToLowerInvariant()
    $markerHasher = [Security.Cryptography.SHA256]::Create()
    try { $markerHash = [BitConverter]::ToString($markerHasher.ComputeHash([Text.Encoding]::ASCII.GetBytes($marker))).Replace('-','').ToLowerInvariant() }
    finally { $markerHasher.Dispose() }
    $keyList = ($keys | ForEach-Object { "'$_'" }) -join ','
    $roleClauses = @()
    foreach ($record in $packetData.records) {
        $key = [string]$record.destination_key
        $role = [string]$record.coordinate_role
        if ($key -notin @('shiraz-hafezieh-v1','shiraz-eram-garden-v1','shiraz-vakil-bazaar-v1','unesco-persepolis-v1') -or
            $role -notin @('representative_point','property_reference')) { throw 'Approved point key or coordinate role is outside the private local packet contract.' }
        $roleClauses += "WHEN '$key' THEN '$role'"
    }
    $roleCase = 'CASE a.destination_key ' + ($roleClauses -join ' ') + ' ELSE NULL END'
    $publicationStatus = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database `
        -c "SELECT CASE WHEN count(*)=0 THEN 'not_published' WHEN count(*)=4 AND (SELECT count(*) FROM operations.private_pilot_geo_approvals)=4 AND count(DISTINCT a.destination_key)=4 AND bool_and(a.decision_sha256='$decisionHash' AND a.marker_sha256='$markerHash' AND d.status='active' AND a.coordinate_role=($roleCase)) AND (SELECT count(*) FROM knowledge.production_destinations WHERE destination_key IN ($keyList))=4 THEN 'published' ELSE 'conflict' END FROM operations.private_pilot_geo_approvals a JOIN knowledge.destinations d USING(destination_key) WHERE a.destination_key IN ($keyList)" 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Could not verify the already-published owner batch.' }
    $publicationStatus = ($publicationStatus | Out-String).Trim()
    if ($publicationStatus -eq 'published') { return $decisionHash }
    if ($publicationStatus -eq 'conflict') { throw 'A partial or mismatched local geographic approval set requires manual review.' }
    $authorizationStatus = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database `
        -c "SELECT CASE WHEN count(*)=4 AND count(DISTINCT destination_key)=4 AND bool_and(decision_sha256='$decisionHash') AND bool_and(marker_sha256='$markerHash') AND bool_and(expires_at>now()) THEN 'ready' ELSE 'incomplete' END FROM operations.private_pilot_geo_authorizations WHERE destination_key IN ($keyList)" 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Could not verify the exact owner authorization batch before publication.' }
    $stages = @()
    if (($authorizationStatus | Out-String).Trim() -ne 'ready') {
        $stages += @{File='rahgard_private_geo_authorize.py'; Args=@('--decisions',$packet,'--target-authorization',$targetAuth,'--provision-owner-authorization')}
    }
    Invoke-LocalPilotDockerSql @'
GRANT USAGE ON SCHEMA operations, knowledge, public, system TO rahgard_pilot_geo_executor;
GRANT SELECT ON system.schema_migrations, public.rahgard_private_pilot_marker,
    knowledge.production_destinations TO rahgard_pilot_geo_publisher;
'@ -Database $Paths.Database
    $stages += @{File='rahgard_private_geo_publication.py'; Args=@('--decisions',$packet,'--target-authorization',$targetAuth,'--apply-approved-geo')}
    foreach ($stage in $stages) {
        $script = Join-Path $BackendRoot ('scripts\' + $stage.File)
        $proc = Start-LocalPilotProcess -File $python -Arguments (@($script) + $stage.Args) -WorkingDirectory $BackendRoot `
            -Environment $runtimeEnv -Stdout (Join-Path $Paths.Logs ($stage.File + '.log')) `
            -Stderr (Join-Path $Paths.Logs ($stage.File + '.error.log'))
        $exitCode = [int]$proc.ExitCode
        if ($exitCode -ne 0) { throw "Controlled local geographic operation failed: $($stage.File) (exit $exitCode)." }
    }
    return (Get-FileHash -LiteralPath $packet -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Apply-LocalOwnerMigration($MigrationInfo) {
    $migration14 = Join-Path $LocalSql '014_local_owner_login.sql'
    if (-not (Test-Path -LiteralPath $migration14)) { throw 'Migration 014 for local owner login is missing.' }
    $hash14 = (Get-FileHash -LiteralPath $migration14 -Algorithm SHA256).Hash.ToLowerInvariant()
    $hash13 = (Get-FileHash -LiteralPath (Join-Path $LocalSql '013_private_pilot_geo_audit.sql') -Algorithm SHA256).Hash.ToLowerInvariant()
    $wrapper = "\set ON_ERROR_STOP on`n\set migration_hash $hash14`nSET ROLE rahgard_pilot_geo_migrator;`n\i /opt/rahgard/pilot-sql/014_local_owner_login.sql`nRESET ROLE;`n"
    $dockerArgs = @('-e',('RAHGARD_PILOT_DATABASE_MARKER=' + $MigrationInfo.marker),
                    '-e',('RAHGARD_PILOT_MIGRATION_0013_SHA256=' + $hash13))
    Invoke-LocalPilotDockerSql @'
GRANT USAGE, CREATE ON SCHEMA identity TO rahgard_pilot_geo_migrator;
GRANT REFERENCES(user_id) ON identity.users TO rahgard_pilot_geo_migrator;
GRANT SELECT ON knowledge.production_destinations TO rahgard_pilot_geo_migrator;
'@ -Database $Paths.Database
    Invoke-LocalPilotGuardedTcpSql $wrapper -Database $Paths.Database -DockerArgs $dockerArgs
    Invoke-LocalPilotDockerSql @'
REVOKE SELECT ON knowledge.production_destinations FROM rahgard_pilot_geo_migrator;
REVOKE REFERENCES(user_id) ON identity.users FROM rahgard_pilot_geo_migrator;
REVOKE CREATE ON SCHEMA identity FROM rahgard_pilot_geo_migrator;
'@ -Database $Paths.Database

    $bootstrapPassword = New-LocalPilotRandomHex 32
    Save-LocalPilotSecret $Paths.OwnerBootstrapPassword $bootstrapPassword
    $bootstrapSetup = @"
CREATE ROLE rahgard_pilot_owner_bootstrap LOGIN PASSWORD '$bootstrapPassword' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT CONNECT ON DATABASE $($Paths.Database) TO rahgard_pilot_owner_bootstrap;
GRANT USAGE ON SCHEMA identity,system,public TO rahgard_pilot_owner_bootstrap;
GRANT SELECT ON system.schema_migrations,public.rahgard_private_pilot_marker TO rahgard_pilot_owner_bootstrap;
GRANT SELECT(user_id) ON identity.users TO rahgard_pilot_owner_bootstrap;
GRANT INSERT(user_id,auth_subject,display_name) ON identity.users TO rahgard_pilot_owner_bootstrap;
GRANT INSERT ON identity.local_owner_credentials TO rahgard_pilot_owner_bootstrap;
GRANT SELECT(owner_id,login_name) ON identity.local_owner_credentials TO rahgard_pilot_owner_bootstrap;
GRANT UPDATE(salt,verifier,iterations) ON identity.local_owner_credentials TO rahgard_pilot_owner_bootstrap;
GRANT SELECT(user_id,revoked_at) ON identity.web_sessions TO rahgard_pilot_owner_bootstrap;
GRANT UPDATE(revoked_at,revoked_reason) ON identity.web_sessions TO rahgard_pilot_owner_bootstrap;
"@
    Invoke-LocalPilotDockerSql $bootstrapSetup -Database $Paths.Database
    $verify = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database `
        -c "SELECT (SELECT count(*) FROM identity.local_owner_credentials)=0 AND (SELECT sha256 FROM system.schema_migrations WHERE migration_id='0014_local_owner_login')='$hash14'"
    if ($LASTEXITCODE -ne 0 -or ($verify | Out-String).Trim() -ne 't') { throw 'Local owner schema migration or initial empty-owner state did not verify.' }
    return $hash14
}

function Get-LocalPilotStateOrFail {
    $state = Read-LocalPilotState $Paths
    if (-not $state) { throw 'No initialized local-pilot state exists. Use Start -InitializeDatabase -ConfirmPrivatePilot first.' }
    return $state
}

function Assert-LocalPilotBaseMigrationCheckpoint {
    $expected = @()
    $legacyHash = (Get-FileHash -LiteralPath $LegacySql -Algorithm SHA256).Hash.ToLowerInvariant()
    $expected += "0000_legacy_tourism_points_baseline|$legacyHash"
    $files = @(
        '0001_core_schema|001_core_schema.sql','0002_synthetic_knowledge_seed|002_synthetic_knowledge_seed.sql',
        '0003_synthetic_e2e_seed|003_synthetic_e2e_seed.sql','0004_app_role_grants|004_app_role_grants.sql',
        '0005_verified_unesco_destination_seed|005_verified_unesco_destination_seed.sql',
        '0006_verified_unesco_destination_seed_batch2|006_verified_unesco_destination_seed_batch2.sql',
        '0007_shiraz_dalahoo_wikipedia_dataset_v1|007_shiraz_dalahoo_wikipedia_dataset_v1.sql',
        '0008_authentication_foundation|008_authentication_foundation.sql','0009_traveler_core|009_traveler_core.sql',
        '0010_task31_content_privacy_full_itinerary|010_task31_content_privacy_full_itinerary.sql',
        '0011_internal_chat_turns|011_internal_chat_turns.sql','0012_task5_published_claim_evidence|012_task5_published_claim_evidence.sql'
    )
    foreach ($entry in $files) {
        $parts = $entry.Split('|')
        $path = Join-Path $SqlDir $parts[1]
        if (-not (Test-Path -LiteralPath $path)) { throw 'A required base migration is missing during recovery validation.' }
        $expected += "$($parts[0])|$((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant())"
    }
    $expected = @($expected | Sort-Object)
    $actual = @(& docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database `
        -c 'SELECT migration_id||''|''||sha256 FROM system.schema_migrations ORDER BY migration_id' 2>$null |
        ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ })
    $geoHash = (Get-FileHash -LiteralPath (Join-Path $LocalSql '013_private_pilot_geo_audit.sql') -Algorithm SHA256).Hash.ToLowerInvariant()
    $ownerHash = (Get-FileHash -LiteralPath (Join-Path $LocalSql '014_local_owner_login.sql') -Algorithm SHA256).Hash.ToLowerInvariant()
    $geoApplied = $false
    $ownerApplied = $false
    if ($actual.Count -ge 14) { $expected += "0013_private_pilot_geo_audit|$geoHash"; $expected = @($expected | Sort-Object); $geoApplied = $true }
    if ($actual.Count -eq 15) { $expected += "0014_local_owner_login|$ownerHash"; $expected = @($expected | Sort-Object); $ownerApplied = $true }
    if ($LASTEXITCODE -ne 0 -or $actual.Count -notin @(13,14,15) -or ($actual -join "`n") -ne ($expected -join "`n")) {
        throw 'Interrupted database migration ledger is not an exact reviewed 0000–0012, 0000–0013, or 0000–0014 checkpoint.'
    }
    $marker = Get-LocalPilotMarker
    $phaseSql = if ($ownerApplied) {
@'
SELECT CASE WHEN to_regclass('operations.private_pilot_geo_authorizations') IS NOT NULL
 AND (SELECT count(*) FROM operations.private_pilot_geo_authorizations) IN (0,4)
 AND (SELECT count(DISTINCT destination_key) FROM operations.private_pilot_geo_authorizations)=
     (SELECT count(*) FROM operations.private_pilot_geo_authorizations)
 AND to_regclass('operations.private_pilot_geo_approvals') IS NOT NULL
 AND (SELECT count(*) FROM operations.private_pilot_geo_approvals) IN (0,4)
 AND (SELECT count(DISTINCT destination_key) FROM operations.private_pilot_geo_approvals)=
     (SELECT count(*) FROM operations.private_pilot_geo_approvals)
 AND to_regclass('identity.local_owner_credentials') IS NOT NULL
 AND NOT EXISTS (SELECT 1 FROM identity.local_owner_credentials)
 THEN 'owner_migration_only' ELSE 'later_state' END
'@
    } elseif ($geoApplied) {
@'
SELECT CASE WHEN to_regclass('operations.private_pilot_geo_authorizations') IS NOT NULL
 AND (SELECT count(*) FROM operations.private_pilot_geo_authorizations) IN (0,4)
 AND (SELECT count(DISTINCT destination_key) FROM operations.private_pilot_geo_authorizations)=
     (SELECT count(*) FROM operations.private_pilot_geo_authorizations)
 AND to_regclass('operations.private_pilot_geo_approvals') IS NOT NULL
 AND NOT EXISTS (SELECT 1 FROM operations.private_pilot_geo_approvals)
 AND NOT EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0014_local_owner_login')
 AND to_regclass('identity.local_owner_credentials') IS NULL
 THEN 'geo_migration_only' ELSE 'later_state' END
'@
    } else {
@'
SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id IN ('0013_private_pilot_geo_audit','0014_local_owner_login'))
 AND to_regclass('operations.private_pilot_geo_authorizations') IS NULL
 AND to_regclass('identity.local_owner_credentials') IS NULL
 THEN 'base_only' ELSE 'later_state' END
'@
    }
    $phase = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database -c $phaseSql 2>$null
    $expectedPhase = if ($ownerApplied) { 'owner_migration_only' } elseif ($geoApplied) { 'geo_migration_only' } else { 'base_only' }
    if ($LASTEXITCODE -ne 0 -or ($phase | Out-String).Trim() -ne $expectedPhase) {
        throw 'Interrupted database contains a later publication/auth stage; preserving it for manual review.'
    }
    return [pscustomobject]@{
        marker=$marker
        geo_migration_applied=$geoApplied
        owner_migration_applied=$ownerApplied
        migration_0014_hash=$ownerHash
        migration_0012_hash=(Get-FileHash -LiteralPath (Join-Path $SqlDir '012_task5_published_claim_evidence.sql') -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}

function Test-LocalPilotPortAvailable([int]$Port) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try { $listener.Start(); return $true } catch { return $false }
    finally { try { $listener.Stop() } catch {} }
}

function Wait-LocalPilotHttp([string]$Url, [int]$TimeoutSeconds = 60) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 15 -UseBasicParsing
            if ($response.StatusCode -eq 200) { return }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    throw 'Local pilot readiness endpoint did not become healthy before timeout.'
}

function New-LocalPilotCertificate {
    if ((Test-Path -LiteralPath $Paths.Pfx) -and (Test-Path -LiteralPath $Paths.PfxPassword) -and
        (Test-Path -LiteralPath $Paths.PfxCertificate)) {
        $existingCertificate = [Security.Cryptography.X509Certificates.X509Certificate2]::new([IO.File]::ReadAllBytes($Paths.PfxCertificate))
        try { return (Assert-LocalPilotHttpsCertificate $existingCertificate.Thumbprint) }
        finally { $existingCertificate.Dispose() }
    }
    if ((Test-Path -LiteralPath $Paths.Pfx) -or (Test-Path -LiteralPath $Paths.PfxPassword) -or
        (Test-Path -LiteralPath $Paths.PfxCertificate)) {
        throw 'Partial localhost certificate files exist; refusing replacement.'
    }
    $password = New-LocalPilotRandomHex 32
    $secure = ConvertTo-SecureString $password -AsPlainText -Force
    $certificate = New-SelfSignedCertificate -DnsName 'localhost' -CertStoreLocation 'Cert:\CurrentUser\My' `
        -KeyAlgorithm RSA -KeyLength 3072 -KeyExportPolicy Exportable -KeyUsage DigitalSignature,KeyEncipherment `
        -NotAfter ([datetime]::UtcNow.AddYears(2)) -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.1')
    try {
        Export-PfxCertificate -Cert $certificate -FilePath $Paths.Pfx -Password $secure -Force | Out-Null
        Export-Certificate -Cert $certificate -FilePath $Paths.PfxCertificate -Type CERT -Force | Out-Null
        Save-LocalPilotSecret $Paths.PfxPassword $password
        Set-LocalPilotAcl $Paths.Pfx
        Set-LocalPilotAcl $Paths.PfxCertificate
    } catch {
        Remove-Item -LiteralPath $Paths.Pfx,$Paths.PfxCertificate -Force -ErrorAction SilentlyContinue
        throw
    } finally {
        # The proxy loads the private key from the ACL-protected PFX. Keep no
        # second exportable copy in the user's general-purpose personal store.
        $createdCertificate = Join-Path 'Cert:\CurrentUser\My' $certificate.Thumbprint
        if (Test-Path -LiteralPath $createdCertificate) {
            Remove-Item -LiteralPath $createdCertificate -Force -ErrorAction Stop
        }
    }
    return $certificate.Thumbprint
}

function Install-LocalPilotBackupRole {
    $statusQuery = "SELECT CASE WHEN EXISTS(SELECT 1 FROM pg_roles WHERE rolname='ai_tourism_backup' AND rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolbypassrls) THEN 'ok' ELSE 'bad' END"
    if (Test-Path -LiteralPath $Paths.BackupPassword) {
        $password = Read-LocalPilotSecret $Paths.BackupPassword
        $result = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d postgres -c $statusQuery
        if ($LASTEXITCODE -ne 0 -or ($result | Out-String).Trim() -ne 'ok') { throw 'Existing backup role does not match the protected local-pilot contract.' }
    } else {
        $password = New-LocalPilotRandomHex 32
        Save-LocalPilotSecret $Paths.BackupPassword $password
        $create = "CREATE ROLE ai_tourism_backup LOGIN PASSWORD '$password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; GRANT CONNECT ON DATABASE $($Paths.Database) TO ai_tourism_backup;"
        Invoke-LocalPilotDockerSql $create -Database 'postgres'
    }
    $membership = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d postgres `
        -c "SELECT pg_has_role('ai_tourism_backup','pg_read_all_data','MEMBER')"
    if ($LASTEXITCODE -ne 0) { throw "Could not verify backup role's global data privileges." }
    if (($membership | Out-String).Trim() -eq 't') {
        Invoke-LocalPilotDockerSql 'REVOKE pg_read_all_data FROM ai_tourism_backup' -Database 'postgres'
    }
    $schemas = 'identity,knowledge,travel,conversation,recommendation,integration,operations,public,system,tiger,topology'
    $scopedGrants = "GRANT CONNECT ON DATABASE $($Paths.Database) TO ai_tourism_backup; GRANT USAGE ON SCHEMA $schemas TO ai_tourism_backup; GRANT SELECT ON ALL TABLES IN SCHEMA $schemas TO ai_tourism_backup; GRANT SELECT ON ALL SEQUENCES IN SCHEMA $schemas TO ai_tourism_backup;"
    Invoke-LocalPilotDockerSql $scopedGrants -Database $Paths.Database
    $verified = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d postgres `
        -c "SELECT CASE WHEN NOT pg_has_role('ai_tourism_backup','pg_read_all_data','MEMBER') AND EXISTS(SELECT 1 FROM pg_roles WHERE rolname='ai_tourism_backup' AND rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolbypassrls) THEN 'ok' ELSE 'bad' END"
    if ($LASTEXITCODE -ne 0 -or ($verified | Out-String).Trim() -ne 'ok') { throw 'Backup role retained broad privileges or failed its scoped read-only check.' }
}

function Start-LocalPilotWebProcesses($State) {
    $node = Get-Command node -ErrorAction Stop
    $pythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Repository-local Python environment is missing; refusing a global interpreter.' }
    if (-not (Test-LocalPilotPortAvailable ([int]$State.api_port)) -or
        -not (Test-LocalPilotPortAvailable ([int]$State.https_port))) { throw 'Recorded local API/HTTPS port is occupied by an unowned listener.' }
    $providerAdminEnabled = [int]$State.migration_count -eq 16
    $providerVault = Join-Path $Paths.Secrets 'ai-provider-vault'
    if ($providerAdminEnabled) {
        if (-not (Test-Path -LiteralPath $providerVault)) {
            New-Item -ItemType Directory -Path $providerVault | Out-Null
            Set-LocalPilotAcl $providerVault -Directory
        } else { Assert-LocalPilotAcl $providerVault -Directory -Protected }
    }
    $nodeExe = $node.Source
    $apiEnv = @{
        APP_ENV='local_pilot'; APP_HOST='127.0.0.1'; APP_PORT=[string]$State.api_port; LOG_LEVEL='INFO'
        DATABASE_HOST='localhost'; DATABASE_PORT=[string]$State.database_port; DATABASE_NAME=$Paths.Database
        DATABASE_USER='ai_tourism_app'; DATABASE_PASSWORD=(Read-LocalPilotSecret $Paths.AppPassword)
        DATABASE_CONNECT_TIMEOUT_SECONDS='3'; PGSSLMODE='verify-full'; PGSSLROOTCERT=$Paths.DatabaseCertificate
        AUTH_ENABLED='true'; AUTH_LOCAL_OWNER_ENABLED='true'; AUTH_SMS_ADAPTER='disabled'
        AUTH_COOKIE_SECURE='true'; AUTH_ALLOWED_ORIGINS="https://localhost:$($State.https_port)"
        AUTH_SESSION_IDLE_SECONDS='1800'; AUTH_SESSION_ABSOLUTE_SECONDS='28800'
        AUTH_OTP_HMAC_SECRET=(Read-LocalPilotSecret $Paths.AppHmac)
        AUTH_CSRF_SECRET=(Read-LocalPilotSecret $Paths.AppCsrf)
        AUTH_RATE_LIMIT_SECRET=(Read-LocalPilotSecret $Paths.AppRate)
        AI_PROVIDER_ADMIN_ENABLED=($providerAdminEnabled.ToString().ToLowerInvariant())
        AI_PROVIDER_VAULT_DIR=$providerVault
        AI_PROVIDER_ADMIN_RECOVERY_PEPPER=(Read-LocalPilotSecret $Paths.AppHmac)
        TOURISM_RAG_ENABLED='false'; INTERNAL_CHAT_ENABLED='false'
        PYTHONUTF8='1'; PYTHONDONTWRITEBYTECODE='1'
    }
    $api = Start-LocalPilotBackgroundProcess -File $pythonExe -Arguments @('-m','uvicorn','app.main:app','--host','127.0.0.1',
        '--port',[string]$State.api_port,'--no-access-log') `
        -WorkingDirectory $BackendRoot -Environment $apiEnv -Stdout (Join-Path $Paths.Logs 'api.log') `
        -Stderr (Join-Path $Paths.Logs 'api-error.log')
    $State.api_process = @{ pid=$api.Id; started_utc=$api.StartTime.ToUniversalTime().ToString('o'); executable=$pythonExe }
    $nodeEnv = @{
        PILOT_HTTPS_PORT=[string]$State.https_port; PILOT_API_PORT=[string]$State.api_port
        PILOT_FRONTEND_DIST=(Join-Path $FrontendRoot 'dist'); PILOT_TLS_PFX=$Paths.Pfx
        PILOT_TLS_PFX_PASSWORD=(Read-LocalPilotSecret $Paths.PfxPassword)
    }
    $proxy = Start-LocalPilotBackgroundProcess -File $nodeExe -Arguments @((Join-Path $ProjectRoot 'engineering\pilot\local_https_proxy.mjs')) `
        -WorkingDirectory $ProjectRoot -Environment $nodeEnv -Stdout (Join-Path $Paths.Logs 'https-proxy.log') `
        -Stderr (Join-Path $Paths.Logs 'https-proxy-error.log')
    $State.proxy_process = @{ pid=$proxy.Id; started_utc=$proxy.StartTime.ToUniversalTime().ToString('o'); executable=$nodeExe }
    Write-LocalPilotState $Paths $State
    Wait-LocalPilotHttp "http://127.0.0.1:$($State.api_port)/health/ready" 90
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    while ([DateTime]::UtcNow -lt $deadline) {
        $listener = @(Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1 -LocalPort ([int]$State.https_port) -ErrorAction SilentlyContinue)
        $proxyLog = Join-Path $Paths.Logs 'https-proxy.log'
        if ($listener.Count -gt 0 -and (Test-Path -LiteralPath $proxyLog) -and
            (Get-Content -LiteralPath $proxyLog -Raw -ErrorAction SilentlyContinue).Contains("LOOPBACK_HTTPS_READY:$($State.https_port)")) { return }
        Start-Sleep -Milliseconds 500
    }
    throw 'Private HTTPS listener did not become ready; inspect ACL-protected proxy logs.'
}

function Stop-LocalPilotManagedProcess($ProcessState, [string]$Kind, $State) {
    if (-not $ProcessState -or -not $ProcessState.pid) { return }
    $process = Get-Process -Id ([int]$ProcessState.pid) -ErrorAction SilentlyContinue
    if (-not $process) { return }
    $start = [DateTime]::Parse([string]$ProcessState.started_utc).ToUniversalTime()
    if ([Math]::Abs(($process.StartTime.ToUniversalTime() - $start).TotalSeconds) -gt 2) {
        throw "Refusing to stop a process whose PID identity changed ($Kind)."
    }
    $cim = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$ProcessState.pid)" -ErrorAction Stop
    $command = [string]$cim.CommandLine
    if ([string]::IsNullOrWhiteSpace($command)) {
        # Some Windows process providers omit CommandLine/ExecutablePath for a
        # same-user process even when PID, start time and its owned loopback
        # socket remain observable. In that case require all three identity
        # anchors instead of weakening the check to PID alone.
        $owner = Invoke-CimMethod -InputObject $cim -MethodName GetOwner -ErrorAction Stop
        $currentOwner = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        if (-not $owner.User -or "$($owner.Domain)\$($owner.User)" -cne $currentOwner -or
            [IO.Path]::GetFileName([string]$ProcessState.executable) -ine $(if ($Kind -eq 'api') {'python.exe'} else {'node.exe'})) {
            throw "Refusing to stop a process with incomplete Windows identity metadata ($Kind)."
        }
        $port = if ($Kind -eq 'api') { [int]$State.api_port } else { [int]$State.https_port }
        $listeners = @(Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1 -LocalPort $port -ErrorAction SilentlyContinue |
            Where-Object { [int]$_.OwningProcess -eq [int]$ProcessState.pid })
        if ($listeners.Count -ne 1) { throw "Refusing to stop a process whose recorded loopback listener cannot be verified ($Kind)." }
    }
    if ($Kind -eq 'api') {
        $invalidApiCommand = $command -and ($command -notmatch 'python(\.exe)?' -or $command -notmatch 'app\.main:app' -or
            $command -notmatch "--port\s+$([int]$State.api_port)" -or $command -notmatch '127\.0\.0\.1')
        if ($invalidApiCommand) {
            throw 'Refusing to stop a process that no longer matches the recorded API identity.'
        }
    } else {
        $proxyScript = [regex]::Escape((Join-Path $ProjectRoot 'engineering\pilot\local_https_proxy.mjs'))
        $listener = @(Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1 -LocalPort ([int]$State.https_port) -ErrorAction SilentlyContinue)
        if (($command -and ($command -notmatch 'node(\.exe)?' -or $command -notmatch $proxyScript)) -or
            -not ($listener | Where-Object { [int]$_.OwningProcess -eq [int]$ProcessState.pid })) {
            throw 'Refusing to stop a process that no longer matches the recorded HTTPS proxy identity.'
        }
    }
    Stop-Process -Id $process.Id -ErrorAction Stop
    try { $process.WaitForExit(10000) | Out-Null } catch {}
}

function Get-LocalPilotRuntimeStatus($State) {
    $container = Get-LocalPilotContainer $Paths
    $dbStatus = if ($container) { [string]$container.State.Status } else { 'missing' }
    $apiStatus = 'stopped'; $httpsStatus = 'stopped'; $certificateTrusted = $false
    $listeners = @(Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1 -LocalPort ([int]$State.https_port) -ErrorAction SilentlyContinue)
    if ($listeners.Count) { $httpsStatus = 'listening_loopback' }
    if ($State.https_thumbprint) {
        $certificateTrusted = [bool](Get-ChildItem Cert:\CurrentUser\Root -ErrorAction SilentlyContinue |
            Where-Object { $_.Thumbprint -eq $State.https_thumbprint })
    }
    try { $null = Invoke-WebRequest -Uri "http://127.0.0.1:$($State.api_port)/health/ready" -TimeoutSec 15 -UseBasicParsing; $apiStatus = 'ready' } catch {}
    [pscustomobject]@{
        deployment='persistent-private-local'; data_root=$Paths.Root; database=$Paths.Database
        database_port=$State.database_port; container=$Paths.Container; database_status=$dbStatus
        api_port=$State.api_port; api_status=$apiStatus; https_port=$State.https_port; https_status=$httpsStatus
        https_certificate_trusted_by_current_user=$certificateTrusted
        migration_count=$State.migration_count; migration_0015_sha256=$State.migration_0015_sha256
        geo_packet_sha256=$State.geo_packet_sha256
        map_point_notice='Representative coordinates are approximate map points, not verified entrances.'
        live_chat=$false; rag=$false
    }
}

function Get-LocalPilotConfigDigest {
    $inputs = @(
        (Join-Path $BackendRoot 'app'), (Join-Path $FrontendRoot 'src'), (Join-Path $FrontendRoot 'public'),
        $SqlDir, $LocalSql,
        (Join-Path $ProjectRoot 'engineering\pilot\local_https_proxy.mjs'),
        (Join-Path $ProjectRoot 'engineering\pilot\persistent_backup.py'),
        (Join-Path $ProjectRoot 'engineering\pilot\persistent_restore_rehearsal.py'),
        (Join-Path $ProjectRoot 'engineering\pilot\local-persistent\check_postgres_tls.py'),
        (Join-Path $BackendRoot 'scripts\bootstrap_local_owner.py'),
        (Join-Path $BackendRoot 'scripts\rahgard_sign_pilot_geo_authorization.py'),
        (Join-Path $BackendRoot 'scripts\rahgard_private_geo_authorize.py'),
        (Join-Path $BackendRoot 'scripts\rahgard_private_geo_publication.py'),
        (Join-Path $BackendRoot 'scripts\rahgard_geo_visibility.py'),
        (Join-Path $ProjectRoot 'database\tourism_points.sql'),
        (Join-Path $ProjectRoot 'pyproject.toml'),
        (Join-Path $ProjectRoot 'engineering\pilot\local-persistent\Rahgard-LocalPilot.ps1'),
        (Join-Path $ProjectRoot 'engineering\pilot\local-persistent\Rahgard.LocalPilot.psm1'),
        (Join-Path $ProjectRoot 'frontend\package-lock.json'),
        (Join-Path $ProjectRoot 'frontend\package.json'),
        (Join-Path $ProjectRoot 'uv.lock')
    )
    $rows = New-Object System.Collections.Generic.List[string]
    foreach ($entryPath in $inputs) {
        if (-not (Test-Path -LiteralPath $entryPath)) { throw "Configuration input is missing: $entryPath" }
        $item = Get-Item -LiteralPath $entryPath -Force
        $files = if ($item.PSIsContainer) { Get-ChildItem -LiteralPath $entryPath -Recurse -File | Where-Object { $_.FullName -notmatch '\\(__pycache__|node_modules|dist)\\' -and $_.Extension -ne '.pyc' } } else { @($item) }
        foreach ($file in $files) {
            $relative = $file.FullName.Substring($ProjectRoot.Length).TrimStart('\').Replace('\','/')
            $digest = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            $rows.Add("$relative=$digest")
        }
    }
    $canonical = (($rows | Sort-Object) -join "`n")
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($canonical))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}

function Get-LocalPilotBuildDigest {
    $dist = Join-Path $FrontendRoot 'dist'
    if (-not (Test-Path -LiteralPath (Join-Path $dist 'index.html'))) { throw 'PWA production build output is missing.' }
    $rows = @(Get-ChildItem -LiteralPath $dist -Recurse -File | ForEach-Object {
        $relative = $_.FullName.Substring($dist.Length).TrimStart('\').Replace('\','/')
        "$relative=$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant())"
    } | Sort-Object)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes(($rows -join "`n")))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}

function Assert-LocalPilotHttpsCertificate([string]$ExpectedThumbprint) {
    foreach ($file in @($Paths.Pfx,$Paths.PfxPassword,$Paths.PfxCertificate)) {
        if (-not (Test-Path -LiteralPath $file)) { throw 'Complete localhost HTTPS certificate material is required.' }
        Assert-LocalPilotAcl $file
    }
    $public = [Security.Cryptography.X509Certificates.X509Certificate2]::new([IO.File]::ReadAllBytes($Paths.PfxCertificate))
    $pfxPassword = Read-LocalPilotSecret $Paths.PfxPassword
    $private = [Security.Cryptography.X509Certificates.X509Certificate2]::new($Paths.Pfx,$pfxPassword,
        [Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable)
    try {
        $san = [string]($public.Extensions | Where-Object { $_.Oid.Value -eq '2.5.29.17' } | ForEach-Object { $_.Format($false) })
        $eku = [string]($public.Extensions | Where-Object { $_.Oid.Value -eq '2.5.29.37' } | ForEach-Object { $_.Format($false) })
        if ($public.Thumbprint -ne $ExpectedThumbprint -or $private.Thumbprint -ne $ExpectedThumbprint -or
            -not $private.HasPrivateKey -or $public.NotAfter.ToUniversalTime() -le [DateTime]::UtcNow -or
            $san -notmatch 'localhost' -or $eku -notmatch '1\.3\.6\.1\.5\.5\.7\.3\.1') {
            throw 'Local HTTPS certificate does not match the recorded private key, localhost SAN, or server-auth EKU.'
        }
        return $public.Thumbprint
    } finally { $public.Dispose(); $private.Dispose() }
}

function Start-LocalPilot {
    if (-not $ConfirmPrivatePilot) { throw 'Start requires -ConfirmPrivatePilot. This creates a persistent private local database.' }
    if (-not (Test-Path -LiteralPath (Join-Path $BackendRoot 'app\main.py')) -or
        -not (Test-Path -LiteralPath (Join-Path $FrontendRoot 'package.json'))) { throw 'Repository application inputs are missing.' }
    if (Test-Path -LiteralPath (Join-Path $BackendRoot '.env')) {
        throw 'Refusing to start because backend/.env exists; this runtime never reads dotenv files.'
    }
    Initialize-LocalPilotRoot $Paths
    $state = Read-LocalPilotState $Paths
    $initializeNow = $false
    if (-not $state) {
        if (-not $InitializeDatabase) { throw 'First start requires -InitializeDatabase; it creates a new isolated persistent database.' }
        if (-not $PublishApprovedGeo) { throw 'First database initialization requires explicit -PublishApprovedGeo for the owner-approved four-POI packet.' }
        if (-not (Test-LocalPilotPortAvailable $DatabasePort) -or
            -not (Test-LocalPilotPortAvailable $ApiPort) -or
            -not (Test-LocalPilotPortAvailable $HttpsPort)) { throw 'A configured loopback pilot port is already occupied; no resource was changed.' }
        $imageId = Assert-LocalPilotTools $Paths
        if ((Test-Path -LiteralPath $Paths.OwnerPassword) -or (Test-Path -LiteralPath $Paths.AppPassword)) {
            throw 'Untracked credential material exists without an initialized state; refusing to reuse it.'
        }
        $ownerPassword = New-LocalPilotRandomHex 40
        $appPassword = New-LocalPilotRandomHex 40
        [IO.File]::WriteAllText($Paths.OwnerPassword, $ownerPassword, [Text.Encoding]::ASCII)
        Set-LocalPilotAcl $Paths.OwnerPassword
        Save-LocalPilotSecret $Paths.AppPassword $appPassword
        Save-LocalPilotSecret $Paths.AppHmac (New-LocalPilotRandomHex 32)
        Save-LocalPilotSecret $Paths.AppCsrf (New-LocalPilotRandomHex 32)
        Save-LocalPilotSecret $Paths.AppRate (New-LocalPilotRandomHex 32)
        $state = [ordered]@{
            schema='rahgard.local-pilot.v1'; lifecycle='initializing'; data_root=$Paths.Root; root_sha256=$Paths.RootHash
            container_name=$Paths.Container; container_image=$Paths.Image; container_image_id=$imageId
            bind_mount=$Paths.Db; database=$Paths.Database; database_port=$DatabasePort
            api_port=$ApiPort; https_port=$HttpsPort; marker=$null; migration_count=0
            created_utc=[DateTime]::UtcNow.ToString('o'); api_process=$null; proxy_process=$null; restore_candidates=@()
        }
        Write-LocalPilotState $Paths $state
        $initializeNow = $true
    } elseif ($state.lifecycle -eq 'initializing') {
        if (-not $ResumeInitialization -or -not $InitializeDatabase -or -not $PublishApprovedGeo) {
            throw 'Interrupted setup is preserved. Resume only with -ResumeInitialization -InitializeDatabase -PublishApprovedGeo after reviewing the exact local data root.'
        }
        if ($state.schema -ne 'rahgard.local-pilot.v1' -or $state.container_name -ne $Paths.Container -or
            $state.container_image -ne $Paths.Image -or $state.database -ne $Paths.Database -or
            $state.bind_mount -ne $Paths.Db -or [int]$state.migration_count -ne 0 -or $state.marker) {
            throw 'Interrupted setup state is not a pristine supported initialization checkpoint.'
        }
        $imageId = Assert-LocalPilotTools $Paths
        if ($state.container_image_id -ne $imageId) { throw 'Installed image identity differs from the preserved setup checkpoint.' }
        $existingContainer = Get-LocalPilotContainer $Paths
        $reuseContainer = $false
        if ($existingContainer) {
            if ($existingContainer.State.Status -ne 'running') { throw 'Interrupted pilot container is not running; preserving it for manual review.' }
            $migrationInfo = Assert-LocalPilotBaseMigrationCheckpoint
            $roleState = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database -c @'
SELECT CASE WHEN count(*)=4 AND bool_and(NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolbypassrls)
 AND bool_and(rolcanlogin = (rolname IN ('rahgard_pilot_geo_authorizer','rahgard_pilot_geo_publisher')))
 AND pg_has_role('rahgard_pilot_geo_migrator','rahgard_pilot_geo_executor','MEMBER') THEN 'setup_ready'
 WHEN count(*)=4 AND bool_and(NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolbypassrls)
 AND bool_and(rolcanlogin = (rolname IN ('rahgard_pilot_geo_authorizer','rahgard_pilot_geo_publisher')))
 AND NOT pg_has_role('rahgard_pilot_geo_migrator','rahgard_pilot_geo_executor','MEMBER') THEN 'migration_complete'
 ELSE 'role_conflict' END
FROM pg_catalog.pg_roles WHERE rolname IN ('rahgard_pilot_geo_executor','rahgard_pilot_geo_migrator','rahgard_pilot_geo_authorizer','rahgard_pilot_geo_publisher')
'@ 2>$null
            $expectedRoleState = if ($migrationInfo.geo_migration_applied) { 'migration_complete' } else { 'setup_ready' }
            if ($LASTEXITCODE -ne 0 -or ($roleState | Out-String).Trim() -ne $expectedRoleState) {
                throw 'Interrupted database role setup is not the exact safe pre-publication state.'
            }
            $reuseContainer = $true
        } elseif (@(Get-ChildItem -LiteralPath $Paths.Db -Force).Count -ne 0) {
            throw 'The persistent database directory is nonempty without the recorded container; preserving it for manual review.'
        }
        $expectedSecrets = if ($existingContainer -and $migrationInfo.geo_migration_applied) {
            @('postgres-owner-password','app-password.dpapi','auth-hmac.dpapi','auth-csrf.dpapi','auth-rate.dpapi',
              'geo-authorizer-password.dpapi','geo-migrator-password.dpapi','geo-publisher-password.dpapi',
              'geo-owner-authorization-key.dpapi','postgres-root.crt')
        } elseif ($existingContainer) {
            @('postgres-owner-password','app-password.dpapi','auth-hmac.dpapi','auth-csrf.dpapi','auth-rate.dpapi',
              'geo-authorizer-password.dpapi','geo-migrator-password.dpapi','geo-publisher-password.dpapi') | Sort-Object
        } else {
            @('postgres-owner-password','app-password.dpapi','auth-hmac.dpapi','auth-csrf.dpapi','auth-rate.dpapi') | Sort-Object
        }
        if ($existingContainer -and $migrationInfo.owner_migration_applied) {
            $expectedSecrets += @('owner-bootstrap-password.dpapi','backup-password.dpapi')
        }
        $httpsArtifacts = @(
            [bool](Test-Path -LiteralPath $Paths.Pfx),
            [bool](Test-Path -LiteralPath $Paths.PfxPassword),
            [bool](Test-Path -LiteralPath $Paths.PfxCertificate)
        )
        if (@($httpsArtifacts | Where-Object { $_ }).Count -notin @(0,3)) {
            throw 'Interrupted setup contains only part of its generated HTTPS certificate set; preserving it for manual review.'
        }
        if ($httpsArtifacts[0]) { $expectedSecrets += @('localhost.pfx','localhost-pfx-password.dpapi','localhost.cer') }
        $actualSecrets = @(Get-ChildItem -LiteralPath $Paths.Secrets -Force | ForEach-Object Name | Sort-Object)
        $authorizationFiles = @($actualSecrets | Where-Object { $_ -match '^geo-target-authorization(?:-[a-f0-9]{32})?\.json$' })
        $actualNonAuthorization = @($actualSecrets | Where-Object { $_ -notin $authorizationFiles } | Sort-Object)
        if (($actualNonAuthorization -join '|') -ne (@($expectedSecrets | Sort-Object) -join '|') -or
            ($existingContainer -and $migrationInfo.geo_migration_applied -and -not $authorizationFiles.Count) -or
            ($existingContainer -and -not $migrationInfo.geo_migration_applied -and $authorizationFiles.Count)) {
            throw 'Interrupted setup secret inventory differs from the initial checkpoint; preserving it for manual review.'
        }
        foreach ($file in @($Paths.OwnerPassword,$Paths.AppPassword,$Paths.AppHmac,$Paths.AppCsrf,$Paths.AppRate)) { Assert-LocalPilotAcl $file }
        if ((Get-Content -LiteralPath $Paths.OwnerPassword -Raw -Encoding ASCII) -notmatch '^[a-f0-9]{80}$') {
            throw 'Preserved database bootstrap credential does not match the expected generated format.'
        }
        foreach ($secret in @($Paths.AppPassword,$Paths.AppHmac,$Paths.AppCsrf,$Paths.AppRate)) { $null = Read-LocalPilotSecret $secret }
        foreach ($authorizationFile in $authorizationFiles) {
            $authorizationPath = Join-Path $Paths.Secrets $authorizationFile
            $authorizationAcl = Get-Acl -LiteralPath $authorizationPath
            if (-not $authorizationAcl.AreAccessRulesProtected) { Set-LocalPilotAcl $authorizationPath }
            else { Assert-LocalPilotAcl $authorizationPath }
        }
        if ($httpsArtifacts[0]) {
            foreach ($file in @($Paths.Pfx,$Paths.PfxPassword,$Paths.PfxCertificate)) { Assert-LocalPilotAcl $file }
            $publicCert = [Security.Cryptography.X509Certificates.X509Certificate2]::new([IO.File]::ReadAllBytes($Paths.PfxCertificate))
            try { $null = Assert-LocalPilotHttpsCertificate $publicCert.Thumbprint }
            finally { $publicCert.Dispose() }
        }
        if ($existingContainer -and $migrationInfo.geo_migration_applied) {
            if (-not (Test-Path -LiteralPath $Paths.DatabaseCertificate)) { throw 'PostgreSQL TLS checkpoint is incomplete; preserving it for manual review.' }
            Assert-LocalPilotAcl $Paths.DatabaseCertificate
        } elseif (Test-Path -LiteralPath $Paths.DatabaseCertificate) {
            throw 'Unexpected database TLS material exists before migration 0013; preserving it for manual review.'
        }
        if ($existingContainer) {
            if (-not (Test-LocalPilotPortAvailable $ApiPort) -or -not (Test-LocalPilotPortAvailable $HttpsPort)) {
                throw 'A web loopback pilot port is occupied; no resource was changed.'
            }
        } elseif (-not (Test-LocalPilotPortAvailable $DatabasePort) -or
            -not (Test-LocalPilotPortAvailable $ApiPort) -or
            -not (Test-LocalPilotPortAvailable $HttpsPort)) {
            throw 'A configured loopback pilot port is occupied; no resource was changed.'
        }
        $ownerPassword = Get-Content -LiteralPath $Paths.OwnerPassword -Raw -Encoding ASCII
        $appPassword = Read-LocalPilotSecret $Paths.AppPassword
        $initializeNow = $true
    } else {
        $initializeNow = $false
    }

    if ($initializeNow) {
        if (-not $reuseContainer) { New-LocalPilotContainer $imageId $ownerPassword }
        if (-not $reuseContainer) { $migrationInfo = Apply-LocalPilotBaseMigrations $appPassword }
        $geoMigration = Install-LocalPilotGeoRoles $migrationInfo
        Enable-LocalPilotDatabaseTls
        $packetHash = Publish-ApprovedLocalGeo $Paths $migrationInfo $true
        if ($migrationInfo.owner_migration_applied) {
            if (-not (Test-Path -LiteralPath $Paths.OwnerBootstrapPassword)) { throw 'Owner bootstrap credential is absent from the verified 0014 recovery checkpoint.' }
            $bootstrapRole = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d postgres `
                -c "SELECT CASE WHEN EXISTS(SELECT 1 FROM pg_roles WHERE rolname='rahgard_pilot_owner_bootstrap' AND rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolbypassrls) THEN 'ok' ELSE 'bad' END" 2>$null
            if ($LASTEXITCODE -ne 0 -or ($bootstrapRole | Out-String).Trim() -ne 'ok') { throw 'Owner bootstrap DB role differs from the verified 0014 recovery state.' }
            $hash14 = $migrationInfo.migration_0014_hash
        } else { $hash14 = Apply-LocalOwnerMigration $migrationInfo }
        Install-LocalPilotBackupRole
        $dbTlsHash = Assert-LocalPilotDatabaseTls ([pscustomobject]@{
            database_certificate_sha256=$null; marker=$migrationInfo.marker; database_port=$DatabasePort
        })
        $certificateThumbprint = New-LocalPilotCertificate
        $null = Assert-LocalPilotHttpsCertificate $certificateThumbprint
        Push-Location $FrontendRoot
        try { & npm.cmd run build | Out-Null; if ($LASTEXITCODE -ne 0) { throw 'PWA production build failed before runtime state was accepted.' } }
        finally { Pop-Location }
        $state = [ordered]@{
            schema='rahgard.local-pilot.v1'; lifecycle='ready'; data_root=$Paths.Root; root_sha256=$Paths.RootHash
            container_name=$Paths.Container; container_image=$Paths.Image; container_image_id=$imageId
            bind_mount=$Paths.Db; database=$Paths.Database; database_port=$DatabasePort
            api_port=$ApiPort; https_port=$HttpsPort; marker=$migrationInfo.marker
            migration_count=15; migration_0012_sha256=$migrationInfo.migration_0012_hash
            migration_0013_sha256=$geoMigration.hash_0013; migration_0014_sha256=$hash14
            geo_packet_sha256=$packetHash; https_thumbprint=$certificateThumbprint
            database_certificate_sha256=$dbTlsHash; configuration_sha256=(Get-LocalPilotConfigDigest)
            pwa_build_sha256=(Get-LocalPilotBuildDigest)
            created_utc=[DateTime]::UtcNow.ToString('o'); last_started_utc=$null
            api_process=$null; proxy_process=$null; restore_candidates=@()
        }
        Write-LocalPilotState $Paths $state
    } else {
        $imageId = Assert-LocalPilotTools $Paths
        if ($state.container_image_id -ne $imageId) { throw 'The installed PostgreSQL image digest differs from the recorded pilot image; refusing an implicit upgrade.' }
        $container = Get-LocalPilotContainer $Paths
        if (-not $container) { throw 'The recorded PostgreSQL container is missing; refusing to create a replacement over persistent data.' }
        if ($container.State.Status -ne 'running') {
            & docker start $Paths.Container | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'Could not start the exact recorded PostgreSQL container.' }
            $databaseReady = $false
            for ($attempt=0; $attempt -lt 90; $attempt++) {
                & docker exec $Paths.Container pg_isready -U ai_tourism_owner -d $Paths.Database | Out-Null
                if ($LASTEXITCODE -eq 0) { $databaseReady = $true; break }
                Start-Sleep -Seconds 1
            }
            if (-not $databaseReady) { throw 'The exact persistent PostgreSQL container did not become ready after start.' }
        }
        $stateObj = [pscustomobject]$state
        Enable-LocalPilotDatabaseTls
        $null = Assert-LocalPilotReady $stateObj
        $null = Assert-LocalPilotDatabaseTls $stateObj
        $null = Assert-LocalPilotHttpsCertificate ([string]$state.https_thumbprint)
        if ((Get-LocalPilotConfigDigest) -ne [string]$state.configuration_sha256) {
            throw 'Runtime source/configuration checksums changed. Run the explicit Upgrade action before starting new code.'
        }
    }
    if (-not (Test-Path -LiteralPath $Paths.Pfx) -or -not (Test-Path -LiteralPath $Paths.PfxCertificate)) {
        throw 'Local HTTPS certificate material is missing; refusing to start HTTP-only fallback.'
    }
    Push-Location $FrontendRoot
    try {
        & npm.cmd run build | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'PWA production build failed; no public fallback was started.' }
    } finally { Pop-Location }
    $stateObj = [pscustomobject]$state
    $apiReady = $false
    try {
        $apiProbe = Invoke-WebRequest -Uri "http://127.0.0.1:$($state.api_port)/health/ready" -TimeoutSec 2 -UseBasicParsing
        $apiReady = $apiProbe.StatusCode -eq 200
    } catch { $apiReady = $false }
    $proxyListener = @(Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1 -LocalPort ([int]$state.https_port) -ErrorAction SilentlyContinue)
    if (-not $apiReady -or -not $proxyListener.Count) {
        if ($stateObj.api_process) { Stop-LocalPilotManagedProcess $stateObj.api_process 'api' $stateObj; $stateObj.api_process = $null }
        if ($stateObj.proxy_process) { Stop-LocalPilotManagedProcess $stateObj.proxy_process 'proxy' $stateObj; $stateObj.proxy_process = $null }
        Start-LocalPilotWebProcesses $stateObj
    }
    $stateObj.last_started_utc = [DateTime]::UtcNow.ToString('o')
    Write-LocalPilotState $Paths $stateObj
    Get-LocalPilotRuntimeStatus $stateObj
}

function Stop-LocalPilot {
    $state = Get-LocalPilotStateOrFail
    Stop-LocalPilotManagedProcess $state.proxy_process 'proxy' $state
    Stop-LocalPilotManagedProcess $state.api_process 'api' $state
    $container = Get-LocalPilotContainer $Paths
    if ($container -and $container.State.Status -eq 'running') {
        & docker stop --time 60 $Paths.Container | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Could not stop the exact persistent PostgreSQL container cleanly.' }
    }
    $state.proxy_process = $null; $state.api_process = $null
    Write-LocalPilotState $Paths $state
    [pscustomobject]@{ status='stopped'; database_data_preserved=$true; data_root=$Paths.Root; container=$Paths.Container }
}

function Invoke-LocalPilotBackup {
    if (-not $ConfirmPrivatePilot) { throw 'Backup requires -ConfirmPrivatePilot.' }
    $state = Get-LocalPilotStateOrFail
    $null = Assert-LocalPilotReady $state
    Install-LocalPilotBackupRole
    $python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    $backupScript = Join-Path $ProjectRoot 'engineering\pilot\persistent_backup.py'
    $envMap = @{
        RAHGARD_PILOT_PGHOST='127.0.0.1'; RAHGARD_PILOT_PGPORT=[string]$state.database_port
        RAHGARD_PILOT_DATABASE=$Paths.Database; RAHGARD_PILOT_DATABASE_MARKER=$state.marker
        RAHGARD_PILOT_BACKUP_DIR=$Paths.Backups; PGSSLROOTCERT=$Paths.DatabaseCertificate
        PGSSLMODE='verify-full'; RAHGARD_PILOT_DOCKER_CONTAINER=$Paths.Container
    }
    $proc = Start-LocalPilotProcess -File $python -Arguments @($backupScript,'--confirm-private-pilot') `
        -WorkingDirectory (Join-Path $ProjectRoot 'engineering\pilot') -Environment $envMap `
        -Stdout (Join-Path $Paths.Logs 'backup.log') -Stderr (Join-Path $Paths.Logs 'backup-error.log')
    $backupExitCode = [int]$proc.ExitCode
    if ($backupExitCode -ne 0) { throw 'Private PostgreSQL backup failed; check ACL-protected backup logs.' }
    Get-ChildItem -LiteralPath $Paths.Backups -File | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1 |
        ForEach-Object { Assert-LocalPilotAcl $_.FullName; [pscustomobject]@{ status='backup_verified'; path=$_.FullName; bytes=$_.Length; sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant(); encryption='Windows-user DPAPI envelope' } }
}

function Invoke-LocalPilotRestore {
    if (-not $ConfirmRestoreRehearsal) { throw 'Restore is an isolated rehearsal only and requires -ConfirmRestoreRehearsal; it never replaces the active pilot database.' }
    if (-not $Archive) { throw '-Archive is required.' }
    $state = Get-LocalPilotStateOrFail
    $null = Assert-LocalPilotReady $state
    $archivePath = [IO.Path]::GetFullPath($Archive)
    $backupPrefix = $Paths.Backups.TrimEnd('\') + '\'
    if (-not $archivePath.StartsWith($backupPrefix, [StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $archivePath -PathType Leaf)) { throw 'Restore archive must be an existing file inside the private pilot backup directory.' }
    Assert-LocalPilotAcl $archivePath
    $archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $restorePasswordPath = Join-Path $Paths.Secrets 'restore-password.dpapi'
    $restoreRoleCheck = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d postgres -c "SELECT count(*) FROM pg_roles WHERE rolname='ai_tourism_restore'"
    if ($LASTEXITCODE -ne 0) { throw 'Cannot verify isolated restore role.' }
    if ([int](($restoreRoleCheck | Out-String).Trim()) -eq 0) {
        if (Test-Path -LiteralPath $restorePasswordPath) { throw 'Restore credential exists but its PostgreSQL role does not; refusing reconciliation.' }
        $restorePassword = New-LocalPilotRandomHex 32
        Save-LocalPilotSecret $restorePasswordPath $restorePassword
        Invoke-LocalPilotDockerSql "CREATE ROLE ai_tourism_restore LOGIN PASSWORD '$restorePassword' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS" -Database 'postgres'
    } elseif (-not (Test-Path -LiteralPath $restorePasswordPath)) { throw 'Restore role exists without a DPAPI credential; refusing password reset.' }
    $restorePassword = Read-LocalPilotSecret $restorePasswordPath
    $candidate = 'rahgard_restore_' + (New-LocalPilotRandomHex 6)
    $candidateMarker = New-LocalPilotRandomHex 24
    Invoke-LocalPilotDockerSql "CREATE DATABASE $candidate OWNER ai_tourism_restore" -Database 'postgres'
    # Extensions are installed by the operator only in this newly-created
    # candidate. The restore role remains non-superuser and only restores the
    # application objects. The Python guard verifies exact installed versions.
    Invoke-LocalPilotDockerSql @'
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;
GRANT USAGE, CREATE ON SCHEMA tiger, topology TO ai_tourism_restore;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA tiger, topology TO ai_tourism_restore;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA tiger, topology TO ai_tourism_restore;
'@ -Database $candidate
    Invoke-LocalPilotDockerSql "CREATE TABLE public.rahgard_restore_rehearsal_marker(marker_value text NOT NULL); INSERT INTO public.rahgard_restore_rehearsal_marker VALUES ('$candidateMarker'); GRANT SELECT ON public.rahgard_restore_rehearsal_marker TO ai_tourism_restore" -Database $candidate
    $envMap = @{
        RAHGARD_RESTORE_PGHOST='127.0.0.1'; RAHGARD_RESTORE_PGPORT=[string]$state.database_port
        RAHGARD_RESTORE_DATABASE=$candidate; RAHGARD_RESTORE_MARKER=$candidateMarker
        RAHGARD_RESTORE_ARCHIVE=$archivePath; RAHGARD_RESTORE_ARCHIVE_SHA256=$archiveHash
        RAHGARD_RESTORE_EXPECTED_MIGRATIONS=[string]$state.migration_count
        RAHGARD_RESTORE_SPOOL_DIR=$Paths.Backups; PGSSLROOTCERT=$Paths.DatabaseCertificate
        PGSSLMODE='verify-full'; RAHGARD_PILOT_DOCKER_CONTAINER=$Paths.Container
    }
    $script = Join-Path $ProjectRoot 'engineering\pilot\persistent_restore_rehearsal.py'
    $python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    $candidateInfo = @{ database=$candidate; archive_sha256=$archiveHash; status='restore_in_progress'; created_utc=[DateTime]::UtcNow.ToString('o') }
    $state.restore_candidates = @($state.restore_candidates) + @($candidateInfo)
    Write-LocalPilotState $Paths $state
    $proc = Start-LocalPilotProcess -File $python -Arguments @($script,'--confirm-isolated-restore') `
        -WorkingDirectory (Join-Path $ProjectRoot 'engineering\pilot') -Environment $envMap `
        -Stdout (Join-Path $Paths.Logs ($candidate + '.restore.log')) -Stderr (Join-Path $Paths.Logs ($candidate + '.restore-error.log'))
    $restoreExitCode = [int]$proc.ExitCode
    foreach ($item in $state.restore_candidates) { if ($item.database -eq $candidate) { $item.status = if ($restoreExitCode -eq 0) { 'verified_isolated_candidate' } else { 'failed_preserved_for_inspection' } } }
    Write-LocalPilotState $Paths $state
    if ($restoreExitCode -ne 0) { throw "Isolated restore rehearsal failed. Candidate database '$candidate' and archive are preserved; active database was not changed." }
    [pscustomobject]@{ status='restore_rehearsal_passed'; candidate_database=$candidate; archive_sha256=$archiveHash; active_database_unchanged=$true; candidate_activated=$false }
}

function Invoke-LocalPilotUpgrade {
    if (-not $ConfirmPrivatePilot) { throw 'Upgrade requires -ConfirmPrivatePilot.' }
    $state = Get-LocalPilotStateOrFail
    $null = Assert-LocalPilotReady $state
    $actual = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database -c 'SELECT count(*) FROM system.schema_migrations'
    if ($LASTEXITCODE -ne 0) { throw 'Could not read migration ledger.' }
    if ([int](($actual | Out-String).Trim()) -ne [int]$state.migration_count) { throw 'Migration ledger and local state disagree; upgrade stopped without changing the database.' }
    $providerMigration = Join-Path $LocalSql '015_ai_provider_admin.sql'
    $migrationCandidates = @(Get-ChildItem -LiteralPath $LocalSql -Filter '015_*.sql' -File -ErrorAction SilentlyContinue)
    if ($migrationCandidates.Count -gt 1 -or ($migrationCandidates.Count -eq 1 -and $migrationCandidates[0].Name -ne '015_ai_provider_admin.sql')) {
        throw 'An unregistered SQL migration exists; upgrade is fail-closed.'
    }
    foreach ($item in @(@('013_private_pilot_geo_audit.sql',$state.migration_0013_sha256),@('014_local_owner_login.sql',$state.migration_0014_sha256))) {
        $file = Join-Path $LocalSql $item[0]
        if (-not (Test-Path -LiteralPath $file) -or (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item[1]) {
            throw "Migration checksum drift detected for $($item[0]); no upgrade was attempted."
        }
    }
    if ([int]$state.migration_count -eq 15 -and $ApplyProviderAdminMigration) {
        if (-not (Test-Path -LiteralPath $providerMigration)) { throw 'Provider-admin migration file is missing.' }
        $expectedTarget = "$($Paths.Database)@127.0.0.1:$([int]$state.database_port)"
        if ($ConfirmProviderAdminTarget -cne $expectedTarget) { throw "Target confirmation must exactly equal $expectedTarget." }
    } elseif ($ApplyProviderAdminMigration -and [int]$state.migration_count -ne 15) {
        throw 'Provider-admin migration can only be applied once from the exact 15-migration baseline.'
    }
    Push-Location $FrontendRoot
    try { & npm.cmd run build | Out-Null; if ($LASTEXITCODE -ne 0) { throw 'Frontend production build failed; old database and prior release data remain intact.' } }
    finally { Pop-Location }
    if ([int]$state.migration_count -eq 15 -and $ApplyProviderAdminMigration) {
        $migrationHash = (Get-FileHash -LiteralPath $providerMigration -Algorithm SHA256).Hash.ToLowerInvariant()
        $backupResult = @(Invoke-LocalPilotBackup | Where-Object { $_.status -eq 'backup_verified' } | Select-Object -Last 1)
        if ($backupResult.Count -ne 1 -or $backupResult[0].encryption -ne 'Windows-user DPAPI envelope' -or
            $backupResult[0].sha256 -notmatch '^[a-f0-9]{64}$') {
            throw 'A fresh encrypted backup could not be verified; migration was not attempted.'
        }
        $wrapper = "\set ON_ERROR_STOP on`n\set pilot_marker $($state.marker)`n\set migration_0014_hash $($state.migration_0014_sha256)`n\set migration_hash $migrationHash`nSET ROLE rahgard_pilot_geo_migrator;`n\i /opt/rahgard/pilot-sql/015_ai_provider_admin.sql`nRESET ROLE;`n"
        # The no-login migrator receives only the transient DDL/FK grants needed
        # for this exact additive migration. They are revoked even on failure.
        Invoke-LocalPilotDockerSql @"
GRANT CREATE ON DATABASE $($Paths.Database) TO rahgard_pilot_geo_migrator;
GRANT USAGE, CREATE ON SCHEMA identity TO rahgard_pilot_geo_migrator;
GRANT REFERENCES(user_id) ON identity.users TO rahgard_pilot_geo_migrator;
GRANT REFERENCES(session_id) ON identity.web_sessions TO rahgard_pilot_geo_migrator;
"@ -Database $Paths.Database
        $migrationDockerArgs = @('-e',('RAHGARD_PILOT_DATABASE_MARKER=' + $state.marker),
            '-e',('RAHGARD_PILOT_MIGRATION_0014_SHA256=' + $state.migration_0014_sha256),
            '-e',('RAHGARD_PILOT_MIGRATION_0015_SHA256=' + $migrationHash))
        try { Invoke-LocalPilotGuardedTcpSql $wrapper -Database $Paths.Database -DockerArgs $migrationDockerArgs }
        finally {
            Invoke-LocalPilotDockerSql @"
REVOKE CREATE ON DATABASE $($Paths.Database) FROM rahgard_pilot_geo_migrator;
REVOKE CREATE ON SCHEMA identity FROM rahgard_pilot_geo_migrator;
REVOKE REFERENCES(user_id) ON identity.users FROM rahgard_pilot_geo_migrator;
REVOKE REFERENCES(session_id) ON identity.web_sessions FROM rahgard_pilot_geo_migrator;
"@ -Database $Paths.Database
        }
        $migrationRow = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database `
            -c "SELECT migration_id||'|'||sha256 FROM system.schema_migrations WHERE migration_id='0015_ai_provider_admin'"
        if ($LASTEXITCODE -ne 0 -or ($migrationRow | Out-String).Trim() -ne "0015_ai_provider_admin|$migrationHash") {
            throw 'Provider-admin migration did not pass checksum verification.'
        }
        $state.migration_count = 16
        $state | Add-Member -NotePropertyName migration_0015_sha256 -NotePropertyValue $migrationHash -Force
        Write-LocalPilotState $Paths $state
    } elseif ([int]$state.migration_count -eq 16) {
        if (-not (Test-Path -LiteralPath $providerMigration) -or
            (Get-FileHash -LiteralPath $providerMigration -Algorithm SHA256).Hash.ToLowerInvariant() -ne [string]$state.migration_0015_sha256) {
            throw 'Provider-admin migration checksum drift detected; application upgrade was not attempted.'
        }
    }
    Stop-LocalPilotManagedProcess $state.proxy_process 'proxy' $state
    Stop-LocalPilotManagedProcess $state.api_process 'api' $state
    $state.proxy_process=$null; $state.api_process=$null
    $state.configuration_sha256=Get-LocalPilotConfigDigest
    $state.pwa_build_sha256=Get-LocalPilotBuildDigest
    Write-LocalPilotState $Paths $state
    Start-LocalPilotWebProcesses ([pscustomobject]$state)
    [pscustomobject]@{ status=if ($ApplyProviderAdminMigration) {'provider_admin_migration_applied'} else {'application_updated'}; database=$Paths.Database; migration_count=$state.migration_count; configuration_sha256=$state.configuration_sha256; pwa_build_sha256=$state.pwa_build_sha256 }
}

function Invoke-ProviderAdminProvisioning {
    if (-not $ConfirmPrivatePilot) { throw 'Provider-admin provisioning requires -ConfirmPrivatePilot.' }
    $userId = [guid]::Empty
    if (-not [guid]::TryParse($ProviderAdminUserId, [ref]$userId) -or $userId -eq [guid]::Empty) {
        throw '-ProviderAdminUserId must be the exact existing local-owner user UUID.'
    }
    if (-not $ProviderAdminReason -or $ProviderAdminReason.Length -lt 10 -or
        $ProviderAdminReason.Length -gt 120 -or $ProviderAdminReason -notmatch '^[A-Za-z0-9 ._-]+$') {
        throw '-ProviderAdminReason must be a 10-120 character non-secret audit reason using plain ASCII letters, numbers, spaces, dot, underscore or hyphen.'
    }
    $state = Get-LocalPilotStateOrFail
    $null = Assert-LocalPilotReady $state
    if ([int]$state.migration_count -ne 16) { throw 'Apply and verify the additive provider-admin migration before provisioning.' }
    $expectedTarget = "$($Paths.Database)@127.0.0.1:$([int]$state.database_port)"
    if ($ConfirmProviderAdminTarget -cne $expectedTarget) {
        throw "Explicit target confirmation must exactly equal $expectedTarget."
    }
    $id = $userId.ToString('D')
    $eligible = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database `
        -c "SELECT CASE WHEN EXISTS(SELECT 1 FROM identity.users WHERE user_id='$id' AND auth_subject='local_owner' AND account_status='active' AND is_synthetic=FALSE) AND NOT EXISTS(SELECT 1 FROM identity.ai_provider_admin_grants WHERE user_id='$id' AND revoked_at IS NULL) THEN 'eligible' ELSE 'blocked' END"
    if ($LASTEXITCODE -ne 0 -or ($eligible | Out-String).Trim() -ne 'eligible') {
        throw 'Target must be an active existing local-owner identity without a current provider-admin grant; no account or credentials were changed.'
    }
    $reason = $ProviderAdminReason
    $sql = @"
BEGIN;
INSERT INTO identity.ai_provider_admin_grants(user_id,granted_by) VALUES ('$id','$id')
ON CONFLICT (user_id) DO UPDATE SET granted_at=pg_catalog.now(),granted_by=EXCLUDED.granted_by,revoked_at=NULL;
INSERT INTO identity.ai_provider_admin_mfa(user_id) VALUES ('$id') ON CONFLICT DO NOTHING;
INSERT INTO ai_provider.audit_events(actor_id,action,target_type,target_id,outcome,metadata)
VALUES ('$id','admin_provisioned','admin','$id','success',jsonb_build_object('method','private_local_operator','reason','$reason'));
COMMIT;
"@
    Invoke-LocalPilotDockerSql $sql -Database $Paths.Database
    $verified = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database `
        -c "SELECT CASE WHEN EXISTS(SELECT 1 FROM identity.ai_provider_admin_grants WHERE user_id='$id' AND revoked_at IS NULL) AND EXISTS(SELECT 1 FROM identity.ai_provider_admin_mfa WHERE user_id='$id' AND enabled_at IS NULL) THEN 'ok' ELSE 'bad' END"
    if ($LASTEXITCODE -ne 0 -or ($verified | Out-String).Trim() -ne 'ok') { throw 'Provider-admin grant did not pass post-write verification.' }
    [pscustomobject]@{ status='provider_admin_provisioned'; user_id=$id; migration_count=$state.migration_count; totp_enrollment_required=$true; recovery_codes_issued=$false }
}

function Invoke-ProviderAdminRevocation {
    if (-not $ConfirmPrivatePilot) { throw 'Provider-admin revocation requires -ConfirmPrivatePilot.' }
    $userId = [guid]::Empty
    if (-not [guid]::TryParse($ProviderAdminUserId, [ref]$userId) -or $userId -eq [guid]::Empty) {
        throw '-ProviderAdminUserId must be the exact existing provider-admin user UUID.'
    }
    if (-not $ProviderAdminReason -or $ProviderAdminReason.Length -lt 10 -or
        $ProviderAdminReason.Length -gt 120 -or $ProviderAdminReason -notmatch '^[A-Za-z0-9 ._-]+$') {
        throw '-ProviderAdminReason must be a 10-120 character non-secret audit reason.'
    }
    $state = Get-LocalPilotStateOrFail
    $null = Assert-LocalPilotReady $state
    if ([int]$state.migration_count -ne 16) { throw 'Provider-admin migration 015 is not installed.' }
    $expectedTarget = "$($Paths.Database)@127.0.0.1:$([int]$state.database_port)"
    if ($ConfirmProviderAdminTarget -cne $expectedTarget) { throw "Explicit target confirmation must exactly equal $expectedTarget." }
    $id = $userId.ToString('D')
    $eligible = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database `
        -c "SELECT CASE WHEN EXISTS(SELECT 1 FROM identity.users u JOIN identity.ai_provider_admin_grants g USING(user_id) WHERE u.user_id='$id' AND u.auth_subject='local_owner' AND u.account_status='active' AND g.revoked_at IS NULL) THEN 'eligible' ELSE 'blocked' END"
    if ($LASTEXITCODE -ne 0 -or ($eligible | Out-String).Trim() -ne 'eligible') {
        throw 'Target must be an active existing local owner with an active provider-admin grant.'
    }
    $reason = $ProviderAdminReason
    $sql = @"
BEGIN;
UPDATE identity.ai_provider_admin_step_up SET revoked_at=pg_catalog.now() WHERE user_id='$id' AND revoked_at IS NULL;
UPDATE identity.ai_provider_admin_mfa SET secret_ref=NULL,pending_secret_ref=NULL,enabled_at=NULL,
    last_totp_counter=-1,recovery_hashes=ARRAY[]::BYTEA[],version=version+1,updated_at=pg_catalog.now()
    WHERE user_id='$id';
UPDATE identity.ai_provider_admin_grants SET revoked_at=pg_catalog.now() WHERE user_id='$id' AND revoked_at IS NULL;
INSERT INTO ai_provider.audit_events(actor_id,action,target_type,target_id,outcome,metadata)
VALUES ('$id','admin_revoked','admin','$id','success',jsonb_build_object('method','private_local_operator','reason','$reason'));
COMMIT;
"@
    Invoke-LocalPilotDockerSql $sql -Database $Paths.Database
    $verified = & docker exec $Paths.Container psql -X -q -A -t -U ai_tourism_owner -d $Paths.Database `
        -c "SELECT CASE WHEN EXISTS(SELECT 1 FROM identity.ai_provider_admin_grants WHERE user_id='$id' AND revoked_at IS NOT NULL) AND NOT EXISTS(SELECT 1 FROM identity.ai_provider_admin_step_up WHERE user_id='$id' AND revoked_at IS NULL) THEN 'ok' ELSE 'bad' END"
    if ($LASTEXITCODE -ne 0 -or ($verified | Out-String).Trim() -ne 'ok') { throw 'Provider-admin revocation failed post-write verification.' }
    [pscustomobject]@{ status='provider_admin_revoked'; user_id=$id; migration_count=$state.migration_count }
}

function Invoke-LocalPilotRollback {
    throw 'Database rollback is intentionally unavailable: migrations 0013/0014 have no reviewed down migration. Use Restore to validate an encrypted backup in a separate private candidate; active cutover requires a separately reviewed operation.'
}

function Set-LocalPilotCertificateTrust([bool]$Trust) {
    $state = Get-LocalPilotStateOrFail
    $store = [Security.Cryptography.X509Certificates.X509Store]::new(
        [Security.Cryptography.X509Certificates.StoreName]::Root,
        [Security.Cryptography.X509Certificates.StoreLocation]::CurrentUser)
    $store.Open([Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
    if ($Trust) {
        if (-not $ConfirmPrivatePilot) { $store.Close(); throw 'Certificate trust installation requires -ConfirmPrivatePilot and affects only the current Windows user.' }
        $cert = [Security.Cryptography.X509Certificates.X509Certificate2]::new([IO.File]::ReadAllBytes($Paths.PfxCertificate))
        try {
            if ($cert.Thumbprint -ne $state.https_thumbprint) { throw 'Public certificate does not match the recorded localhost certificate.' }
            $san = [string]($cert.Extensions | Where-Object { $_.Oid.Value -eq '2.5.29.17' } | ForEach-Object { $_.Format($false) })
            if ($san -notmatch 'localhost') { throw 'Certificate does not contain a localhost SAN.' }
            $existing = @($store.Certificates | Where-Object { $_.Thumbprint -eq $state.https_thumbprint })
            if (-not $existing.Count) { $store.Add($cert) }
        } finally {
            $cert.Dispose()
            $store.Close()
        }
        [pscustomobject]@{ status='trusted_current_user_only'; thumbprint=$state.https_thumbprint }
    } else {
        try {
            $existing = @($store.Certificates | Where-Object { $_.Thumbprint -eq $state.https_thumbprint })
            foreach ($cert in $existing) { $store.Remove($cert); $cert.Dispose() }
        } finally {
            $store.Close()
        }
        [pscustomobject]@{ status=if ($existing.Count) { 'removed' } else { 'not_installed' }; thumbprint=$state.https_thumbprint }
    }
}

function Invoke-LocalOwnerBootstrap([bool]$Reset) {
    if (-not $ConfirmPrivatePilot) { throw 'Owner bootstrap or recovery requires -ConfirmPrivatePilot.' }
    $state = Get-LocalPilotStateOrFail
    $null = Assert-LocalPilotReady $state
    if (-not $Paths.OwnerBootstrapPassword -or -not (Test-Path -LiteralPath $Paths.OwnerBootstrapPassword)) { throw 'DPAPI owner-bootstrap role credential is missing.' }
    $envMap = @{
        RAHGARD_PILOT_PGHOST='127.0.0.1'; RAHGARD_PILOT_PGPORT=[string]$state.database_port
        RAHGARD_PILOT_DATABASE=$Paths.Database; RAHGARD_PILOT_DATABASE_MARKER=$state.marker
        RAHGARD_PILOT_OWNER_BOOTSTRAP_PASSWORD=(Read-LocalPilotSecret $Paths.OwnerBootstrapPassword)
        PGSSLMODE='verify-full'; PGSSLROOTCERT=$Paths.DatabaseCertificate
        USERPROFILE=$env:USERPROFILE; LOCALAPPDATA=$env:LOCALAPPDATA
        TEMP=$env:TEMP; TMP=$env:TMP; UV_CACHE_DIR=(Join-Path $Paths.Root 'uv-cache')
    }
    if (-not (Test-Path -LiteralPath $envMap.UV_CACHE_DIR)) { New-Item -ItemType Directory -Path $envMap.UV_CACHE_DIR | Out-Null; Set-LocalPilotAcl $envMap.UV_CACHE_DIR -Directory }
    $oldEnv = @{}
    foreach ($key in $envMap.Keys) { $old = Get-Item -LiteralPath "Env:$key" -ErrorAction SilentlyContinue; if ($old) { $oldEnv[$key] = [string]$old.Value } }
    $preserve = @('PATH','SystemRoot','SYSTEMROOT','WINDIR')
    $scrubbed = @([Environment]::GetEnvironmentVariables().Keys | ForEach-Object { [string]$_ } | Where-Object { $_ -notin $preserve -and $_ -notin $envMap.Keys })
    $scrubbedEnv = @{}
    foreach ($key in $scrubbed) { $old = Get-Item -LiteralPath "Env:$key" -ErrorAction SilentlyContinue; if ($old) { $scrubbedEnv[$key] = [string]$old.Value } }
    $uv = (Get-Command uv -ErrorAction Stop).Source
    try {
        foreach ($key in $scrubbed) { Remove-Item -LiteralPath "Env:$key" -ErrorAction SilentlyContinue }
        foreach ($key in $envMap.Keys) { Set-Item -LiteralPath "Env:$key" -Value ([string]$envMap[$key]) }
        if ($Reset) { & $uv run --offline --locked python backend/scripts/bootstrap_local_owner.py --confirm-password-reset --login-name owner }
        else { & $uv run --offline --locked python backend/scripts/bootstrap_local_owner.py --create-owner --login-name owner }
        $exitCode = $LASTEXITCODE
    } finally {
        foreach ($key in $envMap.Keys) {
            if ($oldEnv.ContainsKey($key)) { Set-Item -LiteralPath "Env:$key" -Value $oldEnv[$key] }
            else { Remove-Item -LiteralPath "Env:$key" -ErrorAction SilentlyContinue }
        }
        foreach ($key in $scrubbed) {
            if ($scrubbedEnv.ContainsKey($key)) { Set-Item -LiteralPath "Env:$key" -Value $scrubbedEnv[$key] }
            else { Remove-Item -LiteralPath "Env:$key" -ErrorAction SilentlyContinue }
        }
    }
    if ($exitCode -ne 0) { throw 'Local owner bootstrap/recovery failed; no password content is logged.' }
    [pscustomobject]@{
        status=if ($Reset) { 'password_reset_completed' } else { 'owner_created' }
        login_name='owner'
        database=$Paths.Database
        database_port=$state.database_port
        data_root=$Paths.Root
        password_captured=$false
    }
}

try {
    switch ($Action) {
        'Start' { if ($PSCmdlet.ShouldProcess($Paths.Root,'Start the persistent private Rahgard pilot')) { Start-LocalPilot } }
        'Stop' { if ($PSCmdlet.ShouldProcess($Paths.Container,'Stop local app processes and database while retaining all persistent data')) { Stop-LocalPilot } }
        'Status' {
            if (-not (Test-Path -LiteralPath $Paths.Root)) { [pscustomobject]@{ status='not_initialized'; data_root=$Paths.Root; no_resources_inspected=$true } ; break }
            Assert-NoReparsePath $Paths.Root
            $state = if (Test-Path -LiteralPath $Paths.State) { Read-LocalPilotState $Paths } else { $null }
            if (-not $state) { [pscustomobject]@{ status='not_initialized'; data_root=$Paths.Root; no_resources_inspected=$true } }
            else { Get-LocalPilotRuntimeStatus $state }
        }
        'Backup' { if ($PSCmdlet.ShouldProcess($Paths.Backups,'Create and verify an encrypted DPAPI PostgreSQL backup')) { Invoke-LocalPilotBackup } }
        'Restore' { if ($PSCmdlet.ShouldProcess($Archive,'Restore into a separate marked candidate database; never switch the active database')) { Invoke-LocalPilotRestore } }
        'Upgrade' { if ($PSCmdlet.ShouldProcess($Paths.Root,'Update application bundle without applying new database migrations')) { Invoke-LocalPilotUpgrade } }
        'ProvisionProviderAdmin' { if ($PSCmdlet.ShouldProcess($Paths.Database,'Grant one existing local owner the separate AI Provider Admin capability')) { Invoke-ProviderAdminProvisioning } }
        'RevokeProviderAdmin' { if ($PSCmdlet.ShouldProcess($Paths.Database,'Revoke provider-admin authority and MFA for one existing local owner')) { Invoke-ProviderAdminRevocation } }
        'Rollback' { Invoke-LocalPilotRollback }
        'TrustCertificate' { if ($PSCmdlet.ShouldProcess('CurrentUser Root certificate store','Trust only the recorded localhost pilot certificate')) { Set-LocalPilotCertificateTrust $true } }
        'UntrustCertificate' { if ($PSCmdlet.ShouldProcess('CurrentUser Root certificate store','Remove only the recorded localhost pilot certificate')) { Set-LocalPilotCertificateTrust $false } }
        'BootstrapOwner' { if ($PSCmdlet.ShouldProcess($Paths.Database,'Create the single local owner account interactively')) { Invoke-LocalOwnerBootstrap $false } }
        'ResetOwner' { if ($PSCmdlet.ShouldProcess($Paths.Database,'Reset the owner password and revoke all existing owner sessions')) { Invoke-LocalOwnerBootstrap $true } }
    }
} catch {
    Write-Error -Message ("Local-pilot failure at line {0}: {1}" -f $_.InvocationInfo.ScriptLineNumber,$_.Exception.Message)
    exit 1
}
