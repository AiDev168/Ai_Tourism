[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][ValidateSet('Start','Status','Stop','Open')][string]$Action,
  [string]$DataRoot = (Join-Path $env:LOCALAPPDATA 'Rahgard\Issue27OwnerDemo'),
  [switch]$OpenBrowser
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$RepoRoot = $ProjectRoot
$BaseCompose = Join-Path $RepoRoot 'deploy\staging\compose.yaml'
$Overlay = Join-Path $RepoRoot 'deploy\staging\compose.issue27-local-demo.yaml'
$MfaOverlay = Join-Path $RepoRoot 'deploy\staging\compose.platform-admin-mfa.yaml'
$Initializer = Join-Path $PSScriptRoot 'initialize.py'
$CertMaker = Join-Path $PSScriptRoot 'make_localhost_cert.py'
$DataRoot = [IO.Path]::GetFullPath($DataRoot)
$RepoPrefix = $RepoRoot.TrimEnd('\') + '\'
if ($DataRoot.StartsWith($RepoPrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Demo data must be outside the repository.' }
if (-not (Test-Path -LiteralPath (Split-Path $DataRoot -Qualifier) -PathType Container)) { throw 'Demo data root must be on an existing local drive.' }
$HashProvider = [Security.Cryptography.SHA256]::Create()
try { $Hash = $HashProvider.ComputeHash([Text.Encoding]::UTF8.GetBytes($DataRoot.ToLowerInvariant())) }
finally { $HashProvider.Dispose() }
$Suffix = [BitConverter]::ToString($Hash).Replace('-','').ToLowerInvariant().Substring(0,12)
$Project = "rahgard-issue27-$Suffix"
$Container = "$Project-db-1"
$Volume = "rahgard_issue27_pg_$Suffix"
$Secrets = Join-Path $DataRoot 'secrets'
$Tls = Join-Path $DataRoot 'tls'
$State = Join-Path $DataRoot 'state'
$Config = Join-Path $DataRoot 'demo.env'
$ReadyMarker = Join-Path $State 'schema-initialized'
$ProcessesFile = Join-Path $State 'managed-processes.json'
$Logs = Join-Path $DataRoot 'logs'

function Protect-DataRoot {
  New-Item -ItemType Directory -Force -Path $DataRoot,$Secrets,$Tls,$State,$Logs | Out-Null
  $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
  & icacls.exe $DataRoot '/setowner' "*$sid" '/T' '/C' | Out-Null
  if ($LASTEXITCODE -ne 0) { throw 'Could not assign the private demo data root to the current Windows user.' }
  & icacls.exe $DataRoot '/inheritance:r' '/grant:r' "*$sid`:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' '/T' '/C' | Out-Null
  if ($LASTEXITCODE -ne 0) { throw 'Could not protect the private demo data root with NTFS ACLs.' }
  # Existing files can have inheritance disabled by the creating shell's
  # integrity level. Grant the current owner explicitly on this private tree.
  foreach ($item in Get-ChildItem -LiteralPath $DataRoot -Force -Recurse) {
    $rights = if ($item.PSIsContainer) { '(OI)(CI)F' } else { 'F' }
    & icacls.exe $item.FullName '/grant:r' "*$sid`:$rights" '*S-1-5-18:(OI)(CI)F' '/C' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not secure an existing file in the private demo root.' }
  }
}
function Random-Hex([int]$Bytes) {
  $buffer = [byte[]]::new($Bytes)
  $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
  [BitConverter]::ToString($buffer).Replace('-','').ToLowerInvariant()
}
function Write-Secret([string]$Name,[string]$Value) {
  $path = Join-Path $Secrets $Name
  [IO.File]::WriteAllText($path,$Value + "`n",[Text.UTF8Encoding]::new($false))
}
function Compose([string[]]$Arguments) {
  & docker compose --project-name $Project --env-file $Config -f $BaseCompose -f $Overlay -f $MfaOverlay @Arguments
  if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed for the Issue 27 demo ($($Arguments[0]))." }
}
function Initialize-PrivateConfig {
  if (-not (Test-Path -LiteralPath $Config)) {
    Protect-DataRoot
    $entries = @{
      pg_owner_password=Random-Hex 32; app_db_password=Random-Hex 32
      geo_authorizer_password=Random-Hex 32; geo_publisher_password=Random-Hex 32
      auth_otp_hmac_secret=Random-Hex 32; auth_csrf_secret=Random-Hex 32
      auth_rate_limit_secret=Random-Hex 32; internal_chat_token=Random-Hex 32
      sms_ir_production_api_key=Random-Hex 32
      platform_admin_mfa_encryption_key_hex=Random-Hex 32
      platform_admin_recovery_pepper=Random-Hex 48
    }
    foreach ($name in $entries.Keys) { Write-Secret $name $entries[$name] }
    $marker = Random-Hex 24
    [IO.File]::WriteAllText((Join-Path $State 'database-marker'),$marker,[Text.UTF8Encoding]::new($false))
    $tlsForward = $Tls.Replace('\','/')
    $secretForward = $Secrets.Replace('\','/')
    $sha = (git -C $RepoRoot rev-parse HEAD).Trim()
    if ($sha -notmatch '^[0-9a-f]{40}$') { throw 'Current source release identity is unavailable.' }
    $envLines = @(
      "RAHGARD_COMPOSE_PROJECT=$Project", "RAHGARD_RELEASE_SHA=$sha",
      "RAHGARD_PG_VOLUME=$Volume", 'RAHGARD_WEB_BIND_PORT=18443',
      "RAHGARD_SECRET_DIR=$secretForward", "RAHGARD_TLS_DIR=$tlsForward",
      'RAHGARD_PUBLIC_HOST=localhost', 'RAHGARD_STAGING_EMAIL_SIGNUP_ENABLED=true',
      'RAHGARD_STAGING_EMAIL_SIGNUP_IP_LIMIT=5', 'RAHGARD_STAGING_EMAIL_SIGNUP_GLOBAL_LIMIT=30',
      'RAHGARD_STAGING_EMAIL_SIGNUP_ACCOUNT_LIMIT=25', 'RAHGARD_SMS_ADAPTER=disabled',
      'RAHGARD_SMS_PRODUCTION_TEMPLATE_ID=0', 'RAHGARD_CHAT_ENABLED=false',
      'RAHGARD_CHAT_MODEL=disabled-local-demo'
    )
    [IO.File]::WriteAllLines($Config,$envLines,[Text.UTF8Encoding]::new($false))
    Protect-DataRoot
  } else {
    if (-not (Test-Path -LiteralPath (Join-Path $State 'database-marker') -PathType Leaf)) { throw 'Demo config exists but its protected identity marker is missing; preserve it for review.' }
    Protect-DataRoot
  }
  # Keep the private local demo's non-secret release marker aligned with the
  # checked-out source when it is restarted after an implementation commit.
  # Do not regenerate credentials, volume identity, or any database state.
  $currentSha = (& git -C $RepoRoot rev-parse HEAD | Out-String).Trim()
  if ($LASTEXITCODE -ne 0 -or $currentSha -notmatch '^[0-9a-f]{40}$') { throw 'Current source release identity is unavailable.' }
  $configLines = [IO.File]::ReadAllLines($Config)
  $shaIndexes = @()
  for ($index = 0; $index -lt $configLines.Length; $index++) {
    if ($configLines[$index] -match '^RAHGARD_RELEASE_SHA=') { $shaIndexes += $index }
  }
  if ($shaIndexes.Count -ne 1 -or $configLines[$shaIndexes[0]] -notmatch '^RAHGARD_RELEASE_SHA=[0-9a-f]{40}$') {
    throw 'Private demo release marker is missing, duplicated, or malformed; preserving it for review.'
  }
  if ($configLines[$shaIndexes[0]] -ne "RAHGARD_RELEASE_SHA=$currentSha") {
    $configLines[$shaIndexes[0]] = "RAHGARD_RELEASE_SHA=$currentSha"
    [IO.File]::WriteAllLines($Config,$configLines,[Text.UTF8Encoding]::new($false))
    Protect-DataRoot
  }
  $env:RAHGARD_DEMO_TLS_DIR = $Tls
  $certResult = (& uv run --project $RepoRoot python $CertMaker | Out-String).Trim()
  if ($LASTEXITCODE -ne 0 -or $certResult -notin @('CREATED','PRESENT')) { throw 'Demo TLS certificate creation/validation failed.' }
}
function Require-FreePort([int]$Port) {
  $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
  if ($listeners.Count -gt 0) { throw "Required localhost demo port $Port is already occupied; no process was stopped." }
}
function Start-Demo {
  Initialize-PrivateConfig
  if (-not (Test-Path -LiteralPath $ReadyMarker)) {
    Require-FreePort 443; Require-FreePort 18543
    $existingVolumes = @(& docker volume ls --format '{{.Name}}')
    if ($LASTEXITCODE -ne 0) { throw 'Could not verify isolated demo volume inventory.' }
    if ($existingVolumes -contains $Volume) {
      $priorDb = (& docker compose --project-name $Project --env-file $Config -f $BaseCompose -f $Overlay -f $MfaOverlay ps -q db 2>$null | Out-String).Trim()
      if (-not $priorDb) { throw 'Unmarked Issue 27 volume exists without its task-owned database container; preserving it for manual inspection.' }
      $prior = @(& docker inspect $priorDb | ConvertFrom-Json)[0]
      if ($prior.Config.Labels.'com.docker.compose.project' -ne $Project -or $prior.Config.Labels.'com.docker.compose.service' -ne 'db' -or $prior.Config.Image -ne 'rahgard-postgres:17-postgis36-vector087' -or -not ($prior.Mounts | Where-Object { $_.Destination -eq '/var/lib/postgresql/data' -and $_.Type -eq 'volume' -and $_.Name -eq $Volume })) {
        throw 'Existing unmarked volume is not bound to the exact task-owned PostgreSQL container; preserving it.'
      }
      $ledgerTable = (& docker exec $priorDb psql -X -q -A -t -U ai_tourism_owner -d rahgard_pilot_vps_staging -c "SELECT to_regclass('system.schema_migrations') IS NOT NULL" 2>$null | Out-String).Trim()
      if ($LASTEXITCODE -ne 0 -or $ledgerTable -ne 'f') { throw 'Unmarked task database is not a fresh empty schema; preserving it for manual review.' }
    }
  }
  Compose @('config','--quiet')
  # Use the installed PG17 image without pulling or retagging. Current checked-
  # out FastAPI/PWA source runs locally because Docker Hub is unavailable here.
  Compose @('up','-d','--pull','never','db')
  $dbId = (Compose @('ps','-q','db') | Out-String).Trim()
  if ($dbId -notmatch '^[a-f0-9]{64}$') { throw 'Could not identify the exact Issue 27 database container.' }
  $dbReady = $false
  for ($i=0; $i -lt 60; $i++) {
    & docker exec $dbId pg_isready -U ai_tourism_owner -d rahgard_pilot_vps_staging *> $null
    if ($LASTEXITCODE -eq 0) { $dbReady = $true; break }
    Start-Sleep -Seconds 1
  }
  if (-not $dbReady) { throw 'Task-owned isolated PostgreSQL did not become ready; preserve volume and inspect privately.' }
  $dbMeta = @(& docker inspect $dbId | ConvertFrom-Json)[0]
  if ($dbMeta.Config.Labels.'com.docker.compose.project' -ne $Project -or $dbMeta.Config.Labels.'com.docker.compose.service' -ne 'db' -or $dbMeta.Config.Image -ne 'rahgard-postgres:17-postgis36-vector087' -or -not ($dbMeta.Mounts | Where-Object { $_.Destination -eq '/var/lib/postgresql/data' -and $_.Type -eq 'volume' -and $_.Name -eq $Volume })) { throw 'Issue 27 PostgreSQL container/image/volume identity differs; preserving it.' }
  if (-not (Test-Path -LiteralPath $ReadyMarker)) {
    $env:RAHGARD_DEMO_DB_CONTAINER = $Container
    $env:RAHGARD_PILOT_DATABASE_MARKER = (Get-Content -LiteralPath (Join-Path $State 'database-marker') -Raw).Trim()
    & uv run --project $RepoRoot python $Initializer
    if ($LASTEXITCODE -ne 0) { throw 'Fresh isolated database initialization failed. State is preserved; do not retry/reset it.' }
    [IO.File]::WriteAllText($ReadyMarker,'complete',[Text.UTF8Encoding]::new($false))
  }
  Require-FreePort 443
  Require-FreePort 8801
  Push-Location (Join-Path $RepoRoot 'frontend')
  try {
    $priorPreference = $ErrorActionPreference
    try {
      $ErrorActionPreference = 'Continue'
      & npm.cmd run build *> (Join-Path $Logs 'frontend-build.log')
      $buildExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $priorPreference }
    if ($buildExit -ne 0) { throw 'PWA production build failed; private build log retained.' }
  } finally { Pop-Location }
  $python = (& uv run --project $RepoRoot python -c 'import sys; print(sys._base_executable)' | Out-String).Trim()
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Repository Python environment is unavailable.' }
  $processes = @()
  $apiOut = Join-Path $Logs 'api.stdout.log'; $apiErr = Join-Path $Logs 'api.stderr.log'
  $env:RAHGARD_DEMO_ROOT = $DataRoot
  $api = Start-Process -FilePath $python -ArgumentList @((Join-Path $PSScriptRoot 'run_api.py'),$DataRoot) -WorkingDirectory $RepoRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr
  $processes += [pscustomobject]@{Name='api';Pid=$api.Id;StartUtc=$api.StartTime.ToUniversalTime().ToString('o');Executable=$python;Script=(Join-Path $PSScriptRoot 'run_api.py')}
  Start-Sleep -Seconds 2
  if ($api.HasExited) { throw 'Local API process exited during startup; inspect private task logs.' }
  $webOut = Join-Path $Logs 'web.stdout.log'; $webErr = Join-Path $Logs 'web.stderr.log'
  $web = Start-Process -FilePath $python -ArgumentList @((Join-Path $PSScriptRoot 'serve.py')) -WorkingDirectory $RepoRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $webOut -RedirectStandardError $webErr
  $processes += [pscustomobject]@{Name='web';Pid=$web.Id;StartUtc=$web.StartTime.ToUniversalTime().ToString('o');Executable=$python;Script=(Join-Path $PSScriptRoot 'serve.py')}
  ConvertTo-Json -InputObject $processes -Depth 4 | Set-Content -LiteralPath $ProcessesFile -Encoding UTF8
  $ready = $false
  for ($i=0; $i -lt 60; $i++) {
    $priorPreference = $ErrorActionPreference
    try { $ErrorActionPreference = 'Continue'; $status = (& curl.exe -k -sS -o NUL -w '%{http_code}' https://localhost/health/live 2>$null | Out-String).Trim(); $curlExit = $LASTEXITCODE }
    finally { $ErrorActionPreference = $priorPreference }
    if ($curlExit -eq 0 -and $status -eq '200') { $ready = $true; break }
    Start-Sleep -Seconds 2
  }
  if (-not $ready) { throw 'Local API/HTTPS did not become healthy; preserve state and inspect private task logs.' }
  $authMethod = (& curl.exe -k -sS https://localhost/api/v1/auth/method 2>$null | Out-String | ConvertFrom-Json)
  if ($LASTEXITCODE -ne 0 -or -not $authMethod.staging_email_signup) { throw 'Staging email registration is not enabled on the isolated demo.' }
  Write-Host 'PASS: isolated Owner/Partner/Traveler demo is running.' -ForegroundColor Green
  Write-Host 'URL: https://localhost/admin   |   https://localhost/partners'
  Write-Host 'Environment: loopback only; SMS/Chat/RAG/provider-admin disabled; 25 runtime migrations through 0026.'
  Write-Host "Persistent demo volume: $Volume (Stop preserves this volume)."
  if ($OpenBrowser) { Open-Demo }
}
function Status-Demo {
  if (-not (Test-Path -LiteralPath $Config)) { Write-Host 'NOT STARTED'; return }
  Compose @('ps')
  if (Test-Path $ProcessesFile) {
    $tracked = Get-Content -LiteralPath $ProcessesFile -Raw | ConvertFrom-Json
    foreach ($item in $tracked) {
      $port = if ($item.Name -eq 'api') { 8801 } else { 443 }
      $listen = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
      $proc = if ($listen) { Get-CimInstance Win32_Process -Filter "ProcessId=$($listen.OwningProcess)" -ErrorAction SilentlyContinue }
      if ($proc -and $proc.CommandLine -like "*$($item.Script)*") { Write-Host "$($item.Name): running" }
      else { Write-Host "$($item.Name): stopped or identity changed" }
    }
  }
  if (Test-Path -LiteralPath $ReadyMarker) { Write-Host 'Schema initialization marker: complete (local demo only).' }
  $code = (& curl.exe -k -sS -o NUL -w '%{http_code}' https://localhost/health/live 2>$null | Out-String).Trim()
  Write-Host "Local HTTPS health status: $code"
}
function Stop-Demo {
  if (-not (Test-Path -LiteralPath $Config)) { Write-Host 'NOT STARTED'; return }
  if (Test-Path $ProcessesFile) {
    $tracked = Get-Content -LiteralPath $ProcessesFile -Raw | ConvertFrom-Json
    foreach ($item in $tracked) {
      $port = if ($item.Name -eq 'api') { 8801 } else { 443 }
      $listen = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($listen) {
        $listener = Get-CimInstance Win32_Process -Filter "ProcessId=$($listen.OwningProcess)" -ErrorAction SilentlyContinue
        if (-not $listener -or $listener.CommandLine -notlike "*$($item.Script)*") { throw "Refusing to stop unrelated process on port $port." }
        if ($item.Name -eq 'api' -and $listener.CommandLine -notlike "*$DataRoot*") { throw 'Refusing API listener because its demo data-root identity differs.' }
        Stop-Process -Id $listener.ProcessId -Force
      }
      # The original launcher PID is also stopped only when it still names the
      # exact script and start time recorded by this run.
      $launcher = Get-CimInstance Win32_Process -Filter "ProcessId=$($item.Pid)" -ErrorAction SilentlyContinue
      if ($launcher) {
        if ($launcher.CommandLine -notlike "*$($item.Script)*") { throw "Refusing changed launcher PID $($item.Pid)." }
        $start = (Get-Process -Id $item.Pid).StartTime.ToUniversalTime().ToString('o')
        if ($start -eq $item.StartUtc) { Stop-Process -Id $item.Pid -Force }
      }
    }
    Remove-Item -LiteralPath $ProcessesFile
  }
  Compose @('stop','db')
  Write-Host "Stopped task-owned local processes and demo database. Persistent volume $Volume was preserved."
}
function Open-Demo {
  $browser = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
  if (-not (Test-Path $browser)) { $browser = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' }
  if (-not (Test-Path $browser)) { throw 'Chrome or Edge was not found; open https://localhost/admin manually.' }
  $profile = Join-Path $DataRoot 'browser-profile'
  New-Item -ItemType Directory -Force $profile | Out-Null
  $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
  & icacls.exe $profile '/inheritance:r' '/grant:r' "*$sid`:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' | Out-Null
  Start-Process -FilePath $browser -ArgumentList @('--new-window',"--user-data-dir=$profile",'--no-first-run','--disable-sync','--ignore-certificate-errors','https://localhost/admin')
}

switch ($Action) {
  'Start' { Start-Demo }
  'Status' { Status-Demo }
  'Stop' { Stop-Demo }
  'Open' { Open-Demo }
}
