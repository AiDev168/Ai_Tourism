[CmdletBinding()]
param(
    [ValidateRange(0, 65535)][int]$HttpsPort = 0,
    [ValidateRange(0, 65535)][int]$ApiPort = 0
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$BackendRoot = Join-Path $ProjectRoot 'backend'
$FrontendRoot = Join-Path $ProjectRoot 'frontend'
$DatabaseRunner = Join-Path $ProjectRoot 'engineering\database-prep\scripts\Start-Disposable-Mvp-E2E.ps1'
$ProxyScript = Join-Path $PSScriptRoot 'local_https_proxy.mjs'

if (-not (Test-Path -LiteralPath $DatabaseRunner) -or -not (Test-Path -LiteralPath $ProxyScript)) {
    throw 'Issue 6 pilot inputs are incomplete.'
}
if (Test-Path -LiteralPath (Join-Path $BackendRoot '.env')) {
    throw 'Refusing to start because backend/.env exists. This runner never reads dotenv files.'
}
if ($HttpsPort -eq 55433 -or $ApiPort -eq 55433) { throw 'Shared port 55433 is forbidden.' }

function Get-FreeLoopbackPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    try { $listener.Start(); return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port }
    finally { $listener.Stop() }
}
if ($ApiPort -eq 0) { $ApiPort = Get-FreeLoopbackPort }
if ($HttpsPort -eq 0) { $HttpsPort = Get-FreeLoopbackPort }
if ($HttpsPort -eq $ApiPort) { $HttpsPort = Get-FreeLoopbackPort }

