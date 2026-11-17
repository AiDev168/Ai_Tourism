Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-LocalPilotPaths([string]$DataRoot) {
    $repository = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
    $root = [IO.Path]::GetFullPath($DataRoot)
    if ($root.StartsWith('\\', [StringComparison]::OrdinalIgnoreCase) -or $root -notmatch '^[A-Za-z]:\\') {
        throw 'Local-first pilot storage must use a local drive, not a UNC, network share, or non-drive path.'
    }
    if ($root.Equals($repository, [StringComparison]::OrdinalIgnoreCase) -or
        $root.StartsWith($repository.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $repository.StartsWith($root.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Local pilot data root must be outside and separate from the repository.'
    }
    if ($root.Contains(',')) { throw 'Local pilot root cannot contain a Docker mount delimiter.' }
    $hash = [Security.Cryptography.SHA256]::Create()
    try { $rootHash = [BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($root.ToLowerInvariant()))).Replace('-', '').ToLowerInvariant() }
    finally { $hash.Dispose() }
    $token = $rootHash.Substring(0, 12)
    $repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
    return [pscustomobject]@{
        Root = $root; RootHash = $rootHash; State = Join-Path $root 'pilot-state.json'
        Db = Join-Path $root 'postgres-data'; Secrets = Join-Path $root 'secrets'
        Logs = Join-Path $root 'logs'; Backups = Join-Path $root 'backups'; ToolCache = Join-Path $root 'uv-cache'
        OwnerPassword = Join-Path $root 'secrets\postgres-owner-password'
        AppPassword = Join-Path $root 'secrets\app-password.dpapi'
        OwnerBootstrapPassword = Join-Path $root 'secrets\owner-bootstrap-password.dpapi'
        BackupPassword = Join-Path $root 'secrets\backup-password.dpapi'
        AppHmac = Join-Path $root 'secrets\auth-hmac.dpapi'
        AppCsrf = Join-Path $root 'secrets\auth-csrf.dpapi'
        AppRate = Join-Path $root 'secrets\auth-rate.dpapi'
        Pfx = Join-Path $root 'secrets\localhost.pfx'
        PfxCertificate = Join-Path $root 'secrets\localhost.cer'
        PfxPassword = Join-Path $root 'secrets\localhost-pfx-password.dpapi'
        DatabaseCertificate = Join-Path $root 'secrets\postgres-root.crt'
        GeoAuthorizerPassword = Join-Path $root 'secrets\geo-authorizer-password.dpapi'
        GeoPublisherPassword = Join-Path $root 'secrets\geo-publisher-password.dpapi'
        GeoMigratorPassword = Join-Path $root 'secrets\geo-migrator-password.dpapi'
        RepoRoot = $repoRoot
        SqlDirectory = Join-Path $repoRoot 'engineering\database-prep\sql'
        LegacySql = Join-Path $repoRoot 'database\tourism_points.sql'
        PilotSql = Join-Path $repoRoot 'engineering\pilot\sql'
        GeoBatch = Join-Path $repoRoot 'engineering\pilot\geo-visibility-approved-localpilot-2026-11-11.json'
        Container = "rahgard-local-pg17-$token"; Database = 'rahgard_pilot_local'
        Image = 'ai-tourism-postgres:17-postgis36-vector087'
    }
}

function Assert-NoReparsePath([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    $cursor = $full
    while ($cursor) {
        try { $attributes = [IO.File]::GetAttributes($cursor) }
        catch [IO.FileNotFoundException] { $attributes = $null }
        catch [IO.DirectoryNotFoundException] { $attributes = $null }
        if ($null -ne $attributes -and ($attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'Local pilot storage includes a reparse point or junction.'
        }
        $parent = [IO.Directory]::GetParent($cursor)
        if (-not $parent) { break }
        $cursor = $parent.FullName
    }
}

function Set-LocalPilotAcl([string]$Path, [switch]$Directory) {
    $guardPath = if ($Directory) { $Path } else { [IO.Directory]::GetParent([IO.Path]::GetFullPath($Path)).FullName }
    Assert-NoReparsePath $guardPath
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
    # Construct a DACL-only descriptor. Get-Acl/Set-Acl round-trips audit
    # metadata on some Windows hosts and can require SeSecurityPrivilege,
    # which this least-privilege local pilot must not request.
    $acl = if ($Directory) { New-Object Security.AccessControl.DirectorySecurity }
           else { New-Object Security.AccessControl.FileSecurity }
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($sidText in @($sid.Value, 'S-1-5-18')) {
        $identity = [Security.Principal.SecurityIdentifier]::new($sidText)
        $inheritance = if ($Directory) { [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit } else { [Security.AccessControl.InheritanceFlags]::None }
        $rule = [Security.AccessControl.FileSystemAccessRule]::new(
            $identity, [Security.AccessControl.FileSystemRights]::FullControl,
            $inheritance, [Security.AccessControl.PropagationFlags]::None,
            [Security.AccessControl.AccessControlType]::Allow)
        [void]$acl.AddAccessRule($rule)
    }
    $acl.SetOwner($sid)
    if ($Directory) { [IO.Directory]::SetAccessControl($Path,$acl) }
    else { [IO.File]::SetAccessControl($Path,$acl) }
    Assert-LocalPilotAcl $Path -Directory:$Directory -Protected
}

function Assert-LocalPilotAcl([string]$Path, [switch]$Directory, [switch]$Protected) {
    $guardPath = if ($Directory) { $Path } else { [IO.Directory]::GetParent([IO.Path]::GetFullPath($Path)).FullName }
    Assert-NoReparsePath $guardPath
    $acl = if ($Directory) { [IO.Directory]::GetAccessControl($Path) } else { [IO.File]::GetAccessControl($Path) }
    $currentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    if (($Protected -and -not $acl.AreAccessRulesProtected) -or
        $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $currentSid) {
        throw 'Local pilot NTFS owner or DACL inheritance is unsafe.'
    }
    $allowed = @($currentSid, 'S-1-5-18')
    $expectedInheritance = if ($Directory) {
        [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit
    } else { [Security.AccessControl.InheritanceFlags]::None }
    $entries = @($acl.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier]))
    if (-not $entries.Count) { throw 'Local pilot path has no explicit ACL entries.' }
    foreach ($entry in $entries) {
        if ($entry.IdentityReference.Value -notin $allowed -or
            $entry.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
            $entry.IsInherited -or
            $entry.InheritanceFlags -ne $expectedInheritance -or
            $entry.PropagationFlags -ne [Security.AccessControl.PropagationFlags]::None -or
            $entry.FileSystemRights -ne [Security.AccessControl.FileSystemRights]::FullControl) {
            throw 'Local pilot NTFS ACL contains an inherited, broad, or unexpected access rule.'
        }
    }
    foreach ($required in $allowed) {
        if (-not ($entries | Where-Object { $_.IdentityReference.Value -eq $required -and $_.FileSystemRights -band [Security.AccessControl.FileSystemRights]::FullControl })) {
            throw 'Local pilot NTFS ACL is missing an approved full-control identity.'
        }
    }
}

function Initialize-LocalPilotRoot($Paths) {
    if (Test-Path -LiteralPath $Paths.Root) {
        Assert-NoReparsePath $Paths.Root
        if (-not (Test-Path -LiteralPath $Paths.State)) {
            throw 'Data root already exists without a matching pilot state file; refusing to alter user-owned contents or ACLs.'
        }
        Assert-LocalPilotAcl $Paths.Root -Directory
        foreach ($directory in @($Paths.Db, $Paths.Secrets, $Paths.Logs, $Paths.Backups, $Paths.ToolCache)) {
            if (-not (Test-Path -LiteralPath $directory)) { throw 'A directory recorded by pilot state is missing.' }
            Assert-LocalPilotAcl $directory -Directory
        }
        foreach ($file in @($Paths.State, $Paths.OwnerPassword, $Paths.AppPassword, $Paths.AppHmac,
                            $Paths.AppCsrf, $Paths.AppRate, $Paths.Pfx, $Paths.PfxPassword,
                            $Paths.PfxCertificate, $Paths.DatabaseCertificate, $Paths.OwnerBootstrapPassword,
                            $Paths.BackupPassword, $Paths.GeoAuthorizerPassword, $Paths.GeoPublisherPassword,
                            $Paths.GeoMigratorPassword)) {
            if (Test-Path -LiteralPath $file) { Assert-LocalPilotAcl $file }
        }
        return
    } else {
        $parent = Split-Path -Parent $Paths.Root
        if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
        New-Item -ItemType Directory -Path $Paths.Root | Out-Null
    }
    Set-LocalPilotAcl $Paths.Root -Directory
    foreach ($directory in @($Paths.Db, $Paths.Secrets, $Paths.Logs, $Paths.Backups, $Paths.ToolCache)) {
        if (-not (Test-Path -LiteralPath $directory)) { New-Item -ItemType Directory -Path $directory | Out-Null }
        Assert-NoReparsePath $directory
        Set-LocalPilotAcl $directory -Directory
    }
}

function New-LocalPilotRandomHex([int]$Bytes = 32) {
    $raw = New-Object byte[] $Bytes
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($raw) } finally { $rng.Dispose() }
    return [BitConverter]::ToString($raw).Replace('-', '').ToLowerInvariant()
}

function Save-LocalPilotSecret([string]$Path, [string]$Value) {
    $secure = ConvertTo-SecureString -String $Value -AsPlainText -Force
    $encoded = ConvertFrom-SecureString -SecureString $secure
    [IO.File]::WriteAllText($Path, $encoded, [Text.Encoding]::ASCII)
    Set-LocalPilotAcl $Path
}

function Read-LocalPilotSecret([string]$Path) {
    Assert-LocalPilotAcl $Path
    $secure = ConvertTo-SecureString -String ([IO.File]::ReadAllText($Path, [Text.Encoding]::ASCII))
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

function Read-LocalPilotState($Paths) {
    if (-not [IO.File]::Exists($Paths.State)) { return $null }
    Assert-LocalPilotAcl $Paths.State
    try { $state = Get-Content -LiteralPath $Paths.State -Raw -Encoding UTF8 | ConvertFrom-Json }
    catch { throw 'Local pilot state file is unreadable or malformed.' }
    if ($state.schema -ne 'rahgard.local-pilot.v1' -or
        [IO.Path]::GetFullPath([string]$state.data_root) -ne $Paths.Root -or
        $state.root_sha256 -ne $Paths.RootHash -or $state.container_name -ne $Paths.Container -or
        $state.database -ne $Paths.Database -or $state.bind_mount -ne $Paths.Db) {
        throw 'Local pilot state identity does not match the selected private data root.'
    }
    return $state
}

function Write-LocalPilotState($Paths, $State) {
    $temporary = $Paths.State + '.new'
    if (Test-Path -LiteralPath $temporary) {
        Assert-LocalPilotAcl $temporary
        try { $staged = Get-Content -LiteralPath $temporary -Raw -Encoding UTF8 | ConvertFrom-Json }
        catch { throw 'A preserved pilot state checkpoint is malformed; leaving it and the active state unchanged.' }
        $identityMatches = $staged.schema -eq 'rahgard.local-pilot.v1' -and
            [IO.Path]::GetFullPath([string]$staged.data_root) -eq $Paths.Root -and
            $staged.root_sha256 -eq $Paths.RootHash -and $staged.container_name -eq $Paths.Container -and
            $staged.database -eq $Paths.Database -and $staged.bind_mount -eq $Paths.Db
        $fields = @('lifecycle','database_port','api_port','https_port','marker','migration_count',
            'migration_0012_sha256','migration_0013_sha256','migration_0014_sha256','migration_0015_sha256','geo_packet_sha256',
            'https_thumbprint','database_certificate_sha256','configuration_sha256','pwa_build_sha256')
        $mismatches = @()
        foreach ($field in $fields) {
            if ([string]$staged.$field -cne [string]$State.$field) { $mismatches += $field }
        }
        if (-not $identityMatches) {
            throw 'Preserved pilot state checkpoint conflicts with the requested state update; neither file was overwritten.'
        }
        if ($mismatches.Count -and @($mismatches | Where-Object { $_ -notin @('configuration_sha256','pwa_build_sha256') }).Count) {
            throw 'Preserved pilot state checkpoint conflicts with database or approval identity; neither file was overwritten.'
        }
        if ($mismatches.Count) {
            $superseded = $temporary + '.superseded'
            if (Test-Path -LiteralPath $superseded) { throw 'A superseded state checkpoint already exists; preserving all state files.' }
            Move-Item -LiteralPath $temporary -Destination $superseded
            Assert-LocalPilotAcl $superseded
            [IO.File]::WriteAllText($temporary, ($State | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
            Set-LocalPilotAcl $temporary
        }
    } else {
        [IO.File]::WriteAllText($temporary, ($State | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
        Set-LocalPilotAcl $temporary
    }
    if (Test-Path -LiteralPath $Paths.State) {
        Assert-LocalPilotAcl $Paths.State
        $backup = $temporary + '.previous'
        if (Test-Path -LiteralPath $backup) { throw 'A prior state-replacement backup exists; preserving all state files for review.' }
        [IO.File]::Replace($temporary, $Paths.State, $backup)
        Assert-LocalPilotAcl $backup
        Remove-Item -LiteralPath $backup -Force
    } else {
        Move-Item -LiteralPath $temporary -Destination $Paths.State
    }
    Assert-LocalPilotAcl $Paths.State
}

function Get-LocalPilotContainer($Paths) {
    $null = & docker info --format '{{.ID}}' 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Docker daemon is unavailable; refusing to create or alter resources.' }
    $ids = @(& docker container ls --all --quiet --filter "name=^/$($Paths.Container)$" 2>$null)
    if ($LASTEXITCODE -ne 0) { throw 'Docker could not enumerate the exact local-pilot container identity.' }
    if ($ids.Count -eq 0) { return $null }
    if ($ids.Count -ne 1) { throw 'Multiple Docker containers match the exact local-pilot identity.' }
    $raw = & docker inspect $Paths.Container 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Docker could not inspect the exact local-pilot container.' }
    try { $container = @($raw | ConvertFrom-Json)[0] } catch { throw 'Local pilot Docker metadata is malformed.' }
    if ($container.Name -ne "/$($Paths.Container)" -or
        $container.Config.Labels.'rahgard.local-pilot' -ne 'true' -or
        $container.Config.Labels.'rahgard.local-pilot-root' -ne $Paths.RootHash -or
        $container.Config.Image -ne $Paths.Image) {
        throw 'A Docker container name conflict exists; refusing to inspect or alter another resource.'
    }
    if ($container.HostConfig.RestartPolicy.Name -ne 'unless-stopped') {
        throw 'Persistent PostgreSQL restart policy differs from the approved local-pilot setting.'
    }
    if ($container.HostConfig.AutoRemove -ne $false) {
        throw 'Persistent PostgreSQL container must not be auto-removed.'
    }
    $expectedMounts = @(
        @{Source=$Paths.Db; Destination='/var/lib/postgresql/data'; ReadWrite=$true},
        @{Source=$Paths.SqlDirectory; Destination='/opt/rahgard/sql'; ReadWrite=$false},
        @{Source=$Paths.LegacySql; Destination='/opt/rahgard/legacy/tourism_points.sql'; ReadWrite=$false},
        @{Source=$Paths.PilotSql; Destination='/opt/rahgard/pilot-sql'; ReadWrite=$false},
        @{Source=$Paths.GeoBatch; Destination='/opt/rahgard/pilot/geo-visibility-approved-localpilot-2026-11-11.json'; ReadWrite=$false},
        @{Source=$Paths.OwnerPassword; Destination='/run/secrets/postgres-owner-password'; ReadWrite=$false}
    )
    $actualMounts = @($container.Mounts)
    if ($actualMounts.Count -ne $expectedMounts.Count) { throw 'Persistent container has unexpected bind mount count.' }
    foreach ($expected in $expectedMounts) {
        $mount = @($actualMounts | Where-Object { $_.Destination -eq $expected.Destination })
        if ($mount.Count -ne 1 -or $mount[0].Type -ne 'bind' -or
            -not [string]::Equals([IO.Path]::GetFullPath($mount[0].Source),[IO.Path]::GetFullPath($expected.Source),[StringComparison]::OrdinalIgnoreCase) -or
            [bool]$mount[0].RW -ne [bool]$expected.ReadWrite) {
            throw 'Persistent container bind mount source, destination, or access mode differs from its reviewed identity.'
        }
    }
    $publishedKeys = @($container.HostConfig.PortBindings.PSObject.Properties.Name)
    $port = @($container.HostConfig.PortBindings.'5432/tcp')
    if ($publishedKeys.Count -ne 1 -or $publishedKeys[0] -ne '5432/tcp' -or
        $port.Count -ne 1 -or $port[0].HostIp -ne '127.0.0.1' -or
        [int]$port[0].HostPort -eq 55433) {
        throw 'PostgreSQL must be bound to one loopback port other than 55433.'
    }
    return $container
}

function Assert-LocalPilotTools($Paths) {
    foreach ($name in @('docker','uv','node','npm')) {
        if (-not (Get-Command $name -ErrorAction SilentlyContinue)) { throw "Required local tool is unavailable: $name" }
    }
    $image = (& docker image inspect --format '{{.Id}}' $Paths.Image 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $image) { throw 'Required PostgreSQL 17/PostGIS/pgvector image is not already present; this command does not pull or build images.' }
    return $image
}

Export-ModuleMember -Function *-LocalPilot*, Assert-LocalPilotAcl, Assert-NoReparsePath
