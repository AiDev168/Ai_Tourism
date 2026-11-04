BEGIN;

-- One fully synthetic graph exercises FK paths across identity, conversation,
-- trip extraction, recommendations, scoring, editable itinerary, outbound links
-- and feedback. These records are QA/demo-only and are never production data.

INSERT INTO identity.users
    (user_id, auth_subject, email, display_name, account_status, is_synthetic)
VALUES
    ('10000000-0000-4000-8000-000000000001', 'qa-subject-001',
     'qa.user@ai-tourism.example.invalid', 'کاربر آزمایشی', 'active', TRUE)
ON CONFLICT (user_id) DO UPDATE SET
    auth_subject = EXCLUDED.auth_subject,
    email = EXCLUDED.email,
    display_name = EXCLUDED.display_name,
    account_status = 'active',
    is_synthetic = TRUE,
    updated_at = NOW();

INSERT INTO identity.user_consents
    (consent_id, user_id, consent_type, policy_version, is_granted,
     granted_at, consent_source, is_synthetic)
VALUES
    ('11000000-0000-4000-8000-000000000001',
     '10000000-0000-4000-8000-000000000001',
     'privacy_policy', 'qa-v1', TRUE, '2027-01-01T09:00:00Z', 'qa_seed', TRUE)
ON CONFLICT (consent_id) DO UPDATE SET
    is_granted = EXCLUDED.is_granted,
    granted_at = EXCLUDED.granted_at,
    is_synthetic = TRUE;

INSERT INTO identity.user_preferences
    (preference_id, user_id, preference_key, preference_value, weight,
     confidence, preference_source, is_long_term, is_synthetic)
VALUES
    ('12000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001',
     'travel_style', '{"values":["nature","family"]}'::JSONB, 0.9, 0.95, 'user_explicit', TRUE, TRUE),
    ('12000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000001',
     'budget_level', '{"value":"moderate"}'::JSONB, 0.8, 0.9, 'user_explicit', TRUE, TRUE),
    ('12000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000001',
     'transport', '{"values":["private_car"]}'::JSONB, 0.6, 0.8, 'user_explicit', TRUE, TRUE)
ON CONFLICT (preference_id) DO UPDATE SET
    preference_value = EXCLUDED.preference_value,
    weight = EXCLUDED.weight,
    confidence = EXCLUDED.confidence,
    is_synthetic = TRUE,
    updated_at = NOW();

INSERT INTO conversation.conversations
    (conversation_id, user_id, channel, language_code, conversation_status,
     structured_context, is_synthetic, started_at, last_message_at)
VALUES
    ('20000000-0000-4000-8000-000000000001',
     '10000000-0000-4000-8000-000000000001', 'pwa', 'fa', 'completed',
     '{"fixture":"synthetic-e2e-v1","flow":"trip_recommendation"}'::JSONB,
     TRUE, '2027-01-01T09:00:00Z', '2027-01-01T09:02:00Z')
ON CONFLICT (conversation_id) DO UPDATE SET
    structured_context = EXCLUDED.structured_context,
    conversation_status = 'completed',
    is_synthetic = TRUE,
    last_message_at = EXCLUDED.last_message_at;

INSERT INTO conversation.messages
    (message_id, conversation_id, role, content, message_type, metadata, is_synthetic, created_at)
VALUES
    ('21000000-0000-4000-8000-000000000001', '20000000-0000-4000-8000-000000000001',
     'user', 'برای یک سفر خانوادگی سه روزه، طبیعت خنک و مسیر نه‌چندان سخت پیشنهاد بده.',
     'text', '{"fixture":true,"step":1}'::JSONB, TRUE, '2027-01-01T09:00:00Z'),
    ('21000000-0000-4000-8000-000000000002', '20000000-0000-4000-8000-000000000001',
     'assistant', 'برای محدود کردن پیشنهادها، مبدأ و حدود بودجه را مشخص می‌کنی؟',
     'text', '{"fixture":true,"step":2}'::JSONB, TRUE, '2027-01-01T09:00:30Z'),
    ('21000000-0000-4000-8000-000000000003', '20000000-0000-4000-8000-000000000001',
     'user', 'مبدأ شهر آزمایشی و بودجه متوسط است؛ با خودرو شخصی سفر می‌کنیم.',
     'text', '{"fixture":true,"step":3}'::JSONB, TRUE, '2027-01-01T09:01:00Z'),
    ('21000000-0000-4000-8000-000000000004', '20000000-0000-4000-8000-000000000001',
     'assistant', 'سه گزینه آزمایشی بر اساس طبیعت، دشواری مسیر و سفر خانوادگی مرتب شده‌اند.',
     'text', '{"fixture":true,"step":4,"not_a_real_llm_call":true}'::JSONB, TRUE, '2027-01-01T09:02:00Z')
