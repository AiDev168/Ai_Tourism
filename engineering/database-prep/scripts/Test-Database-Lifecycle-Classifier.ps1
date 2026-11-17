$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'Database-Lifecycle.psm1') -Force

$baseline = @(
    '0000_legacy_tourism_points_baseline', '0001_core_schema',
    '0002_synthetic_knowledge_seed', '0003_synthetic_e2e_seed',
    '0004_app_role_grants', '0005_verified_unesco_destination_seed',
    '0006_verified_unesco_destination_seed_batch2'
)
$integrated = $baseline + '0007_shiraz_dalahoo_wikipedia_dataset_v1'
$authBaseline = $baseline + '0008_authentication_foundation'
$authIntegrated = $integrated + '0008_authentication_foundation'
$travelerBaseline = $authBaseline + '0009_traveler_core'
$travelerIntegrated = $authIntegrated + '0009_traveler_core'
$task31Baseline = $travelerBaseline + '0010_task31_content_privacy_full_itinerary'
$task31Integrated = $travelerIntegrated + '0010_task31_content_privacy_full_itinerary'
$chatBaseline = $task31Baseline + '0011_internal_chat_turns'
$chatIntegrated = $task31Integrated + '0011_internal_chat_turns'
$claimEvidenceBaseline = $chatBaseline + '0012_task5_published_claim_evidence'
$claimEvidenceIntegrated = $chatIntegrated + '0012_task5_published_claim_evidence'
$cases = @(
    @{ Name = 'exact 0006 ledger'; Ids = $baseline; Expected = '0006'; Error = $false },
    @{ Name = 'exact 0007 ledger'; Ids = $integrated; Expected = '0007'; Error = $false },
    @{ Name = '0006 plus authentication ledger'; Ids = $authBaseline; Expected = '0006-auth'; Error = $false },
    @{ Name = '0007 plus authentication ledger'; Ids = $authIntegrated; Expected = '0007-auth'; Error = $false },
    @{ Name = '0006 plus authentication and traveler migration'; Ids = $travelerBaseline; Expected = '0006-auth-0009'; Error = $false },
    @{ Name = '0007 plus authentication and traveler migration'; Ids = $travelerIntegrated; Expected = '0007-auth-0009'; Error = $false },
    @{ Name = '0006 plus Task 3.1 migration'; Ids = $task31Baseline; Expected = '0006-auth-0009-0010'; Error = $false },
    @{ Name = '0007 plus Task 3.1 migration'; Ids = $task31Integrated; Expected = '0007-auth-0009-0010'; Error = $false },
    @{ Name = '0006 plus Chat migration'; Ids = $chatBaseline; Expected = '0006-auth-0009-0010-0011'; Error = $false },
    @{ Name = '0007 plus Chat migration'; Ids = $chatIntegrated; Expected = '0007-auth-0009-0010-0011'; Error = $false },
    @{ Name = '0006 plus claim evidence migration'; Ids = $claimEvidenceBaseline; Expected = '0006-auth-0009-0010-0011-0012'; Error = $false },
    @{ Name = '0007 plus claim evidence migration'; Ids = $claimEvidenceIntegrated; Expected = '0007-auth-0009-0010-0011-0012'; Error = $false },
    @{ Name = 'empty ledger'; Ids = @(); Expected = ''; Error = $true },
    @{ Name = 'partial 0006 ledger'; Ids = $baseline[0..5]; Expected = ''; Error = $true },
    @{ Name = '0008 with missing 0006 predecessor'; Ids = @($baseline[0..5] + '0008_authentication_foundation'); Expected = ''; Error = $true },
    @{ Name = '0007 and 0008 with missing 0006 predecessor'; Ids = @($baseline[0..5] + '0007_shiraz_dalahoo_wikipedia_dataset_v1' + '0008_authentication_foundation'); Expected = ''; Error = $true },
    @{ Name = '0009 without 0008 predecessor'; Ids = @($baseline + '0009_traveler_core'); Expected = ''; Error = $true },
    @{ Name = '0009 with missing 0006 predecessor'; Ids = @($baseline[0..5] + '0007_shiraz_dalahoo_wikipedia_dataset_v1' + '0008_authentication_foundation' + '0009_traveler_core'); Expected = ''; Error = $true },
    @{ Name = '0010 without 0009 predecessor'; Ids = @($authBaseline + '0010_task31_content_privacy_full_itinerary'); Expected = ''; Error = $true },
    @{ Name = '0010 with missing 0006 predecessor'; Ids = @($baseline[0..5] + '0007_shiraz_dalahoo_wikipedia_dataset_v1' + '0008_authentication_foundation' + '0010_task31_content_privacy_full_itinerary'); Expected = ''; Error = $true },
    @{ Name = '0007 marker with missing predecessor'; Ids = @($baseline[0..5] + '0007_shiraz_dalahoo_wikipedia_dataset_v1'); Expected = ''; Error = $true },
    @{ Name = 'unknown migration'; Ids = @($baseline + '0009_unrecognized'); Expected = ''; Error = $true },
    @{ Name = 'duplicate migration identifier'; Ids = @($baseline + $baseline[-1]); Expected = ''; Error = $true }
)

