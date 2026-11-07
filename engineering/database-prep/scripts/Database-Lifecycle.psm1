Set-StrictMode -Version Latest

$script:Migration0006Ids = @(
    '0000_legacy_tourism_points_baseline',
    '0001_core_schema',
    '0002_synthetic_knowledge_seed',
    '0003_synthetic_e2e_seed',
    '0004_app_role_grants',
    '0005_verified_unesco_destination_seed',
    '0006_verified_unesco_destination_seed_batch2'
)
$script:Migration0007Ids = $script:Migration0006Ids + '0007_shiraz_dalahoo_wikipedia_dataset_v1'

function Resolve-DatabaseLifecycleState {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [string[]]$AppliedMigrationIds
    )

    $applied = @($AppliedMigrationIds | Sort-Object)
    $baseline = @($script:Migration0006Ids | Sort-Object)
    $shiraz = @($script:Migration0007Ids | Sort-Object)
    $appliedKey = $applied -join ','

    if ($appliedKey -ceq ($baseline -join ',')) {
        return [pscustomobject]@{
            Name = '0006'
            ExpectedRows = 419
            MigrationIds = $script:Migration0006Ids
            IncludesShiraz = $false
        }
    }

    if ($appliedKey -ceq ($shiraz -join ',')) {
        return [pscustomobject]@{
            Name = '0007'
            ExpectedRows = 695
            MigrationIds = $script:Migration0007Ids
            IncludesShiraz = $true
        }
    }

    throw "Unsupported or partial database migration ledger. Expected exactly baseline 0000 through 0006 or Shiraz-integrated 0000 through 0007; found: $appliedKey. No migration was applied."
}

function Resolve-DatabaseInitializationAction {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateSet('fresh', '0006', '0007')][string]$State,
        [switch]$ApplyPendingMigrationsToExistingDatabase
    )

    switch ($State) {
        'fresh' { return 'initialize-fresh' }
        '0007' { return 'already-integrated' }
        '0006' {
            if ($ApplyPendingMigrationsToExistingDatabase) { return 'apply-pending-0007' }
            throw 'Existing database is at Migration 0006 / 419 rows. Migration 0007 is pending and requires separate owner approval. To opt in after that approval, rerun with -ApplyPendingMigrationsToExistingDatabase. No database write was performed.'
        }
    }
}

Export-ModuleMember -Function Resolve-DatabaseLifecycleState, Resolve-DatabaseInitializationAction
