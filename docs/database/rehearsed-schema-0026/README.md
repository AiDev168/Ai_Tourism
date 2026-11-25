# Rahgard rehearsed schema catalogue - PostgreSQL 0026

## Scope and evidence boundary

This catalogue was generated from the isolated local Owner Demo PostgreSQL 17 database with a read-only application role. The collector queried PostgreSQL catalog metadata only; it did not read application row payloads, user messages, tenant records, or credentials. This is not a live VPS snapshot or an architecture approval.

- Source checkout at capture: `9680a2011815f82387400815fb6c10be26f20169`; API/PWA ran from local source, not newly built application images.
- Authorized database: `rahgard_pilot_vps_staging`. The non-template inventory also exposed `postgres`; that database was outside scope and was not opened.
- Catalogue: 105 relations (91 tables, 14 views), 1,132 column occurrences, 230 baseline glossary descriptions, and 902 undocumented occurrences.
- The 902 gaps are not distinct business requirements: 631 first-party base occurrences, 102 system/operations, 150 derived-view occurrences, and 19 extension-managed occurrences.
- `complete=false`; business meaning and architectural necessity are not approved. Unknown meanings remain unknown.

## Owner and technical entry points

- [Persian Owner index](OWNER_INDEX_FA.md)
- [Role, form, and API coverage](FORM_API_COVERAGE.md)
- [Sanitized snapshot evidence and checksums](SNAPSHOT_EVIDENCE.json)
- [Sanitized catalog metadata, including view definitions](catalog_metadata_snapshot.json)
- [Machine-readable manifest](manifest.json)
- Validate hashes, counts, and relation-document paths: `uv run python tools/schema/validate_rehearsed_schema.py`

## Relation documents

Each link is a generated object-level description. Column occurrences in views may repeat base attributes; presence in PostgreSQL does not establish product necessity or editability.

