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
$script:Migration0008Ids = $script:Migration0006Ids + '0008_authentication_foundation'
$script:Migration0007And0008Ids = $script:Migration0007Ids + '0008_authentication_foundation'
$script:Migration0006AuthTravelerIds = $script:Migration0008Ids + '0009_traveler_core'
$script:Migration0007AuthTravelerIds = $script:Migration0007And0008Ids + '0009_traveler_core'
$script:Migration0006AuthTask31Ids = $script:Migration0006AuthTravelerIds + '0010_task31_content_privacy_full_itinerary'
$script:Migration0007AuthTask31Ids = $script:Migration0007AuthTravelerIds + '0010_task31_content_privacy_full_itinerary'
$script:Migration0006ChatIds = $script:Migration0006AuthTask31Ids + '0011_internal_chat_turns'
$script:Migration0007ChatIds = $script:Migration0007AuthTask31Ids + '0011_internal_chat_turns'
$script:Migration0006ClaimEvidenceIds = $script:Migration0006ChatIds + '0012_task5_published_claim_evidence'
$script:Migration0007ClaimEvidenceIds = $script:Migration0007ChatIds + '0012_task5_published_claim_evidence'

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
    $authBaseline = @($script:Migration0008Ids | Sort-Object)
    $authShiraz = @($script:Migration0007And0008Ids | Sort-Object)
    $travelerBaseline = @($script:Migration0006AuthTravelerIds | Sort-Object)
    $travelerShiraz = @($script:Migration0007AuthTravelerIds | Sort-Object)
    $task31Baseline = @($script:Migration0006AuthTask31Ids | Sort-Object)
    $task31Shiraz = @($script:Migration0007AuthTask31Ids | Sort-Object)
    $chatBaseline = @($script:Migration0006ChatIds | Sort-Object)
    $chatShiraz = @($script:Migration0007ChatIds | Sort-Object)
    $claimEvidenceBaseline = @($script:Migration0006ClaimEvidenceIds | Sort-Object)
    $claimEvidenceShiraz = @($script:Migration0007ClaimEvidenceIds | Sort-Object)
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

    if ($appliedKey -ceq ($authBaseline -join ',')) {
        return [pscustomobject]@{
            Name = '0006-auth'
            ExpectedRows = 420
            MigrationIds = $script:Migration0008Ids
            IncludesShiraz = $false
            IncludesAuthentication = $true
        }
    }

    if ($appliedKey -ceq ($authShiraz -join ',')) {
        return [pscustomobject]@{
            Name = '0007-auth'
            ExpectedRows = 696
            MigrationIds = $script:Migration0007And0008Ids
            IncludesShiraz = $true
            IncludesAuthentication = $true
        }
    }

    if ($appliedKey -ceq ($travelerBaseline -join ',')) {
        return [pscustomobject]@{
            Name = '0006-auth-0009'
            ExpectedRows = 421
            MigrationIds = $script:Migration0006AuthTravelerIds
            IncludesShiraz = $false
            IncludesAuthentication = $true
            IncludesTravelerCore = $true
        }
    }

    if ($appliedKey -ceq ($travelerShiraz -join ',')) {
        return [pscustomobject]@{
            Name = '0007-auth-0009'
            ExpectedRows = 697
            MigrationIds = $script:Migration0007AuthTravelerIds
            IncludesShiraz = $true
            IncludesAuthentication = $true
            IncludesTravelerCore = $true
        }
    }

    if ($appliedKey -ceq ($task31Baseline -join ',')) {
        return [pscustomobject]@{
            Name = '0006-auth-0009-0010'
            ExpectedRows = 422
            MigrationIds = $script:Migration0006AuthTask31Ids
            IncludesShiraz = $false
            IncludesAuthentication = $true
            IncludesTravelerCore = $true
            IncludesTask31 = $true
        }
    }

    if ($appliedKey -ceq ($task31Shiraz -join ',')) {
        return [pscustomobject]@{
            Name = '0007-auth-0009-0010'
            ExpectedRows = 698
            MigrationIds = $script:Migration0007AuthTask31Ids
            IncludesShiraz = $true
            IncludesAuthentication = $true
            IncludesTravelerCore = $true
            IncludesTask31 = $true
        }
    }

    if ($appliedKey -ceq ($chatBaseline -join ',')) {
        return [pscustomobject]@{
            Name = '0006-auth-0009-0010-0011'
            ExpectedRows = 423
            MigrationIds = $script:Migration0006ChatIds
            IncludesShiraz = $false
            IncludesAuthentication = $true
            IncludesTravelerCore = $true
            IncludesTask31 = $true
            IncludesChat = $true
        }
    }
    if ($appliedKey -ceq ($chatShiraz -join ',')) {
        return [pscustomobject]@{
            Name = '0007-auth-0009-0010-0011'
            ExpectedRows = 699
            MigrationIds = $script:Migration0007ChatIds
            IncludesShiraz = $true
            IncludesAuthentication = $true
            IncludesTravelerCore = $true
            IncludesTask31 = $true
            IncludesChat = $true
        }
    }
    if ($appliedKey -ceq ($claimEvidenceBaseline -join ',')) {
        return [pscustomobject]@{
            Name = '0006-auth-0009-0010-0011-0012'
            ExpectedRows = 424
            MigrationIds = $script:Migration0006ClaimEvidenceIds
            IncludesShiraz = $false
            IncludesAuthentication = $true
            IncludesTravelerCore = $true
            IncludesTask31 = $true
            IncludesChat = $true
            IncludesClaimEvidence = $true
        }
    }
    if ($appliedKey -ceq ($claimEvidenceShiraz -join ',')) {
        return [pscustomobject]@{
            Name = '0007-auth-0009-0010-0011-0012'
            ExpectedRows = 700
            MigrationIds = $script:Migration0007ClaimEvidenceIds
            IncludesShiraz = $true
            IncludesAuthentication = $true
            IncludesTravelerCore = $true
            IncludesTask31 = $true
            IncludesChat = $true
            IncludesClaimEvidence = $true
        }
    }
    throw "Unsupported or partial database migration ledger. Expected an exact supported migration state through 0012; found: $appliedKey. No migration was applied."
}

