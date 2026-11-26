[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$image = 'rahgard-postgres:17-postgis36-vector087'
$suffix = [guid]::NewGuid().ToString('N').Substring(0,12)
$project = "rahgard-issue27-$suffix"
$container = "$project-db-1"
$scratch = Join-Path $env:TEMP "rahgard-027-$suffix"
$secrets = Join-Path $scratch 'secrets'
$marker = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N').Substring(0,16)
$created = $false

function New-RandomHex([int]$bytes) {
  $buffer = [byte[]]::new($bytes)
  $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
  [BitConverter]::ToString($buffer).Replace('-','').ToLowerInvariant()
}
function Assert-Docker([string]$step) {
  if ($LASTEXITCODE -ne 0) { throw "Isolated migration 0027 test failed at $step." }
}

try {
  & docker image inspect $image *> $null
  if ($LASTEXITCODE -ne 0) { throw 'Pinned local PG17 test image is unavailable; no image pull was attempted.' }
  if (& docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $container }) { throw 'Generated isolated container name collision.' }
  New-Item -ItemType Directory -Force -Path $secrets | Out-Null
  foreach ($name in @('pg_owner_password','app_db_password','geo_authorizer_password','geo_publisher_password')) {
    [IO.File]::WriteAllText((Join-Path $secrets $name),(New-RandomHex 32)+"`n",[Text.UTF8Encoding]::new($false))
  }
  $dockerArgs = @(
    'run','-d','--name',$container,'--network','none',
    '--label',"com.docker.compose.project=$project",'--label','com.docker.compose.service=db',
    '--tmpfs','/var/lib/postgresql/data:rw,noexec,nosuid,size=2g',
    '--tmpfs','/var/run/postgresql:rw,noexec,nosuid,size=16m',
    '--mount',"type=bind,source=$secrets,target=/run/secrets,readonly",
    '--env','POSTGRES_DB=rahgard_pilot_vps_staging','--env','POSTGRES_USER=ai_tourism_owner',
    '--env','POSTGRES_PASSWORD_FILE=/run/secrets/pg_owner_password',$image
  )
  & docker @dockerArgs *> $null
  Assert-Docker 'create'
  $created = $true
  $inspect = @(& docker inspect $container | ConvertFrom-Json)[0]
  $published = @($inspect.NetworkSettings.Ports.PSObject.Properties | Where-Object { $_.Value })
  if ($inspect.HostConfig.NetworkMode -ne 'none' -or $published.Count -gt 0) {
    throw 'Disposable database is not isolated from host/public networking.'
  }
  if (@($inspect.Mounts | Where-Object { $_.Type -eq 'volume' }).Count -gt 0) {
    throw 'Disposable database unexpectedly uses a named/persistent volume.'
  }
  $ready = $false
  for ($i=0; $i -lt 60; $i++) {
    & docker exec $container pg_isready -U ai_tourism_owner -d rahgard_pilot_vps_staging *> $null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
  }
  if (-not $ready) { throw 'Disposable PG17 did not become ready.' }

  $env:RAHGARD_DEMO_DB_CONTAINER = $container
  $env:RAHGARD_PILOT_DATABASE_MARKER = $marker
  Push-Location $root
  try {
    $priorPreference = $ErrorActionPreference
    $nativePriorPreference = $PSNativeCommandUseErrorActionPreference
    try {
      $ErrorActionPreference = 'Continue'
      $PSNativeCommandUseErrorActionPreference = $false
      $initializeOutput = @(& uv run python engineering/pilot/issue27-local-demo/initialize.py 2>&1 | ForEach-Object { $_.ToString() })
      $initializeExit = $LASTEXITCODE
    } finally {
      $ErrorActionPreference = $priorPreference
      $PSNativeCommandUseErrorActionPreference = $nativePriorPreference
    }
    foreach ($line in $initializeOutput) {
      if ($line -match '^(APPLY|PASS|BLOCKED):?') { Write-Output $line }
    }
    if ($initializeExit -ne 0) { throw 'Isolated database initialization failed; no details or credentials were emitted.' }
  }
  finally { Pop-Location }

  $ledger = (& docker exec $container psql -X -q -A -t -U ai_tourism_owner -d rahgard_pilot_vps_staging -c "SELECT count(*)||':'||max(migration_id) FROM system.schema_migrations") | Out-String
  Assert-Docker 'ledger-read'
  if ($ledger.Trim() -ne '26:0027_server_ai_provider_admin') { throw 'Isolated 0027 ledger is not exact.' }

  $sqlPath = Join-Path $PSScriptRoot '027_server_ai_provider_admin_rls.sql'
  Get-Content -LiteralPath $sqlPath -Raw | & docker exec -i $container psql -X -v ON_ERROR_STOP=1 -U ai_tourism_owner -d rahgard_pilot_vps_staging
  Assert-Docker 'RLS-and-step-up-acceptance'
  Write-Output 'PASS: disposable network-none PostgreSQL 17; clean migration chain through 0027; provider-admin row policies, step-up and runtime access verified.'
}
finally {
  Remove-Item Env:RAHGARD_DEMO_DB_CONTAINER -ErrorAction SilentlyContinue
  Remove-Item Env:RAHGARD_PILOT_DATABASE_MARKER -ErrorAction SilentlyContinue
  if ($created) { & docker rm -f $container *> $null }
  if (Test-Path -LiteralPath $scratch) { Remove-Item -LiteralPath $scratch -Recurse -Force }
}