- [`conversation.assistant_turns`](rahgard_pilot_vps_staging-6b3312d4/conversation-8b34dbc2/tables/assistant_turns-f6adb88f.md) - 12 column occurrences; table; origin `first_party_application_base`.
- [`conversation.conversations`](rahgard_pilot_vps_staging-6b3312d4/conversation-8b34dbc2/tables/conversations-5c0dc939.md) - 13 column occurrences; table; origin `first_party_application_base`.
- [`conversation.messages`](rahgard_pilot_vps_staging-6b3312d4/conversation-8b34dbc2/tables/messages-f5cccfb7.md) - 15 column occurrences; table; origin `first_party_application_base`.
- [`geo.admin_area_aliases`](rahgard_pilot_vps_staging-6b3312d4/geo-e81935fb/tables/admin_area_aliases-69b365be.md) - 10 column occurrences; table; origin `first_party_application_base`.
- [`geo.admin_area_releases`](rahgard_pilot_vps_staging-6b3312d4/geo-e81935fb/tables/admin_area_releases-b7a694e4.md) - 11 column occurrences; table; origin `first_party_application_base`.
- [`geo.admin_areas`](rahgard_pilot_vps_staging-6b3312d4/geo-e81935fb/tables/admin_areas-3e2eda73.md) - 13 column occurrences; table; origin `first_party_application_base`.
- [`identity.auth_rate_limits`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/auth_rate_limits-ab60a2e5.md) - 4 column occurrences; table; origin `first_party_application_base`.
- [`identity.catalogue_review_grants`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/catalogue_review_grants-2d028f1d.md) - 6 column occurrences; table; origin `first_party_application_base`.
- [`identity.otp_challenges`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/otp_challenges-1969c61e.md) - 13 column occurrences; table; origin `first_party_application_base`.
- [`identity.platform_admin_mfa`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/platform_admin_mfa-73921895.md) - 8 column occurrences; table; origin `not assessed`.
- [`identity.platform_admin_mfa_events`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/platform_admin_mfa_events-af25d73e.md) - 5 column occurrences; table; origin `not assessed`.
- [`identity.platform_admin_step_up`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/platform_admin_step_up-4243c1a7.md) - 5 column occurrences; table; origin `not assessed`.
- [`identity.staging_auth_limits`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/staging_auth_limits-1f09c6f7.md) - 4 column occurrences; table; origin `first_party_application_base`.
- [`identity.staging_invites`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/staging_invites-0d54e43c.md) - 6 column occurrences; table; origin `first_party_application_base`.
- [`identity.staging_password_credentials`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/staging_password_credentials-617738de.md) - 6 column occurrences; table; origin `first_party_application_base`.
- [`identity.user_consents`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/user_consents-7a7aebd6.md) - 10 column occurrences; table; origin `first_party_application_base`.
- [`identity.user_preferences`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/user_preferences-7e378789.md) - 11 column occurrences; table; origin `first_party_application_base`.
- [`identity.users`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/users-7dfb4cf6.md) - 10 column occurrences; table; origin `first_party_application_base`.
- [`identity.verified_phones`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/verified_phones-66f7e274.md) - 4 column occurrences; table; origin `first_party_application_base`.
- [`identity.web_sessions`](rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/web_sessions-a075ea48.md) - 10 column occurrences; table; origin `first_party_application_base`.
- [`integration.chat_daily_global_budget`](rahgard_pilot_vps_staging-6b3312d4/integration-eb92cc52/tables/chat_daily_global_budget-27b4bbd7.md) - 2 column occurrences; table; origin `first_party_system_or_operations`.
- [`integration.chat_daily_user_budget`](rahgard_pilot_vps_staging-6b3312d4/integration-eb92cc52/tables/chat_daily_user_budget-6c98bd64.md) - 3 column occurrences; table; origin `first_party_system_or_operations`.
- [`integration.external_links`](rahgard_pilot_vps_staging-6b3312d4/integration-eb92cc52/tables/external_links-b9ab75bd.md) - 9 column occurrences; table; origin `first_party_system_or_operations`.
- [`integration.outbound_clicks`](rahgard_pilot_vps_staging-6b3312d4/integration-eb92cc52/tables/outbound_clicks-19c8afdc.md) - 9 column occurrences; table; origin `first_party_system_or_operations`.
- [`knowledge.active_embedding_spaces`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/active_embedding_spaces-1b30f488.md) - 11 column occurrences; view; origin `derived_view`.
- [`knowledge.catalogue_publication_events`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/catalogue_publication_events-c4a82f50.md) - 7 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.chunk_embeddings`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/chunk_embeddings-f9d8072c.md) - 6 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.culinary_item_sources`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/culinary_item_sources-c8ea7adb.md) - 14 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.culinary_knowledge_items`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/culinary_knowledge_items-39e2713d.md) - 21 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_access_points`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_access_points-0c087cc8.md) - 14 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_aliases`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_aliases-75309a16.md) - 10 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_candidate_evidence`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_candidate_evidence-92151fb7.md) - 11 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_candidate_reviews`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_candidate_reviews-4cf36b04.md) - 10 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_candidates`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_candidates-6a9824e7.md) - 21 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_categories`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_categories-6ec43aad.md) - 6 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_category_map`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_category_map-2776bfb3.md) - 5 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_claim_evidence`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_claim_evidence-c4355517.md) - 23 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_enrichment_proposal_sources`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_enrichment_proposal_sources-7ce2e624.md) - 14 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_enrichment_proposals`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_enrichment_proposals-253b2149.md) - 16 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_localizations`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_localizations-0eb8da97.md) - 11 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_operational_assertions`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_operational_assertions-5805af5e.md) - 17 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_sources`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_sources-52eec045.md) - 7 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_tags`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_tags-fe7b7ef7.md) - 2 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destination_visit_duration_evidence`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_visit_duration_evidence-5579d9f3.md) - 13 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.destinations`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destinations-1af0500e.md) - 28 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.embedding_spaces`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/embedding_spaces-f7a9b58b.md) - 12 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.knowledge_chunks`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/knowledge_chunks-c1de8a43.md) - 10 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.knowledge_documents`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/knowledge_documents-c8a3d0bd.md) - 18 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.knowledge_sources`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/knowledge_sources-059f8744.md) - 10 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.production_chunk_embeddings`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_chunk_embeddings-c270ebe9.md) - 14 column occurrences; view; origin `derived_view`.
- [`knowledge.production_culinary_knowledge`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_culinary_knowledge-bb2646f2.md) - 9 column occurrences; view; origin `derived_view`.
- [`knowledge.production_destination_categories`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_destination_categories-afee998c.md) - 5 column occurrences; view; origin `derived_view`.
- [`knowledge.production_destination_category_map`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_destination_category_map-389c0e66.md) - 4 column occurrences; view; origin `derived_view`.
- [`knowledge.production_destination_claim_evidence`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_destination_claim_evidence-c36d86cb.md) - 26 column occurrences; view; origin `derived_view`.
- [`knowledge.production_destination_sources`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_destination_sources-9f650eaa.md) - 11 column occurrences; view; origin `derived_view`.
- [`knowledge.production_destination_tags`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_destination_tags-965cf515.md) - 2 column occurrences; view; origin `derived_view`.
- [`knowledge.production_destinations`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_destinations-40eadf41.md) - 27 column occurrences; view; origin `derived_view`.
- [`knowledge.production_retrieval_chunks`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_retrieval_chunks-5c690ae9.md) - 19 column occurrences; view; origin `derived_view`.
- [`knowledge.production_retrieval_documents`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_retrieval_documents-7946c5ed.md) - 22 column occurrences; view; origin `derived_view`.
- [`knowledge.source_candidate_reviews`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/source_candidate_reviews-447c5344.md) - 9 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.source_candidates`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/source_candidates-96f26cbd.md) - 17 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.source_registry_registration_events`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/source_registry_registration_events-091879f4.md) - 10 column occurrences; table; origin `first_party_application_base`.
- [`knowledge.source_verification_reviews`](rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/source_verification_reviews-cc624d8f.md) - 11 column occurrences; table; origin `first_party_application_base`.
- [`operations.ai_model_calls`](rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/ai_model_calls-48e13f37.md) - 12 column occurrences; table; origin `first_party_system_or_operations`.
- [`operations.audit_events`](rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/audit_events-14cca081.md) - 9 column occurrences; table; origin `first_party_system_or_operations`.
- [`operations.dataset_import_batches`](rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/dataset_import_batches-df7cf9dc.md) - 8 column occurrences; table; origin `first_party_system_or_operations`.
- [`operations.dataset_import_files`](rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/dataset_import_files-904901ca.md) - 15 column occurrences; table; origin `first_party_system_or_operations`.
- [`operations.feedback`](rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/feedback-59bda3f8.md) - 10 column occurrences; table; origin `first_party_system_or_operations`.
- [`operations.private_pilot_geo_approvals`](rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/private_pilot_geo_approvals-b1ba5af2.md) - 9 column occurrences; table; origin `first_party_system_or_operations`.
- [`operations.private_pilot_geo_authorizations`](rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/private_pilot_geo_authorizations-4ca96d93.md) - 17 column occurrences; table; origin `first_party_system_or_operations`.
- [`partner.availability_snapshots`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/availability_snapshots-ba838abd.md) - 14 column occurrences; table; origin `first_party_application_base`.
- [`partner.branches`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/branches-dce19053.md) - 12 column occurrences; table; origin `first_party_application_base`.
- [`partner.invitations`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/invitations-33cd5e40.md) - 10 column occurrences; table; origin `first_party_application_base`.
- [`partner.memberships`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/memberships-5050625e.md) - 9 column occurrences; table; origin `first_party_application_base`.
- [`partner.offers`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/offers-92ab364e.md) - 13 column occurrences; table; origin `first_party_application_base`.
- [`partner.organizations`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/organizations-f8a665a9.md) - 15 column occurrences; table; origin `first_party_application_base`.
- [`partner.platform_grant_events`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/platform_grant_events-771a5214.md) - 8 column occurrences; table; origin `not assessed`.
- [`partner.platform_grants`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/platform_grants-a4a5df9a.md) - 6 column occurrences; table; origin `first_party_application_base`.
- [`partner.prices`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/prices-fe81f939.md) - 14 column occurrences; table; origin `first_party_application_base`.
- [`partner.review_events`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/review_events-3b16bd9c.md) - 9 column occurrences; table; origin `first_party_application_base`.
- [`partner.schedules`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/schedules-6e9a1ab2.md) - 12 column occurrences; table; origin `first_party_application_base`.
- [`partner.service_destinations`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/service_destinations-210419ff.md) - 7 column occurrences; table; origin `first_party_application_base`.
- [`partner.service_localizations`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/service_localizations-51c8d7f8.md) - 9 column occurrences; table; origin `first_party_application_base`.
- [`partner.services`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/services-ef1c4b45.md) - 12 column occurrences; table; origin `first_party_application_base`.
- [`partner.share_eligible_organizations`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/views/share_eligible_organizations-ce33f94c.md) - 3 column occurrences; view; origin `derived_view`.
- [`partner.traveler_request_inbox`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/traveler_request_inbox-e77d4232.md) - 6 column occurrences; table; origin `first_party_application_base`.
- [`partner.traveler_request_revisions`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/traveler_request_revisions-e7bb178d.md) - 11 column occurrences; table; origin `first_party_application_base`.
- [`partner.traveler_request_shares`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/traveler_request_shares-27951838.md) - 9 column occurrences; table; origin `first_party_application_base`.
- [`partner.trip_company_responses`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/trip_company_responses-f5079928.md) - 18 column occurrences; table; origin `first_party_application_base`.
- [`partner.verification_cases`](rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/verification_cases-ccd9ee8c.md) - 11 column occurrences; table; origin `first_party_application_base`.
- [`public.geography_columns`](rahgard_pilot_vps_staging-6b3312d4/public-efa1f375/views/geography_columns-d4370c1b.md) - 7 column occurrences; view; origin `extension_managed`.
- [`public.geometry_columns`](rahgard_pilot_vps_staging-6b3312d4/public-efa1f375/views/geometry_columns-db35ba0f.md) - 7 column occurrences; view; origin `extension_managed`.
- [`public.rahgard_private_pilot_marker`](rahgard_pilot_vps_staging-6b3312d4/public-efa1f375/tables/rahgard_private_pilot_marker-64e06a2e.md) - 1 column occurrences; table; origin `first_party_system_or_operations`.
- [`public.spatial_ref_sys`](rahgard_pilot_vps_staging-6b3312d4/public-efa1f375/tables/spatial_ref_sys-6b0f8c39.md) - 5 column occurrences; table; origin `extension_managed`.
- [`recommendation.recommendation_requests`](rahgard_pilot_vps_staging-6b3312d4/recommendation-dbfe9375/tables/recommendation_requests-b58aca54.md) - 10 column occurrences; table; origin `first_party_application_base`.
- [`recommendation.recommendation_score_components`](rahgard_pilot_vps_staging-6b3312d4/recommendation-dbfe9375/tables/recommendation_score_components-e3b855a1.md) - 10 column occurrences; table; origin `first_party_application_base`.
- [`recommendation.recommendations`](rahgard_pilot_vps_staging-6b3312d4/recommendation-dbfe9375/tables/recommendations-f9b89ad4.md) - 12 column occurrences; table; origin `first_party_application_base`.
- [`system.schema_migrations`](rahgard_pilot_vps_staging-6b3312d4/system-bbc5e661/tables/schema_migrations-26bec784.md) - 3 column occurrences; table; origin `first_party_system_or_operations`.
- [`travel.itineraries`](rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/itineraries-03a4100d.md) - 12 column occurrences; table; origin `first_party_application_base`.
- [`travel.itinerary_stops`](rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/itinerary_stops-5025eb44.md) - 13 column occurrences; table; origin `first_party_application_base`.
- [`travel.provisional_itineraries`](rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/provisional_itineraries-db7c0fe6.md) - 11 column occurrences; table; origin `first_party_application_base`.
- [`travel.trip_constraints`](rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/trip_constraints-a41e8f02.md) - 11 column occurrences; table; origin `first_party_application_base`.
- [`travel.trip_interests`](rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/trip_interests-7b9a4366.md) - 7 column occurrences; table; origin `first_party_application_base`.
- [`travel.trip_requirement_revisions`](rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/trip_requirement_revisions-8de20de1.md) - 7 column occurrences; table; origin `first_party_application_base`.
- [`travel.trips`](rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/trips-57866688.md) - 26 column occurrences; table; origin `first_party_application_base`.
