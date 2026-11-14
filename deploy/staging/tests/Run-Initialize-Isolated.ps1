$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$Id = [Guid]::NewGuid().ToString('N').Substring(0,12)
$Project = "rahgard-init-test-$Id"
$Volume = "rahgard-init-pg-$Id"
$RunDir = Join-Path $PSScriptRoot "..\.test-run\$Id"
$Secrets = Join-Path $RunDir 'secrets'
$Config = Join-Path $RunDir '.env'
$ConfigPosix = "/c/" + $Config.Substring(3).Replace('\','/')
$HostSecrets = 'C:/' + $Secrets.Substring(3).Replace('\','/')
$Compose = (Resolve-Path (Join-Path $PSScriptRoot '..\compose.yaml')).Path
$ComposePosix = "/c/" + $Compose.Substring(3).Replace('\','/')
$CreatedProject = $false

function Invoke-LocalPilotRequest([string]$Method,
    [string]$Path, [string]$HostName, [string]$Cookie = '', [string]$Csrf = '', [string]$Json = '') {
    $PayloadJson = (@{ method=$Method; path=$Path; host=$HostName; cookie=$Cookie; csrf=$Csrf; json=$Json } | ConvertTo-Json -Compress -Depth 5)
    $Probe = @'
import json,sys,httpx
p=json.load(sys.stdin)
h={'Host':p['host'],'Origin':'https://'+p['host'],'X-Forwarded-Proto':'https'}
if p.get('cookie'): h['Cookie']=p['cookie']
if p.get('csrf'): h['X-CSRF-Token']=p['csrf']
if p.get('json'): h['Content-Type']='application/json'
with httpx.Client(trust_env=False,timeout=10) as c:
 r=c.request(p['method'],'http://web:8080'+p['path'],headers=h,content=(p.get('json') or '').encode())
 print(json.dumps({'status':r.status_code,'body':r.text,'cookies':r.headers.get_list('set-cookie'),'headers':dict(r.headers)},separators=(',',':')))
'@
    $Raw = $PayloadJson | docker compose --env-file $script:Config -f $script:Compose exec -T api python -c $Probe
    if ($LASTEXITCODE -ne 0) { throw "Isolated in-network probe failed for $Method $Path." }
    $Response = ($Raw | Out-String).Trim() | ConvertFrom-Json
    $Headers = @{}
    foreach ($Header in $Response.headers.PSObject.Properties) { $Headers[$Header.Name.ToLowerInvariant()] = [string]$Header.Value }
    return [pscustomobject]@{ Status=[int]$Response.status; Body=[string]$Response.body; Cookies=@($Response.cookies); Headers=$Headers }
}
New-Item -ItemType Directory -Force -Path $Secrets | Out-Null
try {
    foreach ($Name in @('pg_owner_password','app_db_password','auth_otp_hmac_secret','auth_csrf_secret',
        'auth_rate_limit_secret','internal_chat_token','geo_authorizer_password','geo_publisher_password')) {
        [IO.File]::WriteAllText((Join-Path $Secrets $Name), 'isolated-test-only-' + [Guid]::NewGuid().ToString('N'))
    }
    @(
        "RAHGARD_PUBLIC_HOST=staging-$Id.example.test"
        "RAHGARD_COMPOSE_PROJECT=$Project"
        "RAHGARD_PG_VOLUME=$Volume"
        'RAHGARD_WEB_BIND_PORT=18081'
        'RAHGARD_CHAT_ENABLED=false'
        'RAHGARD_CHAT_MODEL=disabled-test'
        'RAHGARD_RELEASE_SHA=0123456789012345678901234567890123456789'
        "RAHGARD_SECRET_DIR=$HostSecrets"
        "RAHGARD_STATE_DIR=$HostSecrets/../state"
    ) | Set-Content -Encoding Ascii $Config
    $CreatedProject = $true
    docker compose --env-file $Config -f $Compose up -d db
    if ($LASTEXITCODE -ne 0) { throw 'Test-only PostGIS database container failed to start.' }
    $env:RAHGARD_DEPLOY_CONFIG = $ConfigPosix
    $env:RAHGARD_STATE_DIR = "/c/" + (Join-Path $RunDir 'state').Substring(3).Replace('\','/')
    $env:RAHGARD_SECRET_DIR = "/c/" + $Secrets.Substring(3).Replace('\','/')
    & 'C:\Program Files\Git\bin\bash.exe' -lc "cd /c/Projects/Ai_Tourism && ./deploy/staging/initialize-db.sh"
    if ($LASTEXITCODE -ne 0) { throw "Full isolated schema initialization failed with exit $LASTEXITCODE." }
    $Counts = docker compose --env-file $Config -f $Compose exec -T db psql -X -A -t -U ai_tourism_owner -d rahgard_pilot_vps_staging `
        -c "SELECT count(*)||':'||(SELECT count(*) FROM knowledge.production_destinations)||':'||(SELECT count(*) FROM system.schema_migrations WHERE migration_id IN ('0014_local_owner_login','0015_ai_provider_admin')) FROM system.schema_migrations;"
    if ($LASTEXITCODE -ne 0) { throw 'Could not verify the isolated migration ledger and empty production catalogue.' }
    if ($Counts.Trim() -ne '15:0:0') { throw "Unexpected staging counts (migrations:production:admin-migrations): $Counts" }
    docker compose --env-file $Config -f $Compose up -d --no-build --no-deps api
    $ApiWebStartExit = $LASTEXITCODE
    $ApiId = (docker compose --env-file $Config -f $Compose ps -a -q api | Out-String).Trim()
    if (-not $ApiId) { throw "API container was not created (Compose exit $ApiWebStartExit)." }
    $Ready = $false
    for ($i=0; $i -lt 60; $i++) {
        $ApiHealth = (& docker inspect $ApiId --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' 2>$null | Out-String).Trim()
        if ($ApiHealth -eq 'healthy') { $Ready = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $Ready) {
        Write-Output 'Diagnostic: isolated staging service status follows (test-owned project only).'
        docker compose --env-file $Config -f $Compose ps
        Write-Output 'Diagnostic: API startup log follows; this offline test has no traveler credentials.'
        docker compose --env-file $Config -f $Compose logs --no-color api
        Write-Output 'Diagnostic: API health-check state follows.'
        & docker inspect $ApiId --format '{{json .State.Health}}' 2>$null
        throw "API did not become healthy (API=$ApiHealth; Compose exit $ApiWebStartExit)."
    }
    docker compose --env-file $Config -f $Compose up -d --no-build --no-deps web
    if ($LASTEXITCODE -ne 0) { throw 'Could not start the isolated PWA container after the API became healthy.' }
    $WebId = (docker compose --env-file $Config -f $Compose ps -a -q web | Out-String).Trim()
    $WebReady = $false
    for ($i=0; $i -lt 30; $i++) {
        $WebHealth = (& docker inspect $WebId --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' 2>$null | Out-String).Trim()
        if ($WebHealth -eq 'healthy') { $WebReady = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $WebReady) { docker compose --env-file $Config -f $Compose logs --no-color web; throw "PWA did not become healthy (web=$WebHealth)." }
    $HostName = "staging-$Id.example.test"
        $Capability = Invoke-LocalPilotRequest 'GET' '/api/v1/auth/method' $HostName
        $CapabilityOk = ($Capability.Status -eq 200) -and ($Capability.Body -match 'staging_invite') -and
            ($Capability.Body -match 'unavailable') -and ($Capability.Headers['cache-control'] -match 'no-store')
        if (-not $CapabilityOk) {
            throw 'Staging authentication capability endpoint did not expose invitation login and unavailable SMS accurately.'
        }
        $InviteStderr = Join-Path $RunDir 'invite-stderr.log'
        $InviteCommand = "docker compose --env-file `"$Config`" -f `"$Compose`" run -T --rm --no-deps api python -m scripts.create_staging_invite --days 1 2>`"$InviteStderr`""
        $InviteOutput = & cmd.exe /d /c $InviteCommand
        $InviteExit = $LASTEXITCODE
        if ($InviteExit -ne 0) {
            $SafeErr = (Get-Content -Raw $InviteStderr) -replace '(?i)(password|token|secret)=\S+', '$1=[redacted]' -replace 'isolated-test-only-[A-Za-z0-9]+','[test-secret-redacted]'
            Write-Host $SafeErr
            throw "Could not create the test-only one-use invitation (exit $InviteExit)."
        }
        $InviteCode = ($InviteOutput | ForEach-Object { "$($_)" } | Where-Object { $_ -match '^[A-Za-z0-9_-]{40,}$' } | Select-Object -Last 1)
        if (-not $InviteCode) { throw 'The test-only invitation command returned no code.' }
        $Email = "traveler-$Id@example.test"
        $Password = "Staging-Only-$Id-Password!"
        $Redeemed = Invoke-LocalPilotRequest 'POST' '/api/v1/auth/staging/redeem' $HostName '' '' `
            (@{ invite_code=$InviteCode; email=$Email; password=$Password } | ConvertTo-Json -Compress)
        if ($Redeemed.Status -ne 200) { throw 'Invitation redemption did not issue a staging session.' }
        $Session = $Redeemed.Body | ConvertFrom-Json
        $CookieHeader = $Redeemed.Cookies | Where-Object { $_ -match '^__Host-rahgard_session=' } | Select-Object -First 1
        if (-not $CookieHeader -or $CookieHeader -notmatch ';\s*Secure') { throw 'Session cookie is missing the Secure host-only policy.' }
        $Cookie = ($CookieHeader -split ';',2)[0]
        $Me = Invoke-LocalPilotRequest 'GET' '/api/v1/auth/me' $HostName $Cookie
        if ($Me.Status -ne 200 -or ($Me.Body | ConvertFrom-Json).user.auth_method -ne 'staging_invite') {
            throw 'The staged session could not authenticate after invitation redemption.'
        }
        $Conversation = Invoke-LocalPilotRequest 'POST' '/api/v1/conversations' $HostName $Cookie $Session.csrf_token `
            (@{ locale='fa-IR'; request_text='test-only staging journey'; idempotency_key="staging-$Id-journey" } | ConvertTo-Json -Compress)
        if ($Conversation.Status -ne 201) { throw "Owner-scoped conversation persistence failed (HTTP $($Conversation.Status))." }
        $ConversationId = ($Conversation.Body | ConvertFrom-Json).conversation.conversation_id
        $WebPage = Invoke-LocalPilotRequest 'GET' '/' $HostName
        $WebPageOk = ($WebPage.Status -eq 200) -and ($WebPage.Body -match 'id="root"') -and
            $WebPage.Headers.ContainsKey('content-security-policy')
        if (-not $WebPageOk) { throw 'The real static PWA shell/security headers were not served.' }
        $Manifest = Invoke-LocalPilotRequest 'GET' '/manifest.webmanifest' $HostName
        $ManifestOk = ($Manifest.Status -eq 200) -and ($Manifest.Headers['content-type'] -match 'application/manifest\+json') -and
            ($Manifest.Headers['cache-control'] -match 'no-store') -and $Manifest.Headers.ContainsKey('x-content-type-options')
        if (-not $ManifestOk) { throw 'PWA manifest MIME, no-store, or security headers failed.' }
        $Worker = Invoke-LocalPilotRequest 'GET' '/sw.js' $HostName
        if ($Worker.Status -ne 200 -or $Worker.Headers['cache-control'] -notmatch 'no-store') {
            throw 'The service worker update cache policy failed.'
        }
        $Stop = docker compose --env-file $Config -f $Compose stop api
        if ($LASTEXITCODE -ne 0) { throw 'Could not stop the test API for restart persistence verification.' }
        docker compose --env-file $Config -f $Compose start api
        if ($LASTEXITCODE -ne 0) { throw 'Could not restart the test API.' }
        $ApiRestarted = $false
        for ($i=0; $i -lt 60; $i++) {
            $ApiHealth = (& docker inspect $ApiId --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' 2>$null | Out-String).Trim()
            if ($ApiHealth -eq 'healthy') { $ApiRestarted = $true; break }
            Start-Sleep -Seconds 2
        }
        if (-not $ApiRestarted) { docker compose --env-file $Config -f $Compose logs --no-color api; throw 'The restarted API did not become healthy.' }
        $Reopened = Invoke-LocalPilotRequest 'GET' "/api/v1/conversations/$ConversationId" $HostName $Cookie
        if ($Reopened.Status -ne 200 -or ($Reopened.Body | ConvertFrom-Json).conversation_id -ne $ConversationId) {
            throw "The persisted conversation could not be reopened after an API restart (HTTP $($Reopened.Status))."
        }
        Write-Output 'PASS: real Docker PWA/API/PostgreSQL staging flow, invitation session, SMS-unavailable response, conversation persistence and API restart reopen.'
    docker compose --env-file $Config -f $Compose stop api web db
    if ($LASTEXITCODE -ne 0) { throw 'Could not stop the isolated deployment before the database-volume restart check.' }
    docker compose --env-file $Config -f $Compose start db
    if ($LASTEXITCODE -ne 0) { throw 'Could not restart the isolated PostgreSQL container.' }
    $DbReady = $false
    for ($i=0; $i -lt 60; $i++) {
        docker compose --env-file $Config -f $Compose exec -T db pg_isready -U ai_tourism_owner -d rahgard_pilot_vps_staging *> $null
        if ($LASTEXITCODE -eq 0) { $DbReady = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $DbReady) { throw 'PostgreSQL did not recover from a container restart.' }
    $RestartCounts = docker compose --env-file $Config -f $Compose exec -T db psql -X -A -t -U ai_tourism_owner -d rahgard_pilot_vps_staging `
        -c "SELECT count(*)||':'||(SELECT count(*) FROM knowledge.production_destinations)||':'||(SELECT count(*) FROM conversation.conversations) FROM system.schema_migrations;"
    if ($LASTEXITCODE -ne 0 -or $RestartCounts.Trim() -ne '15:0:2') { throw "Persistent volume check failed: $RestartCounts" }
    Write-Output 'PASS: PostgreSQL container restart preserved the migration ledger, empty production view and one test conversation.'
    Write-Output 'PASS: all 15 selected staging migrations and empty production view verified on the task-owned temporary volume.'
}
finally {
    Remove-Item Env:RAHGARD_DEPLOY_CONFIG -ErrorAction SilentlyContinue
    Remove-Item Env:RAHGARD_STATE_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:RAHGARD_SECRET_DIR -ErrorAction SilentlyContinue
    if ($CreatedProject) {
        $PreviousPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        docker compose --env-file $Config -f $Compose down --volumes --remove-orphans 2>&1 | Out-Null
        $ErrorActionPreference = $PreviousPreference
    }
    if (Test-Path $RunDir) { Remove-Item -LiteralPath $RunDir -Recurse -Force }
}