ON CONFLICT (message_id) DO UPDATE SET
    content = EXCLUDED.content,
    metadata = EXCLUDED.metadata,
    is_synthetic = TRUE;

INSERT INTO travel.trips
    (trip_id, user_id, conversation_id, trip_title, origin_text,
     start_date, end_date, duration_days, budget_min, budget_max,
     currency, traveler_count, extracted_requirements, extraction_confidence,
     trip_status, is_synthetic)
VALUES
    ('30000000-0000-4000-8000-000000000001',
     '10000000-0000-4000-8000-000000000001',
     '20000000-0000-4000-8000-000000000001',
     'سفر خانوادگی آزمایشی سه‌روزه', 'شهر آزمایشی QA',
     '2027-04-10', '2027-04-12', 3, 10000000, 25000000,
     'IRR', 3,
     '{"travel_style":["nature","family"],"transport":"private_car","difficulty":"easy_to_moderate","season":"spring"}'::JSONB,
     0.92, 'ready', TRUE)
ON CONFLICT (trip_id) DO UPDATE SET
    extracted_requirements = EXCLUDED.extracted_requirements,
    trip_status = 'ready',
    is_synthetic = TRUE,
    updated_at = NOW();

INSERT INTO travel.trip_constraints
    (constraint_id, trip_id, constraint_key, operator, constraint_value,
     constraint_strength, weight, confidence, source_message_id, is_synthetic)
VALUES
    ('31000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001',
     'duration_days', 'equals', '3'::JSONB, 'hard', 1.0, 0.99,
     '21000000-0000-4000-8000-000000000003', TRUE),
    ('31000000-0000-4000-8000-000000000002', '30000000-0000-4000-8000-000000000001',
     'transport', 'equals', '"private_car"'::JSONB, 'hard', 1.0, 0.95,
     '21000000-0000-4000-8000-000000000003', TRUE),
    ('31000000-0000-4000-8000-000000000003', '30000000-0000-4000-8000-000000000001',
     'difficulty', 'less_than_or_equal', '"moderate"'::JSONB, 'hard', 1.0, 0.9,
     '21000000-0000-4000-8000-000000000001', TRUE)
ON CONFLICT (constraint_id) DO UPDATE SET
    constraint_value = EXCLUDED.constraint_value,
    is_synthetic = TRUE;

INSERT INTO travel.trip_interests
    (trip_interest_id, trip_id, interest_key, weight, is_required, is_synthetic)
VALUES
    ('32000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', 'nature', 0.95, TRUE, TRUE),
    ('32000000-0000-4000-8000-000000000002', '30000000-0000-4000-8000-000000000001', 'family', 0.85, TRUE, TRUE),
    ('32000000-0000-4000-8000-000000000003', '30000000-0000-4000-8000-000000000001', 'cool_weather', 0.7, FALSE, TRUE)
ON CONFLICT (trip_interest_id) DO UPDATE SET
    weight = EXCLUDED.weight,
    is_required = EXCLUDED.is_required,
    is_synthetic = TRUE;

INSERT INTO recommendation.recommendation_requests
    (recommendation_request_id, trip_id, conversation_id, algorithm_version,
     retrieval_version, input_snapshot, request_status, is_synthetic, completed_at)
VALUES
    ('40000000-0000-4000-8000-000000000001',
     '30000000-0000-4000-8000-000000000001',
     '20000000-0000-4000-8000-000000000001',
     'qa-rule-set-v1', 'qa-retrieval-contract-v1',
     '{"fixture":true,"note":"Scores are fabricated only to test persistence and joins."}'::JSONB,
     'completed', TRUE, '2027-01-01T09:02:30Z')
ON CONFLICT (recommendation_request_id) DO UPDATE SET
    input_snapshot = EXCLUDED.input_snapshot,
    request_status = 'completed',
    is_synthetic = TRUE,
    completed_at = EXCLUDED.completed_at;

INSERT INTO recommendation.recommendations
    (recommendation_id, recommendation_request_id, destination_id, rank,
     final_score, confidence, explanation_fa, warnings, is_synthetic)