foreach ($case in $cases) {
    $failed = $false
    try {
        $state = Resolve-DatabaseLifecycleState -AppliedMigrationIds $case.Ids
        if ($case.Error -or $state.Name -ne $case.Expected) {
            throw "Unexpected classifier result for '$($case.Name)': $($state.Name)"
        }
        if (($state.Name -eq '0006' -and $state.ExpectedRows -ne 419) -or
            ($state.Name -eq '0007' -and $state.ExpectedRows -ne 695) -or
            ($state.Name -eq '0006-auth' -and $state.ExpectedRows -ne 420) -or
            ($state.Name -eq '0007-auth' -and $state.ExpectedRows -ne 696) -or
            ($state.Name -eq '0006-auth-0009' -and $state.ExpectedRows -ne 421) -or
            ($state.Name -eq '0007-auth-0009' -and $state.ExpectedRows -ne 697) -or
            ($state.Name -eq '0006-auth-0009-0010' -and $state.ExpectedRows -ne 422) -or
            ($state.Name -eq '0007-auth-0009-0010' -and $state.ExpectedRows -ne 698) -or
            ($state.Name -eq '0006-auth-0009-0010-0011' -and $state.ExpectedRows -ne 423) -or
            ($state.Name -eq '0007-auth-0009-0010-0011' -and $state.ExpectedRows -ne 699) -or
            ($state.Name -eq '0006-auth-0009-0010-0011-0012' -and $state.ExpectedRows -ne 424) -or
            ($state.Name -eq '0007-auth-0009-0010-0011-0012' -and $state.ExpectedRows -ne 700)) {
            throw "Incorrect exact row manifest selected for '$($case.Name)'"
        }
    }
    catch {
        if (-not $case.Error) { throw }
        $failed = $true
    }
    if ($case.Error -and -not $failed) { throw "Expected fail-closed result for '$($case.Name)'" }
    Write-Host "PASS: $($case.Name)"
}