function New-HexValue([int]$Length) {
    $bytes = New-Object byte[] $Length
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    [BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
}

function Restore-PilotEnvironment {
    foreach ($name in $ManagedEnvironmentNames) {
        if ($OriginalManagedEnvironment.ContainsKey($name)) {
            Set-Item -LiteralPath "Env:$name" -Value $OriginalManagedEnvironment[$name]
        }
        else { Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue }
    }
}

function Start-IsolatedProcess(
    [string]$FileName,
    [string[]]$Arguments,
    [string]$WorkingDirectory,
    [hashtable]$ChildEnvironment,
    [string]$StdoutPath,
    [string]$StderrPath
) {
    # Start-Process uses ordinary file redirection (no .NET async output event
    # threads), while this function temporarily exposes only the task-specific
    # configuration to that child and restores the caller's environment.
    $processEnvironmentNames = @($ManagedEnvironmentNames) + @(
        'SMS_IR_SANDBOX_API_KEY','AUTH_OTP_HMAC_SECRET','AUTH_CSRF_SECRET',
        'AUTH_RATE_LIMIT_SECRET','DATABASE_URL'
    )
    $snapshot = @{}
    foreach ($name in $processEnvironmentNames) {
        $item = Get-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
        if ($item) { $snapshot[$name] = [string]$item.Value }
    }
    try {
        foreach ($name in $processEnvironmentNames) {
            if ($ChildEnvironment.ContainsKey($name)) {
                Set-Item -LiteralPath "Env:$name" -Value ([string]$ChildEnvironment[$name])
            }
            else { Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue }
        }
        return Start-Process -FilePath $FileName -ArgumentList $Arguments `
            -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $StdoutPath -RedirectStandardError $StderrPath
    }
    finally {
        foreach ($name in $processEnvironmentNames) {
            if ($snapshot.ContainsKey($name)) {
                Set-Item -LiteralPath "Env:$name" -Value $snapshot[$name]
            }
            else { Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue }
        }
    }
}

function Get-OwnedListenerPid([int]$Port, [System.Diagnostics.Process]$Parent, [string]$CommandPattern) {
    $listeners = @(Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1 -LocalPort $Port -ErrorAction SilentlyContinue)
    foreach ($listener in $listeners) {
        $pidValue = [int]$listener.OwningProcess
        if ($pidValue -eq $Parent.Id) { return $pidValue }
        $child = Get-CimInstance Win32_Process -Filter "ProcessId = $pidValue" -ErrorAction SilentlyContinue
        if ($child -and [int]$child.ParentProcessId -eq $Parent.Id -and $child.CommandLine -match $CommandPattern) {
            return $pidValue
        }
    }
    return $null
}

$ManagedEnvironmentNames = @(
        'APP_ENV','APP_HOST','APP_PORT','LOG_LEVEL','DATABASE_HOST','DATABASE_PORT',
        'DATABASE_NAME','DATABASE_USER','DATABASE_PASSWORD','AUTH_ENABLED','AUTH_SMS_ADAPTER',
        'AUTH_COOKIE_SECURE','AUTH_ALLOWED_ORIGINS','TOURISM_RAG_ENABLED','TOURISM_RAG_API_URL',
        'TOURISM_RAG_API_TOKEN','INTERNAL_CHAT_ENABLED','INTERNAL_CHAT_ENDPOINT',
        'INTERNAL_CHAT_MODEL','INTERNAL_CHAT_TOKEN','PILOT_HTTPS_PORT','PILOT_API_PORT',
        'PILOT_FRONTEND_DIST','PILOT_TLS_PFX','PILOT_TLS_PFX_PASSWORD',
        'AUTH_INTEGRATION_TESTS','AUTH_TEST_DATABASE_HOST','AUTH_TEST_DATABASE_PORT',
        'AUTH_TEST_DATABASE_NAME','AUTH_TEST_DATABASE_USER','AUTH_TEST_DATABASE_PASSWORD',
        'AUTH_TEST_DATABASE_OWNER_PASSWORD','AUTH_TEST_DATABASE_MARKER','AI_TOURISM_MVP_E2E_CONTAINER'
)
$OriginalManagedEnvironment = @{}
foreach ($name in $ManagedEnvironmentNames) {
    $item = Get-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
    if ($item) { $OriginalManagedEnvironment[$name] = [string]$item.Value }
}

$tag = [Guid]::NewGuid().ToString('N')
$runtime = Join-Path ([IO.Path]::GetTempPath()) "rahgard-issue6-pilot-$tag"
New-Item -ItemType Directory -Path $runtime | Out-Null
$statePath = Join-Path $runtime 'state.json'
$pfxPath = Join-Path $runtime 'localhost.pfx'
$apiLog = Join-Path $runtime 'api.log'
$apiErrorLog = Join-Path $runtime 'api-error.log'
$proxyLog = Join-Path $runtime 'proxy.log'
$proxyErrorLog = Join-Path $runtime 'proxy-error.log'
$apiProcess = $null
$proxyProcess = $null
$databaseContainer = $null
$databaseReady = $false

try {
    # Vite build output only; the frontend is served on the same HTTPS origin
    # and authenticated API responses retain the backend's no-store behavior.
    Push-Location $FrontendRoot
    try {
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend production build failed.' }
    }
    finally { Pop-Location }

    # This existing runner creates a fresh tmpfs PostgreSQL 17 instance, creates
    # least-privilege ai_tourism_app, applies migrations through 0012, and sets
    # an explicit test marker. It never attaches the shared volume or port.
    & $DatabaseRunner -ProjectRoot $ProjectRoot
    $databaseContainer = $env:AI_TOURISM_MVP_E2E_CONTAINER
    if (-not $databaseContainer -or $env:AUTH_TEST_DATABASE_MARKER -eq '') {
        throw 'Guarded disposable database did not provide a verified marker.'
    }
    $databaseReady = $true

    # A short-lived self-signed localhost certificate is generated in memory and
    # written only to this task-owned temp directory. It is not a deployable CA.
    $rsa = [System.Security.Cryptography.RSA]::Create(2048)
    $request = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new(
        'CN=localhost', $rsa,
        [System.Security.Cryptography.HashAlgorithmName]::SHA256,
        [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
    )
    $san = [System.Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
    $san.AddDnsName('localhost')
    $san.AddIpAddress([System.Net.IPAddress]::Loopback)
    $request.CertificateExtensions.Add($san.Build())
    $keyUsage = [System.Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new(
        [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature -bor
        [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyEncipherment,
        $false
    )
    $request.CertificateExtensions.Add($keyUsage)
    $certificate = $request.CreateSelfSigned(
        [DateTimeOffset]::UtcNow.AddMinutes(-5), [DateTimeOffset]::UtcNow.AddHours(8)
    )
    $pfxPassword = New-HexValue 24
    [IO.File]::WriteAllBytes(
        $pfxPath,
        $certificate.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Pfx, $pfxPassword)
    )
    $certificate.Dispose(); $rsa.Dispose()

    $databaseName = [string]$env:AUTH_TEST_DATABASE_NAME
    $databasePort = [string]$env:AUTH_TEST_DATABASE_PORT
    $apiEnvironment = @{
        APP_ENV = 'development'; APP_HOST = '127.0.0.1'; APP_PORT = [string]$ApiPort; LOG_LEVEL = 'INFO'
        DATABASE_HOST = '127.0.0.1'; DATABASE_PORT = $databasePort; DATABASE_NAME = $databaseName
        DATABASE_USER = 'ai_tourism_app'; DATABASE_PASSWORD = [string]$env:AUTH_TEST_DATABASE_PASSWORD
        AUTH_ENABLED = 'false'; AUTH_SMS_ADAPTER = 'disabled'; AUTH_COOKIE_SECURE = 'true'
        AUTH_ALLOWED_ORIGINS = "https://localhost:$HttpsPort"; TOURISM_RAG_ENABLED = 'false'
        INTERNAL_CHAT_ENABLED = 'false'; PYTHONUTF8 = '1'; PYTHONDONTWRITEBYTECODE = '1'
    }
    $python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw 'Repository virtual-environment Python is missing.' }
    $apiProcess = Start-IsolatedProcess -FileName $python `
        -Arguments @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',[string]$ApiPort,'--no-access-log') `
        -WorkingDirectory $BackendRoot -ChildEnvironment $apiEnvironment `
        -StdoutPath $apiLog -StderrPath $apiErrorLog

    $nodeEnvironment = @{
        PILOT_HTTPS_PORT = [string]$HttpsPort; PILOT_API_PORT = [string]$ApiPort
        PILOT_FRONTEND_DIST = (Join-Path $FrontendRoot 'dist')
        PILOT_TLS_PFX = $pfxPath; PILOT_TLS_PFX_PASSWORD = $pfxPassword
    }
    $node = (Get-Command node -ErrorAction Stop).Source
    $proxyProcess = Start-IsolatedProcess -FileName $node -Arguments @($ProxyScript) `
        -WorkingDirectory $ProjectRoot -ChildEnvironment $nodeEnvironment `
        -StdoutPath $proxyLog -StderrPath $proxyErrorLog

    $backendReady = $false
    $httpsReady = $false
    $apiListenerPid = $null
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        $apiListenerPid = Get-OwnedListenerPid -Port $ApiPort -Parent $apiProcess `
            -CommandPattern ([regex]::Escape("uvicorn app.main:app --host 127.0.0.1 --port $ApiPort"))
        if (-not $apiProcess.HasExited -and $apiListenerPid) {
            $previousPreference = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            $probe = & curl.exe --silent --show-error --fail "http://127.0.0.1:$ApiPort/health/ready" 2>$null
            $probeExit = $LASTEXITCODE
            $ErrorActionPreference = $previousPreference
            if ($probeExit -eq 0 -and ($probe | Out-String) -match '"status"\s*:\s*"ready"') {
                $backendReady = $true
            }
        }
        $proxyListenerPid = Get-OwnedListenerPid -Port $HttpsPort -Parent $proxyProcess `
            -CommandPattern ([regex]::Escape($ProxyScript))
        if (-not $proxyProcess.HasExited -and $proxyListenerPid -eq $proxyProcess.Id) {
            $previousPreference = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            $probe = & curl.exe --silent --show-error --insecure --fail "https://localhost:$HttpsPort/health/ready" 2>$null
            $probeExit = $LASTEXITCODE
            $ErrorActionPreference = $previousPreference
            if ($probeExit -eq 0 -and ($probe | Out-String) -match '"status"\s*:\s*"ready"') {
                $httpsReady = $true
            }
        }
        if ($backendReady -and $httpsReady) { break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $backendReady -or -not $httpsReady) {
        throw 'Pilot smoke failed. Inspect task-local api.log/proxy.log before stopping.'
    }

    $shellProbePath = Join-Path $runtime 'shell.html'
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & curl.exe --silent --show-error --insecure --fail "https://localhost:$HttpsPort/" --output $shellProbePath
    $shellExit = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    if ($shellExit -ne 0 -or -not (Select-String -LiteralPath $shellProbePath -Pattern '<div id="root"></div>' -Quiet)) {
        throw 'HTTPS PWA shell could not be served from the built Vite bundle.'
    }
    $catalogResponse = & curl.exe --silent --show-error --insecure --fail `
        "https://localhost:$HttpsPort/api/v1/catalog/destinations"
    if ($LASTEXITCODE -ne 0) { throw 'HTTPS API proxy did not return the catalogue response.' }
    $catalog = ($catalogResponse | Out-String) | ConvertFrom-Json
    if ($catalog.count -ne 0) { throw 'Expected the disposable production catalogue to remain empty.' }

    $state = [ordered]@{
        purpose = 'internal-loopback-only-test'
        created_at_utc = [DateTime]::UtcNow.ToString('o')
        https_url = "https://localhost:$HttpsPort/"
        api_port = $ApiPort
        https_port = $HttpsPort
        api_pid = $apiProcess.Id
        api_start_utc = $apiProcess.StartTime.ToUniversalTime().ToString('o')
        api_listener_pid = [int]$apiListenerPid
        api_listener_start_utc = (Get-Process -Id ([int]$apiListenerPid)).StartTime.ToUniversalTime().ToString('o')
        proxy_pid = $proxyProcess.Id
        proxy_start_utc = $proxyProcess.StartTime.ToUniversalTime().ToString('o')
        database_container = $databaseContainer
        database_name = $databaseName
        database_port = [int]$databasePort
        tls_certificate = $pfxPath
        runtime_directory = $runtime
        logs = @($apiLog, $apiErrorLog, $proxyLog, $proxyErrorLog)
        auth_enabled = $false
        chat_enabled = $false
        rag_enabled = $false
        migrations = '0000-0012'
    }
    $state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statePath -Encoding UTF8
    Write-Output "READY: internal loopback pilot at $($state.https_url)"
    Write-Output "STATE: $statePath"
    Write-Output 'Authentication, remote Chat, and owner RAG are disabled; production content approval is unchanged.'
    Write-Output 'Use Stop-Issue6-LocalPilot.ps1 with the STATE path to stop only these task-created processes/container.'
    Restore-PilotEnvironment
}
catch {
    if ($proxyProcess -and -not $proxyProcess.HasExited) { Stop-Process -Id $proxyProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($apiProcess) {
        $orphanListener = Get-OwnedListenerPid -Port $ApiPort -Parent $apiProcess `
            -CommandPattern ([regex]::Escape("uvicorn app.main:app --host 127.0.0.1 --port $ApiPort"))
        if ($orphanListener -and $orphanListener -ne $apiProcess.Id) {
            Stop-Process -Id ([int]$orphanListener) -Force -ErrorAction SilentlyContinue
        }
        if (-not $apiProcess.HasExited) { Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue }
    }
    if ($databaseReady -and $databaseContainer) {
        $existingNames = @(& docker container ls --all --format '{{.Names}}')
        if ($LASTEXITCODE -ne 0) { throw 'Could not inspect Docker names during startup cleanup.' }
        if ($existingNames -contains [string]$databaseContainer) {
            $inspection = & docker inspect $databaseContainer
            if ($LASTEXITCODE -ne 0) { throw 'Could not verify the startup-failure database container.' }
            $metadata = ($inspection | Out-String) | ConvertFrom-Json
            if ($databaseContainer -notmatch '^ai-tourism-mvp-pg17-[a-f0-9]{12}$' -or
                $metadata[0].Name -ne "/$databaseContainer" -or
                $metadata[0].Config.Labels.'ai-tourism.disposable-mvp-e2e' -ne 'true') {
                throw 'Refusing startup-failure cleanup for an unverified database container.'
            }
            & docker stop $databaseContainer | Out-Null
            $remaining = & docker inspect $databaseContainer 2>$null
            if ($LASTEXITCODE -eq 0) {
                $remainingMetadata = ($remaining | Out-String) | ConvertFrom-Json
                if ($remainingMetadata[0].Name -ne "/$databaseContainer" -or
                    $remainingMetadata[0].Config.Labels.'ai-tourism.disposable-mvp-e2e' -ne 'true') {
                    throw 'Refusing explicit startup-failure container removal after identity changed.'
                }
                & docker rm $databaseContainer | Out-Null
            }
        }
    }
    $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    $runtimeFull = [IO.Path]::GetFullPath($runtime)
    if ($runtimeFull.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -and
        $runtimeFull -match 'rahgard-issue6-pilot-[0-9a-f]{32}$' -and
        (Test-Path -LiteralPath $runtimeFull)) {
        Remove-Item -LiteralPath (Join-Path $runtimeFull 'localhost.pfx') -Force -ErrorAction SilentlyContinue
        Write-Output "FAILED: safe diagnostics retained at $runtimeFull (API/proxy logs and shell probe only)."
    }
    Restore-PilotEnvironment
    throw
}