VALUES
    ('41000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000001',
     (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-forest-01'),
     1, 0.920000, 0.90,
     'توصیه کاملاً آزمایشی: این گزینه برای آزمون اتصال پیشنهاد به مقصد و امتیازها استفاده می‌شود.',
     '["synthetic_fixture_only"]'::JSONB, TRUE),
    ('41000000-0000-4000-8000-000000000002', '40000000-0000-4000-8000-000000000001',
     (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-mountain-02'),
     2, 0.835000, 0.85,
     'توصیه کاملاً آزمایشی: مقصد دوم صرفاً برای آزمون رتبه‌بندی است.',
     '["synthetic_fixture_only"]'::JSONB, TRUE),
    ('41000000-0000-4000-8000-000000000003', '40000000-0000-4000-8000-000000000001',
     (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-waterfall-03'),
     3, 0.761000, 0.80,
     'توصیه کاملاً آزمایشی: مقصد سوم صرفاً برای آزمون روابط پایگاه داده است.',
     '["synthetic_fixture_only"]'::JSONB, TRUE)
ON CONFLICT (recommendation_id) DO UPDATE SET
    rank = EXCLUDED.rank,
    final_score = EXCLUDED.final_score,
    explanation_fa = EXCLUDED.explanation_fa,
    warnings = EXCLUDED.warnings,
    is_synthetic = TRUE;

INSERT INTO recommendation.recommendation_score_components
    (score_component_id, recommendation_id, component_key, raw_score,
     normalized_score, weight, weighted_score, component_reason, is_synthetic)
VALUES
    ('42000000-0000-4000-8000-000000000001', '41000000-0000-4000-8000-000000000001', 'interest_match', 0.95, 0.95, 0.40, 0.380000, 'synthetic QA score', TRUE),
    ('42000000-0000-4000-8000-000000000002', '41000000-0000-4000-8000-000000000001', 'family_fit', 0.90, 0.90, 0.30, 0.270000, 'synthetic QA score', TRUE),
    ('42000000-0000-4000-8000-000000000003', '41000000-0000-4000-8000-000000000001', 'difficulty_fit', 0.90, 0.90, 0.30, 0.270000, 'synthetic QA score', TRUE),
    ('42000000-0000-4000-8000-000000000004', '41000000-0000-4000-8000-000000000002', 'interest_match', 0.85, 0.85, 0.40, 0.340000, 'synthetic QA score', TRUE),
    ('42000000-0000-4000-8000-000000000005', '41000000-0000-4000-8000-000000000002', 'family_fit', 0.85, 0.85, 0.30, 0.255000, 'synthetic QA score', TRUE),
    ('42000000-0000-4000-8000-000000000006', '41000000-0000-4000-8000-000000000002', 'difficulty_fit', 0.80, 0.80, 0.30, 0.240000, 'synthetic QA score', TRUE),
    ('42000000-0000-4000-8000-000000000007', '41000000-0000-4000-8000-000000000003', 'interest_match', 0.80, 0.80, 0.40, 0.320000, 'synthetic QA score', TRUE),
    ('42000000-0000-4000-8000-000000000008', '41000000-0000-4000-8000-000000000003', 'family_fit', 0.75, 0.75, 0.30, 0.225000, 'synthetic QA score', TRUE),
    ('42000000-0000-4000-8000-000000000009', '41000000-0000-4000-8000-000000000003', 'difficulty_fit', 0.72, 0.72, 0.30, 0.216000, 'synthetic QA score', TRUE)
ON CONFLICT (score_component_id) DO UPDATE SET
    normalized_score = EXCLUDED.normalized_score,
    weighted_score = EXCLUDED.weighted_score,
    is_synthetic = TRUE;

INSERT INTO travel.itineraries
    (itinerary_id, trip_id, recommendation_request_id, version, title,
     day_count, itinerary_status, is_synthetic)
VALUES
    ('50000000-0000-4000-8000-000000000001',
     '30000000-0000-4000-8000-000000000001',
     '40000000-0000-4000-8000-000000000001',
     1, 'برنامه سه روزه آزمایشی', 3, 'presented', TRUE)
ON CONFLICT (itinerary_id) DO UPDATE SET
    title = EXCLUDED.title,
    day_count = EXCLUDED.day_count,
    itinerary_status = 'presented',
    is_synthetic = TRUE,
    updated_at = NOW();

INSERT INTO travel.itinerary_stops
    (itinerary_stop_id, itinerary_id, destination_id, day_number,
     stop_order, planned_start_time, duration_minutes, notes_fa, is_synthetic)
VALUES
    ('51000000-0000-4000-8000-000000000001', '50000000-0000-4000-8000-000000000001',
     (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-forest-01'),
     1, 1, '09:00', 180, 'توقف نمونه برای آزمون روز اول.', TRUE),
    ('51000000-0000-4000-8000-000000000002', '50000000-0000-4000-8000-000000000001',
     (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-waterfall-03'),
     1, 2, '14:00', 120, 'توقف نمونه دوم برای آزمون ترتیب برنامه.', TRUE),
    ('51000000-0000-4000-8000-000000000003', '50000000-0000-4000-8000-000000000001',
     (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-mountain-02'),
     2, 1, '10:00', 150, 'توقف نمونه برای آزمون روز دوم.', TRUE),
    ('51000000-0000-4000-8000-000000000004', '50000000-0000-4000-8000-000000000001',
     (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-ecotourism-08'),
     2, 2, '15:00', 90, 'توقف نمونه اقامت/تجربه محلی؛ فاقد رزرو واقعی.', TRUE),
    ('51000000-0000-4000-8000-000000000005', '50000000-0000-4000-8000-000000000001',
     (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-lake-07'),
     3, 1, '09:30', 120, 'توقف نمونه برای آزمون روز سوم.', TRUE),
    ('51000000-0000-4000-8000-000000000006', '50000000-0000-4000-8000-000000000001',
     (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-geology-09'),
     3, 2, '13:00', 90, 'توقف پایانی نمونه؛ داده مکانی و زمانی ساختگی است.', TRUE)
ON CONFLICT (itinerary_stop_id) DO UPDATE SET
    day_number = EXCLUDED.day_number,
    stop_order = EXCLUDED.stop_order,
    notes_fa = EXCLUDED.notes_fa,
    is_synthetic = TRUE;

INSERT INTO integration.external_links
    (external_link_id, destination_id, provider_name, service_type,
     label_fa, target_url, is_active, is_synthetic)
VALUES
    ('60000000-0000-4000-8000-000000000001',
     (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-forest-01'),
     'qa-provider', 'tour', 'لینک تور آزمایشی', 'https://tour.example.invalid/qa/forest', FALSE, TRUE),
    ('60000000-0000-4000-8000-000000000002',
     (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-mountain-02'),
     'qa-provider', 'hotel', 'لینک اقامت آزمایشی', 'https://stay.example.invalid/qa/mountain', FALSE, TRUE),
    ('60000000-0000-4000-8000-000000000003',
     (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-waterfall-03'),
     'qa-provider', 'official_info', 'لینک اطلاعات آزمایشی', 'https://info.example.invalid/qa/waterfall', FALSE, TRUE)
ON CONFLICT (external_link_id) DO UPDATE SET
    target_url = EXCLUDED.target_url,
    is_active = FALSE,
    is_synthetic = TRUE;

INSERT INTO operations.feedback
    (feedback_id, user_id, conversation_id, trip_id, recommendation_id,
     feedback_type, rating, comment, is_synthetic)
VALUES
    ('70000000-0000-4000-8000-000000000001',
     '10000000-0000-4000-8000-000000000001',
     '20000000-0000-4000-8000-000000000001',
     '30000000-0000-4000-8000-000000000001',
     '41000000-0000-4000-8000-000000000001',
     'recommendation_rating', 4, 'بازخورد ساختگی برای آزمون ثبت رابطه و امتیاز.', TRUE)
ON CONFLICT (feedback_id) DO UPDATE SET
    rating = EXCLUDED.rating,
    comment = EXCLUDED.comment,
    is_synthetic = TRUE;

INSERT INTO operations.dataset_import_batches
    (batch_key, data_class, record_counts, notes)
VALUES
    ('synthetic-e2e-flow-v1', 'synthetic_fixture',
     '{"users":1,"consents":1,"preferences":3,"conversations":1,"messages":4,"trips":1,"constraints":3,"interests":3,"recommendation_requests":1,"recommendations":3,"score_components":9,"itineraries":1,"itinerary_stops":6,"external_links":3,"feedback":1}'::JSONB,
     'Fully synthetic end-to-end relational graph. No real user, booking, outbound click or LLM billing event is represented.')
ON CONFLICT (batch_key) DO UPDATE SET
    record_counts = EXCLUDED.record_counts,
    notes = EXCLUDED.notes;

INSERT INTO system.schema_migrations (migration_id, sha256)
VALUES ('0003_synthetic_e2e_seed', :'migration_hash')
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;
