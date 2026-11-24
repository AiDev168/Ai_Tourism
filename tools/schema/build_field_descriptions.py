#!/usr/bin/env python3
"""Enrich the Rahgard metadata-only schema catalogue with evidence-aware field docs.

The builder never connects to PostgreSQL or reads application records. It uses
the sanitized pg_catalog snapshot, migration source files and checked-in API
contracts. Any meaning that cannot be supported is explicitly marked unresolved
instead of being guessed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "docs/database/live-schema/catalog_snapshot.json"
DESCRIPTIONS = ROOT / "docs/database/field_descriptions.json"

OFFICIAL_SOURCES = {
    "postgres_types": "https://www.postgresql.org/docs/17/datatype.html",
    "postgres_datetime": "https://www.postgresql.org/docs/17/datatype-datetime.html",
    "postgres_json": "https://www.postgresql.org/docs/17/datatype-json.html",
    "postgres_database_catalog": "https://www.postgresql.org/docs/17/catalog-pg-database.html",
    "postgis_management": "https://postgis.net/docs/using_postgis_dbmanagement.html",
    "pgvector": "https://github.com/pgvector/pgvector",
}

FIELD_MEANINGS = {
    'id': 'Primary identifier for this row; the database constraint section identifies its key role.',
    'user_id': 'User identity that owns or is associated with this record; foreign-key metadata identifies the referenced relation.',
    'organization_id': 'Company/organization scope for this record; foreign-key and row-security rules bind it to that tenant.',
    'destination_id': 'Canonical destination identity associated with this row.',
    'trip_id': 'Stable trip identity connecting requirements, itinerary and company sharing.',
    'conversation_id': 'Conversation containing the travel request/message context.',
    'recommendation_id': 'Recommendation associated with this record; foreign-key metadata identifies the recommendation relation.',
    'recommendation_request_id': 'Identity of the recommendation request used to generate the result.',
    'itinerary_id': 'Saved itinerary associated with this record.',
    'service_id': 'Company service associated with this record.',
    'schedule_id': 'Company schedule associated with this record.',
    'offer_id': 'Company offer associated with this record.',
    'source_id': 'Registered knowledge/source record associated with this evidence or destination.',
    'document_id': 'Knowledge document associated with this record.',
    'chunk_id': 'Knowledge chunk associated with this record.',
    'created_at': 'Timestamp at which this row or event was created.',
    'updated_at': 'Timestamp of the last persisted update to this row.',
    'started_at': 'Timestamp at which the named activity or lifecycle began; entity context is supplied by the table name.',
    'ended_at': 'Timestamp at which the named activity or lifecycle ended; entity context is supplied by the table name.',
    'expires_at': 'Expiry instant after which the associated credential, invitation, session, or record is no longer valid; see table context.',
    'valid_from': 'Inclusive beginning of the validity interval for the associated fact or offer.',
    'valid_until': 'Exclusive/end boundary for the validity interval; exact boundary convention is defined by the consuming contract.',
    'observed_at': 'Time when the associated operational fact was observed, distinct from row creation time.',
    'retrieved_at': 'Time when the associated source/document/evidence was retrieved.',
    'published_at': 'Publication time reported for the administrative dataset or content.',
    'reviewed_at': 'Timestamp when a reviewer last inspected or reviewed this record.',
    'decided_at': 'Timestamp when the review decision was made.',
    'granted_at': 'Time at which the associated permission or consent was granted.',
    'revoked_at': 'Time at which the associated permission or consent was revoked.',
    'consumed_at': 'Time when the one-time challenge or invitation was consumed; null means it has not been consumed.',
    'verified_at': 'Time when the associated identity, source, or organization was verified.',
    'submitted_at': 'Time when the associated request or evidence was submitted for review.',
    'is_synthetic': 'Synthetic/test fixture marker; these records must be excluded from production views.',
    'is_active': 'Activation flag for the associated record; review and publication status remain separate.',
    'is_published': 'Publication flag for the associated approved record or evidence.',
    'is_verified': 'Whether the associated entity/evidence passed the applicable verification review.',
    'is_granted': 'Whether the traveler granted the consent for its recorded purpose and policy version.',
    'is_required': 'Whether the associated interest/constraint is mandatory rather than a preference.',
    'is_revoked': 'Derived flag indicating the claim has been revoked from publication use.',
    'status': "Lifecycle state of this relation's entity; use the associated CHECK/enum constraints for the accepted values.",
    'review_status': "Review lifecycle state of this relation's entity; it is not synonymous with publication.",
    'verification_status': 'State of evidence verification; distinct from application approval and marketplace participation.',
    'application_status': 'State of organization onboarding/application review.',
    'participation_status': "State of the organization's participation in eligible marketplace workflows.",
    'decision': 'Decision for the linked review; the exact enum values are shown in the constraints/API contract.',
    'reason': 'Reviewer explanation for accepting, rejecting, or returning the associated record.',
    'policy_version': 'Consent or review policy identifier acknowledged at the time.',
    'locale': "Locale of this localized value or evidence, using the application's supported locale contract.",
    'language_code': 'Language tag of the knowledge document.',
    'currency': 'Currency denomination attached to the associated budget or price; units must be interpreted with the paired amount/unit fields.',
    'budget_currency_iso': 'ISO currency code associated with the original budget amount.',
    'budget_amount_original': 'Traveler-entered budget amount before normalization; the paired currency and unit fields preserve denomination.',
    'budget_raw_text': 'Original budget wording supplied by the traveler, retained for interpretation provenance.',
    'budget_unit': 'Scale/unit attached to the budget amount (for example an expressed million unit); valid values are defined by the request contract.',
    'latitude': 'Latitude value for the stated coordinate role; source and precision are separately recorded.',
    'longitude': 'Longitude value for the stated coordinate role; source and precision are separately recorded.',
    'point': 'PostGIS point geometry for the named access/location record; coordinate role and SRID must be interpreted from related fields and constraints.',
    'geometry': 'PostGIS geometry for the administrative area; geometry source, feature identity and SRID are recorded separately.',
    'location': 'Geographic location geometry/value for the canonical destination, subject to its explicit coordinate role.',
    'coordinate_role': 'Meaning of the stored coordinate (such as representative point or access point); never infer an entrance from another role.',
    'accessibility_state': 'Evidence-backed accessibility state; unknown is not the same as accessible.',
    'coordinate_precision_m': 'Estimated coordinate precision in metres; it does not assert a visitor entrance.',
    'minimum_minutes': 'Evidence-backed minimum recommended visit duration, in minutes.',
    'maximum_minutes': 'Evidence-backed maximum recommended visit duration, in minutes.',
    'duration_minutes': 'Duration in minutes for the associated itinerary stop.',
    'travel_to_next_estimate_minutes': 'Estimated travel duration to the next stop in minutes; it is an estimate, not a guaranteed route time.',
    'traveler_count': 'Number of travelers in the trip party.',
    'duration_days': 'Trip duration in whole calendar days, when known.',
    'day_count': 'Number of days represented by the associated itinerary.',
    'day_number': 'One-based itinerary day number.',
    'stop_order': 'Ordering of a stop within an itinerary day.',
    'planned_start_time': 'Planned local start time for an itinerary stop; this is a plan value, not venue confirmation.',
    'price_amount': 'Monetary amount for the associated price, interpreted with currency, unit, validity and tax fields.',
    'currency_code': 'Currency code for the associated monetary amount.',
    'weight': 'Relative preference/constraint weight used by recommendation logic; scale and normalization are defined by the application contract.',
    'confidence': 'Confidence value attached to an interpreted preference, evidence or recommendation; range is enforced by constraints/API when present.',
    'approval_confidence': 'Confidence metadata supplied during review; it is not approval authority.',
    'reliability_score': 'Source reliability score used as evidence metadata; the scoring scale is an application contract.',
    'final_score': 'Deterministic recommendation score after configured components and weights.',
    'raw_score': 'Unnormalized score for one recommendation component.',
    'normalized_score': "Score transformed to the recommendation component's normalized scale.",
    'weighted_score': 'Component score after applying its configured weight.',
    'estimated_cost': 'Estimated provider cost for the call; estimation basis is provider/configuration specific.',
    'cost_currency': 'Currency used for the estimated model call cost.',
    'input_tokens': 'Provider-reported or estimated prompt token count.',
    'output_tokens': 'Provider-reported or estimated completion token count.',
    'latency_ms': 'Duration between request start and completion, in milliseconds.',
    'hit_count': 'Number of requests counted in the associated rate-limit window.',
    'failed_attempts': 'Count of failed OTP verification attempts for the challenge.',
    'iterations': 'Password-derivation iteration count used for this credential record; the derived verifier and salt are sensitive authentication data.',
    'vector_dimension': 'Number of numeric dimensions in the associated embedding representation.',
    'embedding': 'Vector representation associated with a knowledge chunk and embedding space; generated data is not a factual source by itself.',
    'similarity_metric': 'Configured distance/similarity function for the embedding space.',
    'content_sha256': 'SHA-256 digest of the associated content version, used for integrity/version identity.',
    'payload_sha256': 'Digest of the serialized proposal payload.',
    'row_sha256': 'Digest used to detect repeated or changed source rows.',
    'file_sha256': 'SHA-256 digest of the imported source file.',
    'source_file_sha256': 'Digest binding the record to an exact uploaded file.',
    'source_checksum': 'Checksum of the imported source dataset; exact algorithm is identified by the contract or adjacent field.',
    'decision_sha256': 'Digest binding a review authorization to its exact serialized decision payload.',
    'marker_sha256': 'Digest of the isolated pilot/deployment marker used to bind an approval to a specific environment.',
    'evidence_ids': 'Identifiers of the reviewed evidence claims supporting publication.',
    'evidence_refs': 'Evidence reference list submitted for independent verification.',
    'evidence_excerpt': 'Short source-language excerpt used to substantiate the source review.',
    'evidence_note': 'Reviewer/source note explaining the evidence relationship; not itself a substitute for the source.',
    'source_url': 'Source URL supporting the associated identity, location, or operational claim.',
    'canonical_url': 'Canonical URL of the associated knowledge document.',
    'url': 'URL for the source/external link; exact role follows table and API contract.',
    'target_url': 'URL opened by an authorized external-link action.',
    'source_license': 'Rights/license status recorded for the source; unknown is not permission.',
    'license': 'Rights/license note projected for the linked evidence.',
    'metadata': 'Structured auxiliary metadata for the associated event/click; content schema is application-specific.',
    'raw_record': 'Exact parsed source row retained for audit/review; never trusted as public content without approval.',
    'raw_content': 'Retrieved source content retained for provenance; access and reuse remain subject to source terms.',
    'content': 'Text content of the associated knowledge chunk; use only through publication and provenance safeguards.',
    'claims': 'Structured claims associated with the content record; each factual claim requires traceable evidence.',
    'provenance': 'Structured provenance describing the sources/support for the associated published knowledge item.',
    'input_snapshot': 'Immutable requirements/input snapshot used for the associated recommendation request.',
    'requirement_snapshot': 'Versioned traveler-requirements snapshot recorded for the trip revision.',
    'confirmed_requirements': 'Traveler-confirmed structured requirements for the trip; explicit user edits take precedence over suggestions.',
    'extracted_requirements': 'Structured requirements extracted from traveler input; provenance/confirmation state is stored separately.',
    'structured_context': 'Private structured conversation context derived from traveler inputs and confirmed corrections.',
    'days': 'Day-by-day provisional itinerary draft payload; remains unverified until supported by approved catalogue evidence.',
    'descriptions_by_locale': 'Localized culinary item descriptions keyed by locale.',
    'names_by_locale': 'Localized culinary item names keyed by locale.',
    'title_by_locale': 'Localized itinerary title keyed by locale.',
    'explanation_by_locale': 'Localized recommendation explanation keyed by locale; factual claims remain subject to evidence.',
    'warnings': 'Warnings attached to the recommendation, including known limitations or unmet constraints.',
    'email': 'User or organization email address; personal/contact data and not a public field by default.',
    'phone_e164': 'Phone number in E.164 format; direct personal identifier and authentication contact data.',
    'password_hash': 'Password verifier hash; sensitive authentication data and never returned to a client.',
    'token_hash': 'Digest of the raw bearer/session token; the raw token is never stored or returned.',
    'token_digest': 'One-way digest of an invitation token; never expose or log the raw token.',
    'csrf_hash': 'One-way digest of the session CSRF value; sensitive security metadata.',
    'verifier_hmac': 'Keyed digest used to verify an OTP without storing the OTP itself.',
    'salt': 'Per-credential random salt used by password derivation; security metadata, never a client field.',
    'subject_digest': 'Pseudonymous digest used to scope a rate-limit subject without storing its raw identifier.',
    'auth_subject': 'Authentication-provider subject identifier for the user; private identity-linkage data.',
    'display_name': "Human-readable name of the user or organization; visibility depends on the owning entity's publication state.",
    'legal_name': "Organization's legal/registered name, supplied by its authorized owner.",
    'description': 'Human-readable description of the associated destination/service/category; source and publication state govern public use.',
    'short_description': 'Short description of the associated destination for compact presentation.',
    'origin_text': 'Traveler-entered or accepted textual departure origin; not a geocoded or verified coordinate by itself.',
    'origin_location': 'Structured geographic departure location, when resolved; provenance/precision determine its reliability.',
    'canonical_name': 'Canonical name for the destination identity as selected by the editorial review process.',
    'canonical_name_fa': 'Official/local Persian canonical name for the administrative area.',
    'canonical_name_en': 'English canonical name for the administrative area.',
    'canonical_name_ar': 'Arabic canonical name for the administrative area.',
    'raw_name': 'Name exactly as received from the imported source record.',
    'raw_city': 'City/locality string exactly as received from the source record; mapping is a separate reviewed operation.',
    'raw_province': 'Province string exactly as received from the source record; mapping is a separate reviewed operation.',
    'city_name': 'City/locality label associated with the destination; free-text legacy value unless linked to an administrative-area identity.',
    'province_name': 'Province label associated with the destination; free-text legacy value unless linked to an administrative-area identity.',
    'country_code': 'Two-letter country identifier where constrained by the contract (ISO 3166-1 alpha-2 for the organization/destination API).',
    'official_code': 'Official administrative-area code from the identified source release.',
    'normalized_key': 'Normalized comparison/search key derived from the original name/alias; it is not a replacement for the raw label.',
    'aliases': 'Alternate names retained for identity matching and search; each alias must remain linked to its source or review state.',
    'tag': 'Tag value associated with the destination; public filtering depends on the approved catalogue view.',
    'category': 'Domain classification for the culinary item, constrained by the import/review taxonomy.',
    'category_key': 'Stable machine-readable category identifier.',
    'destination_type': 'Type/subtype classification for the destination; vocabulary is defined by constraints and API contracts.',
    'proposed_destination_type': "Candidate's proposed destination kind; pending review.",
    'candidate_kind': 'Kind of imported candidate (for example destination identity or discovery lead); allowed values are constrained by the candidate contract.',
    'candidate_status': 'Ingestion/review state for the candidate; it does not make it publicly searchable.',
    'identity_relation': 'Relationship between candidate and canonical destination selected during identity review.',
    'record_origin': 'Origin class of a knowledge record, distinguishing imported/curated/generated/synthetic content per application policy.',
    'record_action': 'Requested import action for this content proposal.',
    'record_key': 'Stable dataset-provided key for the imported culinary or destination record.',
    'source_record_key': 'Source-local record identity used to detect duplicate imports.',
    'source_key': 'Stable source key used for source deduplication.',
    'content_version': 'Version identifier for the localized content revision.',
    'content_status': 'Editorial state for the localized destination content.',
    'translation_status': 'Translation review state for this locale.',
    'point_role': 'Role of the spatial point (entrance, access point, representative point, or another recorded role).',
    'freshness_policy_key': 'Freshness/expiry policy for the operational assertion.',
    'value_state': 'Whether the operational assertion is known, unknown, unavailable, or another state defined by its schema.',
    'fact_type': 'Type of operational fact being asserted (such as opening/access state); exact allowed values are in constraints/API vocabulary.',
    'value_schema_version': 'Schema version used to interpret the structured operational assertion value.',
    'title': 'Human-readable title for the associated document, itinerary, or offer.',
    'label': 'Human-readable label for the associated link, access point, or event.',
    'label_fa': 'Persian human-readable label for the associated external link.',
    'name_fa': 'Persian display label for the destination category.',
    'best_travel_time': 'Season or time window described as preferable in source-backed destination metadata.',
    'difficulty': 'Qualitative difficulty value for a destination or traveler requirement; accepted vocabulary comes from API validation.',
    'suitable_transport': 'Transport suitability/preference metadata; it does not encode a verified road route or duration.',
    'local_food': 'Local-food context for a destination; each factual specialty claim needs its own evidence.',
    'local_language': 'Language/dialect context associated with a destination.',
    'local_souvenirs': 'Local-product context associated with a destination; not proof of current availability.',
    'interest_key': 'Stable identifier for a traveler interest used by the recommendation pipeline.',
    'constraint_key': 'Stable identifier for a traveler constraint; strength/operator/value determine whether it is mandatory.',
    'constraint_value': 'Typed value used to evaluate the associated traveler constraint.',
    'constraint_strength': 'Whether the constraint is hard/mandatory or soft/preferential, as defined by the trip contract.',
    'operator': 'Comparison operator used to evaluate the associated requirement/constraint.',
    'preference_key': 'Stable identifier for a persisted traveler preference.',
    'preference_value': 'Stored value for the named traveler preference; its shape is determined by preference_key and API validation.',
    'preference_source': 'Provenance indicating how the preference was supplied or inferred.',
    'consent_type': 'Purpose for which the traveler granted or revoked consent.',
    'consent_source': 'Channel or actor context through which the consent decision was recorded.',
    'consented_at': 'Time when the associated explicit consent was recorded.',
    'is_long_term': 'Whether the preference is retained as long-term rather than session/trip-scoped.',
    'trip_title': 'Traveler-facing title of the trip; synchronized from the authoritative trip requirements workflow.',
    'trip_status': 'Lifecycle state of the trip.',
    'trip_version': 'Revision/version number used for optimistic concurrency and stale-update detection.',
    'version': 'Revision number for the associated saved entity.',
    'revision': 'Revision number of the associated itinerary/provisional plan.',
    'revision_number': 'Sequential revision number of the trip requirements snapshot.',
    'itinerary_status': 'Lifecycle/verification status of the saved itinerary; unverified plans must remain labeled accordingly.',
    'provisional_itinerary_id': 'Identifier of the model-assisted/manual draft itinerary that is explicitly unverified.',
    'create_idempotency_key': 'Client-generated idempotency key used to prevent duplicate creation on retries.',
    'idempotency_key': 'Request key used to make a repeated operation safe from duplicate application.',
    'channel': 'Origin/channel of the conversation; accepted values are determined by the assistant API contract.',
    'conversation_status': 'Conversation lifecycle state.',
    'purpose': 'Purpose of the authentication or verification challenge.',
    'delivery_status': 'Delivery state reported by the configured OTP delivery adapter; unavailable is distinct from delivered.',
    'resend_after': 'Earliest time at which another challenge delivery may be requested.',
    'superseded_at': 'Time when a newer challenge superseded this challenge.',
    'locked_at': 'Time when the challenge was locked after policy limits were reached.',
    'revoked_reason': 'Recorded reason for revoking the associated session or grant.',
    'absolute_expires_at': 'Absolute session expiry, independent of activity-based idle expiry.',
    'idle_expires_at': 'Session expiry resulting from inactivity.',
    'last_seen_at': 'Most recent recorded session activity time.',
    'key_version': 'Version identifier for the secret/HMAC key used to create the verifier.',
    'login_name': 'Normalized login identifier used by the staging/local password authentication contract.',
    'account_status': 'Account lifecycle state governing whether the user may authenticate.',
    'publishable': 'Projection of current publication eligibility, not a client-controlled state.',
    'batch_key': 'Stable identifier for an idempotent import batch.',
    'dataset_import_batch_id': 'Identifier of the import batch associated with this candidate/proposal.',
    'file_id': 'Imported file record that supplied the associated row.',
    'relative_path': 'Path of an input file relative to the import package root; not an arbitrary server filesystem path.',
    'byte_size': 'Size of the source file in bytes.',
    'format': 'Detected or declared source file format.',
    'schema_signature': "Digest/signature identifying the parsed file's column/schema shape.",
    'source_locale': 'Locale declared by the source dataset/file.',
    'source_dataset_key': 'Stable identifier for the source dataset/package.',
    'row_count': 'Number of rows detected in the source file.',
    'accepted_count': 'Number of source rows accepted by the import validation step.',
    'rejected_count': 'Number of source rows rejected by the import validation step.',
    'import_status': 'Import lifecycle state for the file/batch.',
    'imported_at': 'Time when the import batch was committed to staging.',
    'parsed_at': 'Time when the source file was parsed.',
    'record_counts': 'Per-record-type counts captured for the import batch; keys/schema are defined by the importer.',
    'notes': 'Operator-entered note associated with the import or record.',
    'notes_fa': 'Persian traveler note attached to an itinerary stop.',
    'notes_by_locale': 'Traveler notes keyed by locale for the itinerary stop.',
    'rating': 'User-provided feedback rating; bounds are enforced by the feedback API/database constraints.',
    'feedback_type': 'Feedback category submitted for the associated trip/recommendation.',
    'comment': 'User feedback text; may contain personal information and is not public by default.',
    'resource_id': 'Identifier of the audited/referenced resource; interpretation depends on resource_type.',
    'resource_type': 'Type of audited/referenced resource associated with resource_id.',
    'actor_user_id': 'Authenticated user identity that performed the associated action, when applicable.',
    'actor_type': 'Class of actor performing the audited action (for example user or system).',
    'action': 'Audited operation/event name for the associated resource.',
    'correlation_id': 'Request/operation correlation identifier used to connect sanitized diagnostics.',
    'ai_model_call_id': 'Identifier of the recorded model invocation telemetry row.',
    'call_status': 'Outcome state of the recorded AI provider invocation.',
    'provider_name': 'Provider identifier used for the recorded call or space; API keys are stored elsewhere and never documented here.',
    'model_name': 'Model identifier used for the call/space; not a model credential.',
    'model_revision': 'Provider/model revision identifier used to distinguish model versions.',
    'task_type': 'Application task class for the associated model invocation.',
    'algorithm_version': 'Version identifier for the deterministic recommendation algorithm.',
    'retrieval_version': 'Version identifier for the evidence retrieval contract/configuration used by the request.',
    'request_status': 'Outcome/lifecycle state of the recommendation request.',
    'rank': 'One-based deterministic position of a recommendation within a result set.',
    'component_key': 'Stable name of a recommendation scoring component.',
    'component_reason': 'Explanation for the score contribution from the associated component.',
    'proposed_destination_key': "Candidate's proposed stable canonical destination key.",
    'proposed_name_fa': 'Persian name proposed by the imported candidate; it is not canonical until approved.',
    'proposed_latitude': 'Candidate-provided latitude, unverified until attributable geospatial review.',
    'proposed_longitude': 'Candidate-provided longitude, unverified until attributable geospatial review.',
    'target_destination_id': 'Canonical record chosen as the target of this candidate decision.',
    'target_destination_key': 'Stable canonical destination key targeted by the review/proposal.',
    'parent_destination_id': 'Parent/containing canonical destination where the reviewed relationship is explicit.',
    'admin_area_id': 'Reviewed administrative-area identity associated with the destination.',
    'parent_admin_area_id': 'Parent administrative area in the hierarchy from the referenced release.',
    'release_id': 'Administrative data release that defines this area or alias.',
    'release_key': 'Stable identifier for the administrative dataset release.',
    'authority': 'Publisher/authority responsible for the administrative dataset release.',
    'dataset_title': 'Title of the administrative dataset release.',
    'effective_from': 'Start date when the administrative release or fact applies.',
    'effective_until': 'End date when the administrative release or fact applies, if bounded.',
    'area_type': 'Hierarchy level/type for the administrative area (for example province, county, district, or city).',
    'alias': 'Alternate administrative place name retained for resolution and search.',
    'alias_type': 'Classification of the alternate name (for example spelling, transliteration, or historical name).',
    'source_type': 'Source family or evidence class.',
    'source_name': 'Display name for the registered source.',
    'publisher': 'Publisher/organization responsible for the source page or document.',
    'page_title': 'Title of the source page inspected by the reviewer.',
    'registered_url': 'Reviewed URL registered for the source identity.',
    'registration_note': 'Operator note about registering the source in the evidence registry.',
    'source_role': "Source's role in supporting the linked culinary claim.",
    'source_valid_from': "Beginning of the source claim's stated validity interval.",
    'source_valid_until': "End of the source claim's stated validity interval.",
    'verification_id': 'Identifier of a source verification review.',
    'verifier': 'Reviewer identity or system label that performed source verification; public exposure is restricted.',
    'inspected_at': 'Timestamp when the cited page/document was directly inspected.',
    'registrar_user_id': 'Operator identity that registered the source record.',
    'reviewer_user_id': 'Identifier of the authenticated reviewer who made the decision.',
    'reviewer': 'Reviewer label recorded for the approval; not a public contact field.',
    'evidence_id': 'Identifier of a candidate/source evidence record.',
    'claim_evidence_id': 'Identifier of a destination claim evidence record.',
    'claim_key': 'Stable claim identifier for linking a source to the culinary item.',
    'claim_value': 'Value asserted by the source for the named claim; it remains subject to review status.',
    'field_key': 'Field name/key for the candidate claim or localized value under review.',
    'corpus': 'Corpus/collection label to which the evidence belongs; exact values follow retrieval configuration.',
    'content_hash': 'Digest of the precise evidence content/version associated with the claim.',
    'is_source_verified': 'Derived flag indicating a linked source is verified and not revoked.',
    'is_source_synthetic': 'Derived flag indicating the source is synthetic and must not support production recommendations.',
    'is_source_revoked': 'Derived flag indicating source eligibility was revoked.',
    'is_destination_verified': 'Derived flag indicating the destination passed the required identity/verification state.',
    'is_document_processed': 'Derived flag indicating the linked document passed its processing state required by the view.',
    'provenance_source_name': 'Source name exposed as provenance in the controlled retrieval view.',
    'provenance_source_type': 'Source type exposed as provenance in the controlled retrieval view.',
    'provenance_source_url': 'Source URL exposed as provenance in the controlled retrieval view.',
    'provenance_reliability_score': 'Source reliability score carried into the retrieval projection; interpretation follows source scoring policy.',
    'assertion_id': 'Identity of a time-sensitive operational fact about a destination/access point.',
    'value': 'Typed operational fact value; interpret only with fact_type, value_state, schema version, source, and validity interval.',
    'visit_context': 'Context under which the duration estimate applies, such as a visit mode or itinerary style.',
    'source_registry_registration_events': 'Audit row recording source registry registration metadata.',
    'item_id': 'Identifier of the culinary knowledge item.',
    'item_key': 'Stable canonical key for the culinary knowledge item.',
    'item_source_id': 'Identifier linking the culinary item to one source/claim relationship.',
    'legacy_destination_id': 'Legacy destination identifier retained for compatibility with the prior culinary association.',
    'payload': 'Structured candidate/proposal content; treat as untrusted until schema validation and review.',
    'embedding_space_id': 'Embedding-space configuration used to interpret this vector.',
    'space_key': 'Stable identifier for an embedding configuration.',
    'provider_type': 'Adapter/provider family for the embedding integration; exact values follow provider configuration contract.',
    'preprocessing_version': 'Version of the text preprocessing steps used before embedding.',
    'candidate_id': 'Imported destination-candidate row associated with this review/evidence.',
    'destination_key': 'Stable canonical destination identity key; not a localized display name.',
    'canonical_destination_id': 'Destination identity resulting from the explicit candidate identity decision.',
    'raw_coordinate_role': 'Coordinate role claimed by the imported source; unverified and not an entrance claim.',
    'category_id': 'Destination category associated with the canonical destination.',
    'mapping_source': 'Provenance for assigning this destination-category relationship.',
    'sort_order': 'Stable ordering value used when presenting categories.',
    'access_point_id': 'Identity of a visitor access point linked to a destination; the point role defines what it represents.',
    'publication_id': 'Identity of the destination publication event.',
    'registered_source_id': 'Canonical source linked after registry review.',
    'proposed_source_key': "Source candidate's proposed stable source identity key.",
    'proposed_source_name': "Source candidate's proposed name; not canonical until review.",
    'proposed_publisher': "Source candidate's proposed publisher; not canonical until checked.",
    'proposed_source_type': "Source candidate's proposed source type; not verified until review.",
    'proposed_url': "Source candidate's submitted URL; must be inspected before registration/verification.",
    'proposed_license': "Source candidate's declared license; not proof of redistribution rights.",
    'source_review_id': 'Identifier of the source-candidate review decision.',
    'source_candidate_id': 'Imported source-candidate row associated with this review.',
    'inspection_at': 'Time when the source page was inspected.',
    'external_link_id': "Identifier of the destination's external booking/information link.",
    'service_type': 'Company service classification; allowed types follow the partner API vocabulary.',
    'service_key': 'Stable machine-readable service identifier.',
    'price_currency': 'Currency for the associated price.',
    'price_unit': 'Per-unit basis for the price, as validated by the partner API.',
    'availability_status': 'Availability state reported by the provider; its freshness/validity interval controls current use.',
    'availability_snapshot_id': 'Identifier of a dated availability observation.',
    'schedule_type': 'Kind of service schedule (opening window, departure, appointment, event, or other where allowed).',
    'timezone': 'IANA time-zone identifier used to interpret schedule timestamps.',
    'starts_at': 'Schedule/offer start instant; timezone semantics follow the column type and timezone field.',
    'ends_at': 'Schedule/offer end instant; timezone semantics follow the column type and timezone field.',
    'recurrence': 'Structured recurrence rule for the schedule; accepted shape is validated by the API contract.',
    'capacity_limit': 'Maximum capacity recorded for the offer/schedule; NULL means no limit was supplied, not unlimited service proof.',
    'organization_type': 'Organization category declared by the owner, constrained by partner API vocabulary.',
    'registration_country': 'Two-letter registration country code for the organization.',
    'created_by': 'User identity that created the organization record; ownership and RLS restrict access.',
    'submitted_by': 'User identity that submitted the verification case.',
    'case_id': 'Identifier for the independent organization verification case.',
    'membership_id': 'Identifier of the organization membership/role relationship.',
    'role': 'Organization-scoped membership role; allowed capabilities follow the partner authorization contract.',
    'membership_status': 'Lifecycle state of the organization membership.',
    'branch_id': 'Optional organization branch/location identity; branches are not currently editable through the supported company UI/API.',
    'service_destination_id': 'Identifier of the service-to-canonical-destination association.',
    'response_id': "Identifier of a partner's response to a consented traveler request.",
    'share_id': 'Identifier of the consented traveler-request share.',
    'revision_id': 'Identifier of the immutable traveler-request revision snapshot.',
    'traveler_decision': 'Traveler decision on the linked company response; it is owned by the traveler.',
    'is_shared': 'Whether the traveler explicitly authorized sharing of the associated request.',
    'consent_id': 'Identifier of the recorded traveler consent.',
    'feedback_id': 'Identifier of a feedback record.',
    'score_component_id': 'Identifier of a deterministic recommendation score component.',
    'document_key': 'Stable knowledge-document identity key used for import deduplication.',
    'chunk_index': 'Zero-based or one-based chunk sequence position as defined by the document splitter contract.',
    'char_count': 'Character count stored for the associated chunk/content.',
    'token_count': 'Token count measured by the configured tokenizer; it is not interchangeable with Unicode character count.',
    'document_type': 'Knowledge-document classification used by ingestion/retrieval policy.',
    'ingestion_status': 'Processing state of the knowledge document; processed does not mean source verified or destination published.',
    'dataset_import_file_id': 'Identifier of the dataset file record that supplied this import batch.',
    'count': 'Count for the associated table entity; units are the rows/items named by table context.',
    'dimension': 'Rate-limit grouping dimension (for example a route-specific or request-class key); raw subject identity is stored only as a digest in the paired subject_digest field.',
    'capability': 'Named platform permission granted to a reviewer/operator; ordinary organization memberships do not create this grant.',
    'granted_by': 'Operator user identity that issued the capability grant.',
    'consumed_by': 'User identity that redeemed the one-time invitation; raw invitation code is not stored.',
    'recorded_by': 'Authenticated reviewer/operator identity that recorded the operational assertion.',
    'data_confidence': 'Editorial confidence assigned to the destination data record; it is not a probability of visitor safety or access.',
    'license_note': 'License/rights note entered for the registered source; unknown or blank is not permission to republish.',
    'data_class': 'Import batch classification separating verified/curated source data from other data classes; exact vocabulary is enforced by the ingestion contract.',
    'approval_reference': 'Non-secret reference to the specific owner/operator approval record for this bounded geographic decision.',
    'f_table_catalog': 'Database/catalog name containing the table whose spatial column is registered in the PostGIS geography_columns view.',
    'f_table_schema': 'Schema name containing the spatial table registered in geography_columns.',
    'f_table_name': 'Relation name containing the geography column registered in geography_columns.',
    'f_geography_column': 'Column name of the registered PostGIS geography column.',
    'f_geometry_column': 'Column name of the registered PostGIS geometry column.',
    'coord_dimension': 'Coordinate dimensionality reported by PostGIS (typically 2D or 3D, subject to registered geometry type).',
    'srid': 'Spatial reference system identifier for the registered geometry/geography; interpretation uses the corresponding spatial_ref_sys row.',
    'type': 'Registered geometry/geography type name reported by PostGIS for the spatial column.',
    'auth_name': 'Authority namespace for the spatial reference definition, such as an external coordinate-system registry.',
    'auth_srid': 'Spatial reference identifier assigned by the named authority.',
    'srtext': 'Spatial reference definition in the legacy Well-Known Text representation.',
    'proj4text': 'Projection definition in the PROJ string representation; preserve as extension metadata rather than hand-editing.',
    'explanation_fa': 'Persian-language explanation attached to the recommendation; it must remain within evidence-backed recommendation claims and warnings.',
    'evidence': 'Structured evidence/provenance summary attached to the recommendation response; its claim/source links must remain traceable.',
    'sha256': 'SHA-256 checksum of the exact migration source applied to the database, used to detect migration drift.',
    'start_date': "Trip start date in the database's Gregorian DATE contract; localized/Jalali rendering is a UI concern.",
    'end_date': "Trip end date in the database's Gregorian DATE contract; inclusive/exclusive trip duration is validated by trip constraints.",
    'budget_min': "Lower bound of the accepted normalized trip budget in the currency field's denomination.",
    'budget_max': "Upper bound of the accepted normalized trip budget in the currency field's denomination.",
    'extraction_confidence': 'Confidence recorded for semantic extraction of the trip profile; it does not override explicit user corrections.',
}

# Exact semantics for columns whose names alone are not sufficient. These are
# backed by the indicated migrations, API contracts, or the extension's own
# documented catalog semantics. Keep genuinely unknown fields unresolved.
RELATION_FIELD_MEANINGS = {
    "identity.auth_rate_limits.dimension": "Rate-limit bucket dimension (login name, global, or other configured auth scope); the paired digest identifies the bucket without storing the raw identifier.",
    "identity.staging_auth_limits.dimension": "Staging-auth rate-limit bucket dimension; accepted values are defined by the CHECK constraint in migration 0016.",
    "identity.catalogue_review_grants.capability": "Catalogue capability granted to a reviewer; allowed capabilities are candidate_review, source_review, and catalogue_publish.",
    "identity.catalogue_review_grants.granted_by": "User identity of the operator who issued this catalogue capability grant; it is audit provenance, not the grantee.",
    "identity.staging_invites.consumed_by": "User identity that redeemed this one-time staging invitation; null until successful redemption.",
    "knowledge.destination_operational_assertions.recorded_by": "Authenticated reviewer/operator who recorded this time-sensitive destination assertion; approval remains separately represented by review_status.",
    "knowledge.destinations.data_confidence": "Legacy numeric confidence field constrained to 0–1; the repository has no calibrated scoring rubric, so it must not be interpreted as a probability or used to bypass review/publication gates.",
    "knowledge.production_destinations.data_confidence": "Projected legacy confidence value from the canonical destination; not a probability and not an independent writable publication decision.",
    "knowledge.source_registry_registration_events.license_note": "Reviewer-entered note describing known source license or reuse conditions; nullable when no reliable license detail was established.",
    "operations.dataset_import_batches.data_class": "Classification of imported batch provenance; migration 0018 constrains it to verified_external, user_supplied_unverified, or synthetic_fixture.",
    "operations.private_pilot_geo_approvals.approval_reference": "Non-secret reference identifying the owner approval associated with this consumed geographic visibility authorization.",
    "operations.private_pilot_geo_authorizations.approval_reference": "Non-secret reference to the owner decision authorizing the specific geographic marker; raw approval credentials are not stored here.",
    "recommendation.recommendations.explanation_fa": "Persian-language explanation for the ranked destination recommendation; it must remain consistent with the stored evidence and warning fields.",
    "recommendation.recommendations.evidence": "Structured evidence summary attached to the recommendation; each factual claim must resolve to eligible source/provenance records before being presented as verified.",
    "system.schema_migrations.sha256": "SHA-256 checksum of the exact migration source applied for this migration_id; used to detect schema-history drift.",
    "travel.trips.start_date": "Traveler-selected trip start date stored as Gregorian ISO date; relative-date extraction is resolved before persistence and Jalali is display-only.",
    "travel.trips.end_date": "Traveler-selected inclusive trip end date stored as Gregorian ISO date; nullable while duration/end date remains unknown.",
    "travel.trips.budget_min": "Lower bound of the traveler budget range in the currency stored on the same trip; nullable when no lower bound was supplied.",
    "travel.trips.budget_max": "Upper bound of the traveler budget range in the currency stored on the same trip; nullable when no upper bound was supplied.",
    "travel.trips.extraction_confidence": "Bounded 0–1 confidence indicator for the extraction snapshot; it is advisory metadata and does not confirm a field or override traveler edits.",
    "public.geography_columns.f_table_catalog": "PostGIS compatibility-view catalog name for the database containing a geometry-typed column.",
    "public.geography_columns.f_table_schema": "PostGIS compatibility-view schema name containing a geography-typed column.",
    "public.geography_columns.f_geography_column": "PostGIS compatibility-view column name whose type is geography.",
    "public.geometry_columns.f_table_catalog": "PostGIS compatibility-view catalog name for the database containing a geometry-typed column.",
    "public.geometry_columns.f_table_schema": "PostGIS compatibility-view schema name containing a geometry-typed column.",
    "public.geometry_columns.f_geometry_column": "PostGIS compatibility-view column name whose type is geometry.",
    "public.geography_columns.coord_dimension": "Coordinate dimension reported for the geography column (for example 2D or 3D), as exposed by the PostGIS compatibility view.",
    "public.geometry_columns.coord_dimension": "Coordinate dimension reported for the geometry column (for example 2D or 3D), as exposed by the PostGIS compatibility view.",
    "public.geography_columns.srid": "Spatial Reference System Identifier associated with the geography column, as exposed by PostGIS metadata.",
    "public.geometry_columns.srid": "Spatial Reference System Identifier associated with the geometry column, as exposed by PostGIS metadata.",
    "public.geography_columns.type": "PostGIS geography subtype reported by the compatibility view, such as Point or MultiPolygon.",
    "public.geometry_columns.type": "PostGIS geometry subtype reported by the compatibility view, such as Point or MultiPolygon.",
    "public.spatial_ref_sys.srid": "PostGIS spatial reference system identifier used by spatial values to identify their coordinate reference system.",
    "public.spatial_ref_sys.auth_srid": "Authority-assigned SRID corresponding to this PostGIS spatial reference definition, when known.",
    "public.spatial_ref_sys.srtext": "Well-Known Text definition of the coordinate reference system represented by this PostGIS SRID.",
    "public.spatial_ref_sys.proj4text": "PROJ parameter-string representation of the coordinate reference system; retained for compatibility with PostGIS/PROJ transformations.",
    "knowledge.chunk_embeddings.embedding": "Embedding vector for one knowledge chunk in the linked embedding space; its dimension is validated against that space by the database trigger, and vector values are not source evidence.",
    "knowledge.production_chunk_embeddings.embedding": "Published projection of the linked chunk embedding; its vector dimension follows the linked embedding-space configuration and it is not source evidence.",
    "geo.admin_area_aliases.alias_id": "Surrogate key for one alternate spelling or name associated with a canonical administrative area.",
    "identity.auth_rate_limits.window_started_at": "Timestamp marking the beginning of the authentication rate-limit window represented by this bucket.",
    "identity.otp_challenges.challenge_id": "Primary identifier for one short-lived phone-verification challenge; it is not the OTP code.",
    "identity.staging_auth_limits.window_started_at": "Timestamp marking the beginning of a staging authentication rate-limit window.",
    "identity.staging_invites.invite_id": "Primary identifier for one operator-issued, single-use staging invitation; the invitation secret is stored as a verifier, not in this identifier.",
    "identity.user_preferences.preference_id": "Primary identifier for one persisted user preference record.",
    "identity.verified_phones.challenge_id": "Nullable provenance link to the OTP challenge that verified this phone; it is not a reusable authentication credential.",
    "identity.web_sessions.session_id": "Primary identifier for a server-side session record; bearer and CSRF values are represented by separate digests.",
    "integration.outbound_clicks.outbound_click_id": "Primary identifier for one recorded outbound-link click event.",
    "integration.outbound_clicks.session_id": "Optional session reference associated with the outbound click for bounded attribution; it is not exposed as a login token.",
    "integration.outbound_clicks.clicked_at": "Timestamp at which the traveler activated the curated external link.",
    "knowledge.active_embedding_spaces.lifecycle_status": "Lifecycle state projected for the embedding configuration exposed by this active-space view.",
    "knowledge.chunk_embeddings.chunk_embedding_id": "Primary identifier for one stored embedding vector linked to a knowledge chunk and embedding space.",
    "knowledge.destination_aliases.alias_id": "Primary identifier for one alternate destination name linked to a canonical destination.",
    "knowledge.destination_candidate_reviews.review_id": "Primary identifier for one append-only reviewer decision on an imported destination candidate.",
    "knowledge.destination_enrichment_proposal_sources.proposal_source_id": "Primary identifier for one source-to-enrichment-proposal evidence link.",
    "knowledge.destination_enrichment_proposal_sources.proposal_id": "Foreign-key reference to the enrichment proposal supported by this source record.",
    "knowledge.destination_enrichment_proposals.proposal_id": "Primary identifier for one reviewable proposed change to an existing canonical destination.",
    "knowledge.destination_visit_duration_evidence.duration_id": "Primary identifier for one source-backed visit-duration observation for a destination.",
    "knowledge.embedding_spaces.lifecycle_status": "Lifecycle state of an embedding provider/model/dimension configuration; active status does not by itself establish retrieval quality.",
    "knowledge.production_chunk_embeddings.chunk_embedding_id": "Identifier of the source chunk-embedding record represented by this production projection; not an independently writable key.",
    "knowledge.source_registry_registration_events.registration_id": "Primary identifier for one source-registry registration and rights-review audit event.",
    "operations.audit_events.audit_event_id": "Primary identifier for one security or business audit event; event payloads remain subject to minimization and access policy.",
    "operations.private_pilot_geo_approvals.authorization_id": "Foreign-key identity of the one-use geographic authorization consumed by this approval event.",
    "operations.private_pilot_geo_authorizations.authorization_id": "Primary identifier for a narrowly scoped owner authorization to expose one approximate geographic marker.",
    "public.geography_columns.f_table_name": "PostGIS compatibility-view name of the table containing the geography column.",
    "public.geometry_columns.f_table_name": "PostGIS compatibility-view name of the table containing the geometry column.",
    "public.rahgard_private_pilot_marker.marker_value": "Opaque deployment/test guard marker used to bind privileged pilot operations to the intended isolated database; not a user-facing value.",
    "public.spatial_ref_sys.auth_name": "Name of the standards authority that assigned the corresponding auth_srid, when available.",
    "recommendation.recommendation_requests.completed_at": "Timestamp at which deterministic recommendation processing reached its completed state; null while pending or failed.",
    "system.schema_migrations.migration_id": "Stable migration identifier recorded in the applied-schema ledger; it is the logical migration name, not the source checksum.",
    "system.schema_migrations.applied_at": "Timestamp when this migration ledger entry was committed by the migration runner.",
    "travel.itinerary_stops.itinerary_stop_id": "Primary identifier for one editable stop within a saved itinerary.",
    "travel.trip_constraints.constraint_id": "Primary identifier for one structured hard or soft constraint associated with a traveler trip.",
    "travel.trip_constraints.source_message_id": "Optional reference to the conversation message that supplied evidence for this trip constraint.",
    "travel.trip_interests.trip_interest_id": "Primary identifier for one weighted traveler interest attached to a trip.",
}

TABLE_CONTEXT = {
    "conversation.assistant_turns": "durable assistant turn/idempotency and result state",
    "conversation.conversations": "traveler conversation lifecycle and structured context",
    "conversation.messages": "individual traveler/assistant conversation messages and provider diagnostics",
    "geo.admin_area_aliases": "alternate names for an administrative area in a specific release",
    "geo.admin_area_releases": "versioned authoritative administrative-boundary source release",
    "geo.admin_areas": "administrative hierarchy node with names and sourced geometry",
    "identity.auth_rate_limits": "privacy-preserving authentication rate-limit counter",
    "identity.catalogue_review_grants": "operator capability grant and revocation record",
    "identity.otp_challenges": "one-time phone authentication challenge and verifier state",
    "identity.staging_auth_limits": "staging authentication rate-limit counter",
    "identity.staging_invites": "single-use staging invitation digest and lifecycle",
    "identity.staging_password_credentials": "staging account password verifier material",
    "identity.user_consents": "versioned user privacy/sharing consent decision",
    "identity.user_preferences": "persisted traveler preference and provenance",
    "identity.users": "traveler/account identity and authentication profile",
    "identity.verified_phones": "verified phone-to-user association",
    "identity.web_sessions": "hashed session and CSRF lifecycle; no raw bearer values",
    "integration.external_links": "curated external destination/service link",
    "integration.outbound_clicks": "user action telemetry for an external link",
    "knowledge.catalogue_publication_events": "audited publication decision linking candidate, destination and evidence",
    "knowledge.chunk_embeddings": "vector value associated with a knowledge chunk and embedding space",
    "knowledge.culinary_item_sources": "provenance relationship between a culinary item claim and a source",
    "knowledge.culinary_knowledge_items": "reviewable culinary knowledge content and publication state",
    "knowledge.destination_access_points": "sourced visitor access/location point with explicit point role",
    "knowledge.destination_aliases": "alternate destination name linked to canonical identity",
    "knowledge.destination_candidate_evidence": "claim-level evidence attached to a staged destination candidate",
    "knowledge.destination_candidate_reviews": "identity/review decisions for imported destination candidates",
    "knowledge.destination_candidates": "untrusted imported destination identity or discovery lead pending review",
    "knowledge.destination_categories": "controlled destination category vocabulary",
    "knowledge.destination_category_map": "destination-to-category association and provenance",
    "knowledge.destination_claim_evidence": "reviewed claim-level evidence and publication eligibility state",
    "knowledge.destination_enrichment_proposal_sources": "source relationship for a proposed destination change",
    "knowledge.destination_enrichment_proposals": "reviewable destination enrichment/change proposal",
    "knowledge.destination_localizations": "localized canonical destination names/descriptions and review state",
    "knowledge.destination_operational_assertions": "time-sensitive opening/access/operational fact with freshness metadata",
    "knowledge.destination_sources": "destination-to-registered-source relationship and validity",
    "knowledge.destination_tags": "destination search/filter tag",
    "knowledge.destination_visit_duration_evidence": "source-backed visit-duration interval and context",
    "knowledge.destinations": "canonical tourism destination identity, location, locality and review state",
    "knowledge.embedding_spaces": "embedding provider/model/dimension/lifecycle configuration",
    "knowledge.knowledge_chunks": "bounded text segment from a source document, with hash and counts",
    "knowledge.knowledge_documents": "retrieved/processed source document with destination and provenance links",
    "knowledge.knowledge_sources": "registered source identity and verification/reliability state",
    "operations.ai_model_calls": "internal bounded model-call telemetry, not a conversation transcript",
    "operations.audit_events": "internal security/business audit event metadata",
    "operations.dataset_import_batches": "idempotent import execution and source checksum summary",
    "operations.dataset_import_files": "individual source file parse and acceptance/rejection counts",
    "operations.feedback": "private traveler feedback associated with trip/conversation/recommendation",
    "operations.private_pilot_geo_approvals": "operator-approved map visibility decision bound to a marker and decision digest",
    "operations.private_pilot_geo_authorizations": "scoped authorization for exact pilot geographic records",
    "partner.availability_snapshots": "dated company-reported availability observation",
    "partner.branches": "optional organization branch/location schema; no supported company branch form/API currently exists",
    "partner.invitations": "organization-scoped member invitation lifecycle",
    "partner.memberships": "organization-scoped user role and membership state",
    "partner.offers": "company service offer and validity/capacity data",
    "partner.organizations": "company legal/display profile and separate application, verification, participation states",
    "partner.platform_grants": "operator-only platform capability grants; no normal company CRUD surface",
    "partner.prices": "time-bounded company price observations with currency/unit/tax context",
    "partner.review_events": "append-only audit events for independent organization review decisions",
    "partner.schedules": "company service schedule in an explicit IANA time zone",
    "partner.service_destinations": "company service association with an approved canonical destination",
    "partner.service_localizations": "localized company service name and description",
    "partner.services": "company-owned travel service profile with editorial/publication lifecycle",
    "partner.traveler_request_inbox": "tenant-filtered view of explicitly shared traveler requests and revisions",
    "partner.traveler_request_revisions": "immutable versioned snapshot of traveler-approved shared request data",
    "partner.traveler_request_shares": "traveler-authorized organization/request sharing permission and revocation state",
    "partner.trip_company_responses": "tenant-scoped company response and traveler decision for a shared request",
    "partner.verification_cases": "organization evidence packet submitted for independent review",
    "recommendation.recommendation_requests": "input/version snapshot and lifecycle of deterministic recommendation execution",
    "recommendation.recommendation_score_components": "explainable score contribution for one recommendation",
    "recommendation.recommendations": "ranked destination results with warnings/evidence and localized explanation",
    "system.schema_migrations": "applied migration identity, checksum and time; system-managed, not an application form",
    "travel.itineraries": "saved versioned itinerary and verification state",
    "travel.itinerary_stops": "ordered stop and scheduling/note data for a saved itinerary",
    "travel.provisional_itineraries": "editable model/manual itinerary draft explicitly marked unverified",
    "travel.trip_constraints": "hard/soft traveler constraint and its evidence/provenance",
    "travel.trip_interests": "weighted traveler interest and mandatory-preference flag",
    "travel.trip_requirement_revisions": "immutable revision snapshots of the accepted trip requirements",
    "travel.trips": "authoritative traveler trip profile, original budget denomination and revision",
}


def type_format(pg_type: str) -> str:
    t = pg_type.lower()
    if t == "vector":
        return "pgvector vector value; dimension is stored in the linked embedding-space row and enforced by the database trigger. No fixed dimension is implied by this column type."
    if t == "name":
        return "PostgreSQL identifier-name type; maximum length is the PostgreSQL NAMEDATALEN limit (63 bytes in standard builds)."
    if t.endswith("[]"):
        return f"PostgreSQL array of `{pg_type[:-2]}` values; each element follows the base type and database constraints/API contract."
    if t in {"json", "jsonb"}:
        return "JSON object/array/scalar; exact shape is validated by the consuming contract."
    if t in {"date"}:
        return "Gregorian ISO date YYYY-MM-DD in storage; localized calendars are presentation only."
    if t.startswith("timestamp") or t.startswith("time"):
        return f"PostgreSQL `{pg_type}`; timezone presence is part of the type and must not be inferred."
    if t in {"numeric", "double precision", "real"} or t.startswith("numeric("):
        return f"PostgreSQL `{pg_type}`; unit/currency comes from the paired domain fields, never from the numeric type."
    if t in {"geometry", "geography"} or t.startswith("geometry(") or t.startswith("geography("):
        return f"PostGIS `{pg_type}`; interpret SRID and coordinate role from relation constraints/companion fields."
    return f"PostgreSQL `{pg_type}`; value range and accepted vocabulary follow listed database constraints and API validation."


def ownership(schema: str, table: str) -> str:
    if schema == "partner":
        return "organization owner/member for tenant fields; independent platform reviewer for review/audit fields"
    if schema in {"identity", "conversation", "travel"}:
        return "traveler/account owner, with authentication/system-managed fields writable only by backend services"
    if schema == "knowledge":
        return "catalogue/source editor or import operator; publication fields require an authorized reviewer"
    if schema == "geo":
        return "administrative data steward/import process"
    if schema == "operations":
        return "backend/system operator; no end-user generic write surface"
    if schema == "recommendation":
        return "recommendation service; input snapshots may contain traveler data"
    return "PostgreSQL/PostGIS extension or platform metadata owner"


def sensitivity(schema: str, table: str, field: str) -> str:
    low = field.lower()
    if schema == "identity" and table in {
        "otp_challenges", "staging_invites", "staging_password_credentials",
        "web_sessions", "catalogue_review_grants", "auth_rate_limits", "staging_auth_limits",
    }:
        return "restricted_authentication_or_authorization_metadata"
    if any(k in low for k in ("password", "token", "verifier", "salt", "csrf", "secret", "credential", "phone_e164", "email")):
        return "restricted_authentication_or_direct_identifier"
    if schema in {"identity", "conversation", "travel"} or any(k in low for k in ("raw_record", "raw_content", "requirement", "origin_text", "budget_raw", "comment", "metadata")):
        return "private_traveler_or_import_data"
    if schema == "partner":
        return "confidential_company_data; expose only through tenant and publication policy"
    if schema == "operations":
        return "internal_operational_or_audit_metadata"
    if schema == "knowledge" and field in {"canonical_name", "description", "latitude", "longitude"}:
        return "public_only_when_published_and_source_eligible"
    if schema in {"public", "geo"}:
        return "technical_or_administrative_metadata"
    return "internal_catalogue_or_recommendation_metadata"


def surfaces(schema: str, table: str, field: str) -> tuple[str, str]:
    if schema == "partner":
        if table in {"platform_grants", "review_events", "verification_cases"}:
            return ("platform reviewer queue or append-only audit; tenant filters apply", "review API only for granted operator; company submits evidence only")
        return ("/api/v1/partners organization workspace; filtered by membership/RLS and publication/consent", "organization-scoped partner API with CSRF and tenant RLS")
    if schema == "identity":
        return ("authentication/session endpoints only; secrets/digests never returned", "backend auth service only; no direct client table writes")
    if schema in {"conversation", "travel"}:
        return ("authenticated traveler conversation/trip endpoints, owner-scoped", "authenticated traveler endpoints with CSRF, ownership, and revision checks")
    if schema == "knowledge":
        if table.startswith("production_"):
            return ("published catalogue/retrieval API with source/publication filters", "database view only; no direct end-user writes")
        return ("operator review API or controlled published projection", "authorized catalogue/import/review service; candidate data is not public")
    if schema == "recommendation":
        return ("authenticated recommendation response; private input snapshot is not exposed wholesale", "deterministic recommendation service")
    if schema == "geo":
        return ("resolved administrative metadata/map filters where explicitly exposed", "administrative import/review tooling only")
    if schema == "operations":
        return ("internal diagnostics/audit interfaces with minimization", "backend operator/job only; no generic user CRUD")
    return ("PostgreSQL/PostGIS metadata APIs only when needed", "extension/platform managed")


def source_files(schema: str, table: str, sql_files: list[Path]) -> list[str]:
    matches: list[Path] = []
    pattern = re.compile(r"\b(?:TABLE|VIEW|MATERIALIZED VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\"?" + re.escape(schema) + r"\"?\.)\"?" + re.escape(table) + r"\b", re.I)
    for path in sql_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        if pattern.search(text):
            matches.append(path)
    return [p.relative_to(ROOT).as_posix() for p in matches[:3]]


def main() -> int:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    current = json.loads(DESCRIPTIONS.read_text(encoding="utf-8"))
    sql_files = list((ROOT / "engineering").rglob("*.sql"))
    resolved = unresolved = 0
    for relation in snapshot.get("relations", []):
        db = relation["database"]
        schema, table = relation["relation"]["schema"], relation["relation"]["name"]
        key = f"{db}.{schema}.{table}"
        entry = current.setdefault(key, {})
        legacy_entry = current.get(f"{schema}.{table}", {})
        metadata = entry.setdefault("_field_metadata", {})
        table_context = TABLE_CONTEXT.get(f"{schema}.{table}")
        migration_paths = source_files(schema, table, sql_files)
        for column in relation["columns"]:
            name, pg_type = column["name"], column["pg_type"]
            field_key = f"{schema}.{table}.{name}"
            if column.get("comment"):
                meaning = column["comment"]
            else:
                meaning = entry.get(name, legacy_entry.get(name))
            if isinstance(meaning, dict):
                meaning = meaning.get("meaning")
            meaning = RELATION_FIELD_MEANINGS.get(field_key, meaning)
            if not isinstance(meaning, str) or not meaning.strip():
                meaning = FIELD_MEANINGS.get(name)
            if not meaning and name.endswith("_id"):
                meaning = f"Identifier linking this {table.replace('_', ' ')} record to the related entity; the table's foreign-key constraint names the referenced relation."
            if not meaning and name.endswith("_at"):
                meaning = f"Timestamp for the `{name[:-3].replace('_', ' ')}` event on this {table.replace('_', ' ')} record; PostgreSQL type defines timezone behavior."
            if not meaning and name.startswith("is_"):
                meaning = f"Boolean flag for whether the associated `{name[3:].replace('_', ' ')}` condition applies to this {table.replace('_', ' ')} record."
            if not meaning and name.endswith("_sha256"):
                meaning = f"SHA-256 integrity digest associated with this {table.replace('_', ' ')} record; it is not an authentication secret."
            if not meaning and name.endswith("_url"):
                meaning = f"URL associated with the `{name[:-4].replace('_', ' ')}` relationship; exact rights and publication eligibility depend on the associated source record."
            if not meaning and name.endswith("_by_locale"):
                meaning = "Localized text/values keyed by locale; exact JSON schema is enforced by the consuming API contract."
            if not meaning and name.endswith("_count"):
                meaning = f"Count of `{name[:-6].replace('_', ' ')}` items/rows recorded for the associated {table.replace('_', ' ')}."
            if not meaning and name.endswith("_status"):
                meaning = f"Lifecycle state of the associated {table.replace('_', ' ')}; use this table's CHECK/enum constraints and API contract for allowed values."
            if not meaning and name.endswith("_type"):
                meaning = f"Classification of the associated {table.replace('_', ' ')}; allowed values follow database constraints and the owning API contract."
            if not meaning and name.endswith("_name"):
                meaning = f"Human-readable name for the associated `{name[:-5].replace('_', ' ')}`; source/review/publication state controls public use."
            if not meaning and name.endswith("_key"):
                meaning = f"Stable machine-readable key for the associated `{name[:-4].replace('_', ' ')}` identity or vocabulary."
            if not meaning and name.endswith("_value"):
                meaning = f"Value for the associated `{name[:-6].replace('_', ' ')}` field; schema and meaning are determined by the paired key/type fields and API contract."
            if not meaning and name.endswith("_text"):
                meaning = f"Text value for the associated `{name[:-5].replace('_', ' ')}`; retain source/provenance and privacy context."
            if not meaning and name.endswith("_score"):
                meaning = f"Score for the associated `{name[:-6].replace('_', ' ')}`; scale and interpretation follow the scoring contract."
            if not meaning and name.endswith("_minutes"):
                meaning = f"Time quantity in minutes for the associated `{name[:-8].replace('_', ' ')}`."
            if not meaning and name.endswith("_name"):
                meaning = f"Name of the associated `{name[:-5].replace('_', ' ')}`."
            if not meaning and name.endswith("_digest"):
                meaning = f"One-way digest used to identify the associated `{name[:-7].replace('_', ' ')}` without storing its raw value."
            is_unresolved = not meaning or "Business meaning of `" in meaning
            resolution = "unresolved" if is_unresolved else "resolved"
            if not meaning:
                meaning = f"Business meaning of `{schema}.{table}.{name}` is not established from the checked-in schema, migration, and API sources; owner/domain review is required."
            if is_unresolved:
                unresolved += 1
            else:
                resolved += 1
            paths = ["docs/database/live-schema/catalog_snapshot.json", *migration_paths]
            if schema in {"partner"}:
                paths += ["backend/app/api/partners.py", "frontend/src/partners/PartnerWorkspace.tsx"]
            elif schema in {"identity"}:
                paths += ["backend/app/api/auth.py"]
            elif schema in {"conversation"}:
                paths += ["backend/app/api/assistant.py", "backend/app/modules/trip/assistant_turns.py"]
            elif schema in {"travel"}:
                paths += ["backend/app/api/traveler.py", "backend/app/modules/trip/repository.py"]
            elif schema in {"recommendation"}:
                paths += ["backend/app/modules/recommendation/service.py"]
            elif schema == "knowledge":
                paths += ["backend/app/api/catalogue_review.py", "backend/app/modules/retrieval/contracts.py"]
            elif schema == "geo":
                paths += ["engineering/pilot/sql/018_national_catalogue_ingestion.sql"]
            if pg_type.lower().startswith(("timestamp", "time")) or pg_type.lower() == "date":
                paths.append(OFFICIAL_SOURCES["postgres_datetime"])
            elif pg_type.lower() in {"json", "jsonb"}:
                paths.append(OFFICIAL_SOURCES["postgres_json"])
            elif pg_type.lower() == "vector":
                paths.append(OFFICIAL_SOURCES["pgvector"])
            else:
                paths.append(OFFICIAL_SOURCES["postgres_types"])
            if schema == "public":
                paths.append(OFFICIAL_SOURCES["postgis_management"])
                if table == "rahgard_private_pilot_marker":
                    paths.append("engineering/pilot/Run-National-Catalogue-Browser-E2E.ps1")
            evidence = list(dict.fromkeys(path for path in paths if (ROOT / path).is_file() or path.startswith("https://")))
            sensitivity_value = sensitivity(schema, table, name)
            owner = ownership(schema, table)
            read_surface, write_surface = surfaces(schema, table, name)
            allowed_values = []
            for constraint in relation.get("constraints", []):
                definition = constraint.get("definition", "")
                if name in definition and constraint.get("type") == "c":
                    allowed_values.append(definition)
            format_text = type_format(pg_type)
            if allowed_values:
                format_text += " DB CHECK: " + " | ".join(allowed_values)
            if relation["relation"].get("kind") in {"v", "m"}:
                format_text += " This is a projection/view column; it is not an independent writable field."
            metadata[name] = {
                "meaning": meaning,
                "resolution": resolution,
                "accepted_format_units_enums": format_text,
                "source_evidence": evidence,
                "sensitivity": sensitivity_value,
                "owner": owner,
                "read_surface": read_surface,
                "write_surface": write_surface,
                "table_context": table_context or f"{schema}.{table}; relation semantics must be checked against listed SQL/API sources",
            }
            # Keep backward compatibility for the current renderer and other
            # consumers: the legacy column entry remains a plain meaning string.
            entry[name] = meaning
    current["_documentation_summary"] = {
        "snapshot_created_utc": snapshot.get("created_utc"),
        "source_release": snapshot.get("source_release"),
        "resolved_fields": resolved,
        "unresolved_fields": unresolved,
        "completion_policy": "unresolved fields remain explicitly flagged; do not mark complete until zero unresolved fields and database coverage is exhaustive for the authorized namespace",
    }
    DESCRIPTIONS.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"resolved_fields": resolved, "unresolved_fields": unresolved,
                      "snapshot_columns": sum(len(r["columns"]) for r in snapshot.get("relations", [])),
                      "output": DESCRIPTIONS.as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