function Resolve-DatabaseInitializationAction {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateSet('fresh', '0006', '0007', '0006-auth', '0007-auth', '0006-auth-0009', '0007-auth-0009', '0006-auth-0009-0010', '0007-auth-0009-0010', '0006-auth-0009-0010-0011', '0007-auth-0009-0010-0011', '0006-auth-0009-0010-0011-0012', '0007-auth-0009-0010-0011-0012')][string]$State,
        [switch]$ApplyPendingMigrationsToExistingDatabase,
        [switch]$ApplyAuthenticationMigrationToExistingDatabase,
        [switch]$ApplyTravelerCoreMigrationToExistingDatabase,
        [switch]$ApplyTask31MigrationToExistingDatabase,
        [switch]$ApplyChatMigrationToExistingDatabase,
        [switch]$ApplyClaimEvidenceMigrationToExistingDatabase
    )

    switch ($State) {
        'fresh' { return 'initialize-fresh' }
        '0006-auth' {
            if ($ApplyTravelerCoreMigrationToExistingDatabase) { return 'apply-traveler-0009-from-0006-auth' }
            throw 'Existing database is at Migration 0006 plus 0008. Migration 0009 is pending and requires separate owner approval. Rerun with -ApplyTravelerCoreMigrationToExistingDatabase only after that approval. No database write was performed.'
        }
        '0007-auth' {
            if ($ApplyTravelerCoreMigrationToExistingDatabase) { return 'apply-traveler-0009-from-0007-auth' }
            throw 'Existing database is at Migration 0007 plus 0008. Migration 0009 is pending and requires separate owner approval. Rerun with -ApplyTravelerCoreMigrationToExistingDatabase only after that approval. No database write was performed.'
        }
        '0006-auth-0009' {
            if ($ApplyTask31MigrationToExistingDatabase) { return 'apply-task31-0010-from-0006-auth-0009' }
            throw 'Existing database has Migrations 0000–0009 with the 0006 dataset. Migration 0010 is pending and requires separate owner approval. Rerun with -ApplyTask31MigrationToExistingDatabase only after that approval. No database write was performed.'
        }
        '0007-auth-0009' {
            if ($ApplyTask31MigrationToExistingDatabase) { return 'apply-task31-0010-from-0007-auth-0009' }
            throw 'Existing database has Migrations 0000–0009 with the 0007 dataset. Migration 0010 is pending and requires separate owner approval. Rerun with -ApplyTask31MigrationToExistingDatabase only after that approval. No database write was performed.'
        }
        '0006-auth-0009-0010' {
            if ($ApplyChatMigrationToExistingDatabase) { return 'apply-chat-0011-from-0006' }
            return 'already-task31'
        }
        '0007-auth-0009-0010' {
            if ($ApplyChatMigrationToExistingDatabase) { return 'apply-chat-0011-from-0007' }
            return 'already-task31'
        }
        '0006-auth-0009-0010-0011-0012' { return 'already-claim-evidence' }
        '0007-auth-0009-0010-0011-0012' { return 'already-claim-evidence' }
        '0006-auth-0009-0010-0011' {
            if ($ApplyClaimEvidenceMigrationToExistingDatabase) { return 'apply-claim-evidence-0012-from-0006' }
            return 'already-chat'
        }
        '0007-auth-0009-0010-0011' {
            if ($ApplyClaimEvidenceMigrationToExistingDatabase) { return 'apply-claim-evidence-0012-from-0007' }
            return 'already-chat'
        }
        '0006' {
            if ($ApplyAuthenticationMigrationToExistingDatabase) { return 'apply-auth-0008-from-0006' }
            if ($ApplyPendingMigrationsToExistingDatabase) { return 'apply-pending-0007' }
            throw 'Existing database is at Migration 0006 / 419 rows. Migration 0007 is pending and requires separate owner approval. To opt in after that approval, rerun with -ApplyPendingMigrationsToExistingDatabase. No database write was performed.'
        }
        '0007' {
            if ($ApplyAuthenticationMigrationToExistingDatabase) { return 'apply-auth-0008-from-0007' }
            return 'already-integrated'
        }
    }
}

Export-ModuleMember -Function Resolve-DatabaseLifecycleState, Resolve-DatabaseInitializationAction