$actionCases = @(
    @{ Name = 'fresh database initializes'; State = 'fresh'; OptIn = $false; Expected = 'initialize-fresh'; Error = $false },
    @{ Name = '0006 default refuses pending migration'; State = '0006'; OptIn = $false; Expected = ''; Error = $true },
    @{ Name = '0006 explicit opt-in permits pending migration'; State = '0006'; OptIn = $true; Expected = 'apply-pending-0007'; Error = $false },
    @{ Name = '0006 explicit auth opt-in skips optional 0007'; State = '0006'; AuthOptIn = $true; Expected = 'apply-auth-0008-from-0006'; Error = $false },
    @{ Name = '0007 explicit auth opt-in'; State = '0007'; AuthOptIn = $true; Expected = 'apply-auth-0008-from-0007'; Error = $false },
    @{ Name = '0006 auth state requires explicit traveler migration opt-in'; State = '0006-auth'; Expected = ''; Error = $true },
    @{ Name = '0007 auth state requires explicit traveler migration opt-in'; State = '0007-auth'; Expected = ''; Error = $true },
    @{ Name = '0006 auth explicit traveler migration opt-in'; State = '0006-auth'; TravelerOptIn = $true; Expected = 'apply-traveler-0009-from-0006-auth'; Error = $false },
    @{ Name = '0007 auth explicit traveler migration opt-in'; State = '0007-auth'; TravelerOptIn = $true; Expected = 'apply-traveler-0009-from-0007-auth'; Error = $false },
    @{ Name = '0006 plus 0009 requires explicit Task 3.1 opt-in'; State = '0006-auth-0009'; Expected = ''; Error = $true },
    @{ Name = '0007 plus 0009 requires explicit Task 3.1 opt-in'; State = '0007-auth-0009'; Expected = ''; Error = $true },
    @{ Name = '0006 plus 0009 explicit Task 3.1 opt-in'; State = '0006-auth-0009'; Task31OptIn = $true; Expected = 'apply-task31-0010-from-0006-auth-0009'; Error = $false },
    @{ Name = '0007 plus 0009 explicit Task 3.1 opt-in'; State = '0007-auth-0009'; Task31OptIn = $true; Expected = 'apply-task31-0010-from-0007-auth-0009'; Error = $false },
    @{ Name = '0006 plus 0010 no-op'; State = '0006-auth-0009-0010'; Expected = 'already-task31'; Error = $false },
    @{ Name = '0007 plus 0010 no-op'; State = '0007-auth-0009-0010'; Expected = 'already-task31'; Error = $false },
    @{ Name = '0006 plus 0010 explicit Chat opt-in'; State = '0006-auth-0009-0010'; ChatOptIn = $true; Expected = 'apply-chat-0011-from-0006'; Error = $false },
    @{ Name = '0007 plus 0010 explicit Chat opt-in'; State = '0007-auth-0009-0010'; ChatOptIn = $true; Expected = 'apply-chat-0011-from-0007'; Error = $false },
    @{ Name = '0006 plus 0011 no-op'; State = '0006-auth-0009-0010-0011'; Expected = 'already-chat'; Error = $false },
    @{ Name = '0007 plus 0011 no-op'; State = '0007-auth-0009-0010-0011'; Expected = 'already-chat'; Error = $false },
    @{ Name = '0006 plus 0011 claim migration opt-in'; State = '0006-auth-0009-0010-0011'; ClaimEvidenceOptIn = $true; Expected = 'apply-claim-evidence-0012-from-0006'; Error = $false },
    @{ Name = '0007 plus 0011 claim migration opt-in'; State = '0007-auth-0009-0010-0011'; ClaimEvidenceOptIn = $true; Expected = 'apply-claim-evidence-0012-from-0007'; Error = $false },
    @{ Name = '0006 claim evidence no-op'; State = '0006-auth-0009-0010-0011-0012'; Expected = 'already-claim-evidence'; Error = $false },
    @{ Name = '0007 claim evidence no-op'; State = '0007-auth-0009-0010-0011-0012'; Expected = 'already-claim-evidence'; Error = $false },
    @{ Name = '0007 is a read-only no-op'; State = '0007'; OptIn = $false; Expected = 'already-integrated'; Error = $false }
)
foreach ($case in $actionCases) {
    $failed = $false
    try {
        if ($case.AuthOptIn) {
            $action = Resolve-DatabaseInitializationAction -State $case.State -ApplyAuthenticationMigrationToExistingDatabase
        }
        elseif ($case.TravelerOptIn) {
            $action = Resolve-DatabaseInitializationAction -State $case.State -ApplyTravelerCoreMigrationToExistingDatabase
        }
        elseif ($case.Task31OptIn) {
            $action = Resolve-DatabaseInitializationAction -State $case.State -ApplyTask31MigrationToExistingDatabase
        }
        elseif ($case.ChatOptIn) {
            $action = Resolve-DatabaseInitializationAction -State $case.State -ApplyChatMigrationToExistingDatabase
        }
        elseif ($case.ClaimEvidenceOptIn) {
            $action = Resolve-DatabaseInitializationAction -State $case.State -ApplyClaimEvidenceMigrationToExistingDatabase
        }
        elseif ($case.OptIn) {
            $action = Resolve-DatabaseInitializationAction -State $case.State -ApplyPendingMigrationsToExistingDatabase
        }
        else {
            $action = Resolve-DatabaseInitializationAction -State $case.State
        }
        if ($case.Error -or $action -ne $case.Expected) { throw "Unexpected initialization action for '$($case.Name)': $action" }
    }
    catch {
        if (-not $case.Error) { throw }
        $failed = $true
    }
    if ($case.Error -and -not $failed) { throw "Expected fail-closed initialization for '$($case.Name)'" }
    Write-Host "PASS: $($case.Name)"
}

Write-Host 'PASS: migration ledger classification, initialization opt-in policy, and fail-closed partial/unknown cases.'
