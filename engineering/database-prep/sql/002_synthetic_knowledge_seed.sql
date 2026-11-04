BEGIN;

-- Synthetic source: never cite as a real-world evidence source.
INSERT INTO knowledge.knowledge_sources
    (source_name, source_type, verification_status, reliability_score, notes, is_synthetic)
VALUES
    ('AI Tourism QA Synthetic Fixture Pack v1', 'synthetic_fixture', 'pending', NULL,
     'Entirely fabricated QA data. Not a factual source and not for production recommendations.', TRUE)
ON CONFLICT (source_name) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    verification_status = EXCLUDED.verification_status,
    notes = EXCLUDED.notes,
    is_synthetic = TRUE,
    updated_at = NOW();

INSERT INTO knowledge.destination_categories (category_key, name_fa, description, sort_order, is_active)
VALUES
('nature', 'طبیعت‌گردی', 'مقصدها و تجربه‌های مبتنی بر طبیعت و چشم‌اندازهای طبیعی.', 1, TRUE),
('mountain', 'کوهستان', 'مقصدهای کوهستانی و ارتفاعات.', 2, TRUE),
('waterfall', 'آبشار', 'آبشارها و جاذبه‌های مرتبط با جریان آب.', 3, TRUE),
('desert', 'کویر', 'مقصدهای بیابانی و تجربه‌های کویرگردی.', 4, TRUE),
('historical', 'تاریخی و فرهنگی', 'بناها، محوطه‌ها و مجموعه‌های میراث تاریخی و فرهنگی.', 5, TRUE),
('coastal', 'ساحلی', 'مقصدهای ساحلی و پهنه‌های مرتبط با دریا.', 6, TRUE),
('lake', 'دریاچه', 'دریاچه‌ها و پهنه‌های آبی داخلی.', 7, TRUE),
('ecotourism', 'بوم‌گردی', 'تجربه‌های گردشگری مسئولانه و اقامت/بازدید محلی.', 8, TRUE),
('geology', 'زمین‌شناسی', 'پدیده‌ها و میراث طبیعی زمین‌شناختی.', 9, TRUE),
('family', 'خانوادگی', 'مقصدهایی با شواهد و امکانات مناسب سفر خانوادگی.', 10, TRUE),
('wildlife', 'حیات‌وحش', 'زیستگاه‌ها و تجربه‌های مشاهده حیات‌وحش.', 11, TRUE),
('adventure', 'ماجراجویی', 'فعالیت‌ها و مقصدهای ماجراجویانه.', 12, TRUE)
ON CONFLICT (category_key) DO UPDATE SET
    name_fa = EXCLUDED.name_fa,
    description = EXCLUDED.description,
    sort_order = EXCLUDED.sort_order,
    is_active = TRUE;

INSERT INTO knowledge.destinations (
    destination_key, canonical_name, destination_type, province_name, city_name,
    description, difficulty, suitable_transport, best_travel_time,
    latitude, longitude, coordinate_role, status, data_confidence,
    record_origin, verification_status, is_synthetic
)
VALUES
('qa-forest-01', 'جنگل آزمایشی مهتاب QA-01', 'nature_forest', 'ناحیه آزمایشی', 'شهرک آزمون', 'داده مصنوعی QA: جنگل آزمایشی مهتاب یک نمونه ساختگی برای آزمون جست‌وجوی طبیعت‌گردی است. این مکان واقعی نیست و نباید به کاربر نهایی معرفی شود.', 'متوسط', 'خودرو و پیاده‌روی', 'بهار و پاییز', 0.000, 0.000, 'test_fixture', 'test_only', 0, 'synthetic_fixture', 'not_applicable', TRUE),
('qa-mountain-02', 'روستای کوهستانی آزمایشی QA-02', 'mountain_village', 'ناحیه آزمایشی', 'شهرک آزمون', 'داده مصنوعی QA: روستای کوهستانی آزمایشی برای سنجش درخواست هوای خنک، مسیر کوهستانی و اقامت کوتاه ساخته شده است. این مکان واقعی نیست.', 'متوسط', 'خودرو', 'تابستان', 0.000, 0.010, 'test_fixture', 'test_only', 0, 'synthetic_fixture', 'not_applicable', TRUE),
('qa-waterfall-03', 'آبشار آزمایشی سپید QA-03', 'forest_waterfall', 'ناحیه آزمایشی', 'شهرک آزمون', 'داده مصنوعی QA: آبشار آزمایشی سپید برای آزمون جست‌وجوی آبشار، طبیعت و مسیر پیاده‌روی استفاده می‌شود. این نام و موقعیت ساختگی است.', 'متوسط', 'خودرو و پیاده‌روی', 'بهار و تابستان', 0.010, 0.000, 'test_fixture', 'test_only', 0, 'synthetic_fixture', 'not_applicable', TRUE),
('qa-desert-04', 'کویر آزمایشی ستاره QA-04', 'desert', 'ناحیه آزمایشی', 'شهرک آزمون', 'داده مصنوعی QA: کویر آزمایشی ستاره نمونه‌ای ساختگی برای جست‌وجوی آسمان شب، سکوت و رصد ستارگان است. این مقصد واقعی نیست.', 'متوسط', 'خودرو آفرود', 'پاییز و زمستان', 0.010, 0.010, 'test_fixture', 'test_only', 0, 'synthetic_fixture', 'not_applicable', TRUE),
('qa-historic-05', 'محوطه تاریخی آزمایشی QA-05', 'historical_site', 'ناحیه آزمایشی', 'شهرک آزمون', 'داده مصنوعی QA: محوطه تاریخی آزمایشی جهت آزمون علایق تاریخی، موزه و معماری استفاده می‌شود. این اثر واقعی نیست.', 'آسان', 'خودرو و پیاده‌روی سبک', 'بهار و پاییز', 0.020, 0.000, 'test_fixture', 'test_only', 0, 'synthetic_fixture', 'not_applicable', TRUE),
('qa-coast-06', 'ساحل آزمایشی آبی QA-06', 'coastal_area', 'ناحیه آزمایشی', 'شهرک آزمون', 'داده مصنوعی QA: ساحل آزمایشی آبی برای آزمون جست‌وجوی ساحل، استراحت و تفریحات آبی طراحی شده است. این مکان واقعی نیست.', 'آسان', 'خودرو', 'بهار و تابستان', 0.020, 0.010, 'test_fixture', 'test_only', 0, 'synthetic_fixture', 'not_applicable', TRUE),
('qa-lake-07', 'دریاچه آزمایشی نیلوفر QA-07', 'lake', 'ناحیه آزمایشی', 'شهرک آزمون', 'داده مصنوعی QA: دریاچه آزمایشی نیلوفر نمونه‌ای غیرواقعی برای آزمون جست‌وجوی دریاچه، قایق‌سواری و عکاسی است.', 'آسان', 'خودرو و پیاده‌روی سبک', 'بهار و تابستان', 0.030, 0.000, 'test_fixture', 'test_only', 0, 'synthetic_fixture', 'not_applicable', TRUE),
('qa-ecotourism-08', 'اقامتگاه بوم‌گردی آزمایشی QA-08', 'ecotourism_lodge', 'ناحیه آزمایشی', 'شهرک آزمون', 'داده مصنوعی QA: اقامتگاه بوم‌گردی آزمایشی برای آزمون سفر خانوادگی، تجربه محلی و اقامت دو شبه تعریف شده است. این اقامتگاه وجود خارجی ندارد.', 'آسان', 'خودرو', 'تمام فصل‌ها در داده آزمایشی', 0.030, 0.010, 'test_fixture', 'test_only', 0, 'synthetic_fixture', 'not_applicable', TRUE),
('qa-geology-09', 'پدیده زمین‌شناسی آزمایشی QA-09', 'geological_site', 'ناحیه آزمایشی', 'شهرک آزمون', 'داده مصنوعی QA: پدیده زمین‌شناسی آزمایشی برای آزمون جست‌وجوی ساختارهای طبیعی و ژئوتوریسم است. اطلاعات و مختصات ساختگی‌اند.', 'آسان', 'خودرو و پیاده‌روی', 'بهار و پاییز', 0.040, 0.000, 'test_fixture', 'test_only', 0, 'synthetic_fixture', 'not_applicable', TRUE),
('qa-family-10', 'پارک خانوادگی آزمایشی QA-10', 'family_park', 'ناحیه آزمایشی', 'شهرک آزمون', 'داده مصنوعی QA: پارک خانوادگی آزمایشی برای سنجش سفر با کودک، مسیر آسان و امکانات خانوادگی ساخته شده است. این پارک واقعی نیست.', 'آسان', 'خودرو و حمل‌ونقل عمومی', 'تمام فصل‌ها در داده آزمایشی', 0.040, 0.010, 'test_fixture', 'test_only', 0, 'synthetic_fixture', 'not_applicable', TRUE),
('qa-wildlife-11', 'زیستگاه پرندگان آزمایشی QA-11', 'birdwatching_area', 'ناحیه آزمایشی', 'شهرک آزمون', 'داده مصنوعی QA: زیستگاه پرندگان آزمایشی برای آزمون جست‌وجوی پرنده‌نگری، سکوت و طبیعت محافظت‌شده تعریف شده است. این محدوده واقعی نیست.', 'آسان تا متوسط', 'خودرو و پیاده‌روی', 'پاییز و زمستان', 0.050, 0.000, 'test_fixture', 'test_only', 0, 'synthetic_fixture', 'not_applicable', TRUE),
('qa-adventure-12', 'مسیر ماجراجویی آزمایشی QA-12', 'adventure_route', 'ناحیه آزمایشی', 'شهرک آزمون', 'داده مصنوعی QA: مسیر ماجراجویی آزمایشی برای آزمون فعالیت‌های پرتحرک و پیاده‌روی چالشی است. این مسیر و مختصات واقعی نیستند.', 'سخت', 'خودرو و پیاده‌روی', 'بهار و پاییز', 0.050, 0.010, 'test_fixture', 'test_only', 0, 'synthetic_fixture', 'not_applicable', TRUE)
ON CONFLICT (destination_key) DO UPDATE SET
    canonical_name = EXCLUDED.canonical_name,
    destination_type = EXCLUDED.destination_type,
    description = EXCLUDED.description,
    difficulty = EXCLUDED.difficulty,
    suitable_transport = EXCLUDED.suitable_transport,
    best_travel_time = EXCLUDED.best_travel_time,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    status = 'test_only',
    data_confidence = 0,
    record_origin = 'synthetic_fixture',
    verification_status = 'not_applicable',
    is_synthetic = TRUE,
    updated_at = NOW();

INSERT INTO knowledge.destination_sources (destination_id, source_id, source_role, evidence_note)
SELECT d.destination_id, s.source_id, 'discovery',
       'Synthetic QA fixture relationship; not real-world evidence.'
FROM knowledge.destinations d
JOIN knowledge.knowledge_sources s
  ON s.source_name = 'AI Tourism QA Synthetic Fixture Pack v1'
WHERE d.destination_key LIKE 'qa-%'
ON CONFLICT (destination_id, source_id) DO UPDATE SET
    source_role = EXCLUDED.source_role,
    evidence_note = EXCLUDED.evidence_note;

INSERT INTO knowledge.destination_tags (destination_id, tag)
SELECT destination_id, 'qa_fixture'
FROM knowledge.destinations
WHERE destination_key LIKE 'qa-%'
ON CONFLICT DO NOTHING;

INSERT INTO knowledge.destination_category_map (destination_id, category_id, mapping_source, is_synthetic)
SELECT d.destination_id, c.category_id, 'synthetic_fixture', TRUE
FROM (VALUES
('qa-forest-01', 'nature'),
('qa-mountain-02', 'mountain'),
('qa-waterfall-03', 'waterfall'),
('qa-desert-04', 'desert'),
('qa-historic-05', 'historical'),
('qa-coast-06', 'coastal'),
('qa-lake-07', 'lake'),
('qa-ecotourism-08', 'ecotourism'),
('qa-geology-09', 'geology'),
('qa-family-10', 'family'),
('qa-wildlife-11', 'wildlife'),
('qa-adventure-12', 'adventure')) AS x(destination_key, category_key)
JOIN knowledge.destinations d ON d.destination_key = x.destination_key
JOIN knowledge.destination_categories c ON c.category_key = x.category_key
ON CONFLICT (destination_id, category_id) DO UPDATE SET
    mapping_source = EXCLUDED.mapping_source,
    is_synthetic = TRUE;

INSERT INTO knowledge.knowledge_documents (
    document_key, source_id, destination_id, title, language_code, document_type,
    raw_content, content_sha256, ingestion_status, record_origin, is_synthetic
)
VALUES
('qa-forest-01', (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'), (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-forest-01'), 'پرونده آزمایشی جنگل آزمایشی مهتاب QA-01', 'fa', 'destination_profile', 'داده مصنوعی QA: جنگل آزمایشی مهتاب یک نمونه ساختگی برای آزمون جست‌وجوی طبیعت‌گردی است. این مکان واقعی نیست و نباید به کاربر نهایی معرفی شود.
ویژگی آزمایشی: نوع=nature_forest؛ دشواری=متوسط؛ دسترسی=خودرو و پیاده‌روی؛ فصل=بهار و پاییز.', 'deb8ba38e533ff21213752888c4ed6010a9aae213aea16d66933556702c973d2', 'test_only', 'synthetic_fixture', TRUE),
('qa-mountain-02', (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'), (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-mountain-02'), 'پرونده آزمایشی روستای کوهستانی آزمایشی QA-02', 'fa', 'destination_profile', 'داده مصنوعی QA: روستای کوهستانی آزمایشی برای سنجش درخواست هوای خنک، مسیر کوهستانی و اقامت کوتاه ساخته شده است. این مکان واقعی نیست.
ویژگی آزمایشی: نوع=mountain_village؛ دشواری=متوسط؛ دسترسی=خودرو؛ فصل=تابستان.', '33c93b45c2096bf2919de11a4bf1d7e48b5502073d422a1d1e6851761330c15c', 'test_only', 'synthetic_fixture', TRUE),
('qa-waterfall-03', (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'), (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-waterfall-03'), 'پرونده آزمایشی آبشار آزمایشی سپید QA-03', 'fa', 'destination_profile', 'داده مصنوعی QA: آبشار آزمایشی سپید برای آزمون جست‌وجوی آبشار، طبیعت و مسیر پیاده‌روی استفاده می‌شود. این نام و موقعیت ساختگی است.
ویژگی آزمایشی: نوع=forest_waterfall؛ دشواری=متوسط؛ دسترسی=خودرو و پیاده‌روی؛ فصل=بهار و تابستان.', '27a0a5a7a62e15b3a9ea88a26ca9d3e1781428c63d21fbbf18a4036d57104404', 'test_only', 'synthetic_fixture', TRUE),
('qa-desert-04', (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'), (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-desert-04'), 'پرونده آزمایشی کویر آزمایشی ستاره QA-04', 'fa', 'destination_profile', 'داده مصنوعی QA: کویر آزمایشی ستاره نمونه‌ای ساختگی برای جست‌وجوی آسمان شب، سکوت و رصد ستارگان است. این مقصد واقعی نیست.
ویژگی آزمایشی: نوع=desert؛ دشواری=متوسط؛ دسترسی=خودرو آفرود؛ فصل=پاییز و زمستان.', 'ef314624d74c6535ad7ee2e51549c2f8d878f69c3b7ae3639eb5baf3ead59b2d', 'test_only', 'synthetic_fixture', TRUE),
('qa-historic-05', (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'), (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-historic-05'), 'پرونده آزمایشی محوطه تاریخی آزمایشی QA-05', 'fa', 'destination_profile', 'داده مصنوعی QA: محوطه تاریخی آزمایشی جهت آزمون علایق تاریخی، موزه و معماری استفاده می‌شود. این اثر واقعی نیست.
ویژگی آزمایشی: نوع=historical_site؛ دشواری=آسان؛ دسترسی=خودرو و پیاده‌روی سبک؛ فصل=بهار و پاییز.', 'ac18f9992ff58b43dee7647a041a5c5e77e33d06d144a16d14c6b2f8418de40d', 'test_only', 'synthetic_fixture', TRUE),
('qa-coast-06', (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'), (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-coast-06'), 'پرونده آزمایشی ساحل آزمایشی آبی QA-06', 'fa', 'destination_profile', 'داده مصنوعی QA: ساحل آزمایشی آبی برای آزمون جست‌وجوی ساحل، استراحت و تفریحات آبی طراحی شده است. این مکان واقعی نیست.
ویژگی آزمایشی: نوع=coastal_area؛ دشواری=آسان؛ دسترسی=خودرو؛ فصل=بهار و تابستان.', '20ba072bd35c94c2222ce19db0a233234fb5990d16b6f3ec9358a1b60e8490ea', 'test_only', 'synthetic_fixture', TRUE),
('qa-lake-07', (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'), (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-lake-07'), 'پرونده آزمایشی دریاچه آزمایشی نیلوفر QA-07', 'fa', 'destination_profile', 'داده مصنوعی QA: دریاچه آزمایشی نیلوفر نمونه‌ای غیرواقعی برای آزمون جست‌وجوی دریاچه، قایق‌سواری و عکاسی است.
ویژگی آزمایشی: نوع=lake؛ دشواری=آسان؛ دسترسی=خودرو و پیاده‌روی سبک؛ فصل=بهار و تابستان.', 'f29a34de3e3a946992a3de2196d3158fe40e979f662a99373f6d2049dc035184', 'test_only', 'synthetic_fixture', TRUE),
('qa-ecotourism-08', (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'), (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-ecotourism-08'), 'پرونده آزمایشی اقامتگاه بوم‌گردی آزمایشی QA-08', 'fa', 'destination_profile', 'داده مصنوعی QA: اقامتگاه بوم‌گردی آزمایشی برای آزمون سفر خانوادگی، تجربه محلی و اقامت دو شبه تعریف شده است. این اقامتگاه وجود خارجی ندارد.
ویژگی آزمایشی: نوع=ecotourism_lodge؛ دشواری=آسان؛ دسترسی=خودرو؛ فصل=تمام فصل‌ها در داده آزمایشی.', 'a5d3aad152521b759bd16f6d86a313e1a9eb40a3d2840a8a9555e0fb2e446f0a', 'test_only', 'synthetic_fixture', TRUE),
('qa-geology-09', (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'), (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-geology-09'), 'پرونده آزمایشی پدیده زمین‌شناسی آزمایشی QA-09', 'fa', 'destination_profile', 'داده مصنوعی QA: پدیده زمین‌شناسی آزمایشی برای آزمون جست‌وجوی ساختارهای طبیعی و ژئوتوریسم است. اطلاعات و مختصات ساختگی‌اند.
ویژگی آزمایشی: نوع=geological_site؛ دشواری=آسان؛ دسترسی=خودرو و پیاده‌روی؛ فصل=بهار و پاییز.', '1a28612cfe93ac661a9b6e890ea0ab4072876faeb97fa4cdd327118ca4dba606', 'test_only', 'synthetic_fixture', TRUE),
('qa-family-10', (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'), (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-family-10'), 'پرونده آزمایشی پارک خانوادگی آزمایشی QA-10', 'fa', 'destination_profile', 'داده مصنوعی QA: پارک خانوادگی آزمایشی برای سنجش سفر با کودک، مسیر آسان و امکانات خانوادگی ساخته شده است. این پارک واقعی نیست.
ویژگی آزمایشی: نوع=family_park؛ دشواری=آسان؛ دسترسی=خودرو و حمل‌ونقل عمومی؛ فصل=تمام فصل‌ها در داده آزمایشی.', '36580e829012abd7bde45c1546033af70992195a52d8d9d5d3b9bc822cb63618', 'test_only', 'synthetic_fixture', TRUE),
('qa-wildlife-11', (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'), (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-wildlife-11'), 'پرونده آزمایشی زیستگاه پرندگان آزمایشی QA-11', 'fa', 'destination_profile', 'داده مصنوعی QA: زیستگاه پرندگان آزمایشی برای آزمون جست‌وجوی پرنده‌نگری، سکوت و طبیعت محافظت‌شده تعریف شده است. این محدوده واقعی نیست.
ویژگی آزمایشی: نوع=birdwatching_area؛ دشواری=آسان تا متوسط؛ دسترسی=خودرو و پیاده‌روی؛ فصل=پاییز و زمستان.', '87375e9e612eccb6a652b3a31deed8d0f36e74afebcb9e18a0e14e22dafa5151', 'test_only', 'synthetic_fixture', TRUE),
('qa-adventure-12', (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'), (SELECT destination_id FROM knowledge.destinations WHERE destination_key = 'qa-adventure-12'), 'پرونده آزمایشی مسیر ماجراجویی آزمایشی QA-12', 'fa', 'destination_profile', 'داده مصنوعی QA: مسیر ماجراجویی آزمایشی برای آزمون فعالیت‌های پرتحرک و پیاده‌روی چالشی است. این مسیر و مختصات واقعی نیستند.
ویژگی آزمایشی: نوع=adventure_route؛ دشواری=سخت؛ دسترسی=خودرو و پیاده‌روی؛ فصل=بهار و پاییز.', '19f588d67b9a4c04435e06155aa8051f3f643ff2ed2024f8f98be96a9fce5bf1', 'test_only', 'synthetic_fixture', TRUE)
ON CONFLICT (document_key) DO UPDATE SET
    source_id = EXCLUDED.source_id,
    destination_id = EXCLUDED.destination_id,
    title = EXCLUDED.title,
    raw_content = EXCLUDED.raw_content,
    content_sha256 = EXCLUDED.content_sha256,
    ingestion_status = 'test_only',
    record_origin = 'synthetic_fixture',
    is_synthetic = TRUE,
    updated_at = NOW();

INSERT INTO knowledge.knowledge_chunks (
    document_id, chunk_index, content, char_count, token_count,
    content_sha256, metadata, is_synthetic
)
VALUES
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-forest-01'), 0, 'جنگل آزمایشی مهتاب QA-01: داده مصنوعی QA: جنگل آزمایشی مهتاب یک نمونه ساختگی برای آزمون جست‌وجوی طبیعت‌گردی است. این مکان واقعی نیست و نباید به کاربر نهایی معرفی شود.', 166, NULL, '1df673ca3076289523a54697a2acd3f3378425155002bf7dbb6646bbde8000ba', jsonb_build_object('fixture_key', 'qa-forest-01', 'chunk_role', 'overview', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-forest-01'), 1, 'ویژگی‌های آزمایشی جنگل آزمایشی مهتاب QA-01: نوع مقصد nature_forest؛ دشواری متوسط؛ دسترسی خودرو و پیاده‌روی؛ فصل پیشنهادی در سناریوی ساختگی بهار و پاییز. این داده صرفاً برای آزمون ذخیره و بازیابی است.', 199, NULL, '3ab3640850acf8575c93d82feab1db96f7019a30ae2e9893976e80e672e5caa6', jsonb_build_object('fixture_key', 'qa-forest-01', 'chunk_role', 'attributes', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-mountain-02'), 0, 'روستای کوهستانی آزمایشی QA-02: داده مصنوعی QA: روستای کوهستانی آزمایشی برای سنجش درخواست هوای خنک، مسیر کوهستانی و اقامت کوتاه ساخته شده است. این مکان واقعی نیست.', 162, NULL, 'b42a6e97dd6ea46591cf6bd9d3bd33ba137a8ddb2fd82a6d35046c446dc09417', jsonb_build_object('fixture_key', 'qa-mountain-02', 'chunk_role', 'overview', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-mountain-02'), 1, 'ویژگی‌های آزمایشی روستای کوهستانی آزمایشی QA-02: نوع مقصد mountain_village؛ دشواری متوسط؛ دسترسی خودرو؛ فصل پیشنهادی در سناریوی ساختگی تابستان. این داده صرفاً برای آزمون ذخیره و بازیابی است.', 190, NULL, '0c80d31b797f42d1f72fbf53a4219f40231e84a47559c2cd22c85d7f135e4cae', jsonb_build_object('fixture_key', 'qa-mountain-02', 'chunk_role', 'attributes', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-waterfall-03'), 0, 'آبشار آزمایشی سپید QA-03: داده مصنوعی QA: آبشار آزمایشی سپید برای آزمون جست‌وجوی آبشار، طبیعت و مسیر پیاده‌روی استفاده می‌شود. این نام و موقعیت ساختگی است.', 155, NULL, '8d427eb95379b4bdb9a1f3421c283715aa7f149cce020b2ce7089a7228b237dc', jsonb_build_object('fixture_key', 'qa-waterfall-03', 'chunk_role', 'overview', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-waterfall-03'), 1, 'ویژگی‌های آزمایشی آبشار آزمایشی سپید QA-03: نوع مقصد forest_waterfall؛ دشواری متوسط؛ دسترسی خودرو و پیاده‌روی؛ فصل پیشنهادی در سناریوی ساختگی بهار و تابستان. این داده صرفاً برای آزمون ذخیره و بازیابی است.', 204, NULL, 'c56964eef163e506852e811eb16116e21721b8057beb371a2073940017ea83ba', jsonb_build_object('fixture_key', 'qa-waterfall-03', 'chunk_role', 'attributes', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-desert-04'), 0, 'کویر آزمایشی ستاره QA-04: داده مصنوعی QA: کویر آزمایشی ستاره نمونه‌ای ساختگی برای جست‌وجوی آسمان شب، سکوت و رصد ستارگان است. این مقصد واقعی نیست.', 145, NULL, '4426e63bcdfde6b4b4623a665a92717dfe96efcc7b7d742d2b98ad06740be193', jsonb_build_object('fixture_key', 'qa-desert-04', 'chunk_role', 'overview', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-desert-04'), 1, 'ویژگی‌های آزمایشی کویر آزمایشی ستاره QA-04: نوع مقصد desert؛ دشواری متوسط؛ دسترسی خودرو آفرود؛ فصل پیشنهادی در سناریوی ساختگی پاییز و زمستان. این داده صرفاً برای آزمون ذخیره و بازیابی است.', 188, NULL, 'c06c7b70f2acb70d216ac42f4e325ccad7d615c0f38d5e49aac72b1ec4905fe9', jsonb_build_object('fixture_key', 'qa-desert-04', 'chunk_role', 'attributes', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-historic-05'), 0, 'محوطه تاریخی آزمایشی QA-05: داده مصنوعی QA: محوطه تاریخی آزمایشی جهت آزمون علایق تاریخی، موزه و معماری استفاده می‌شود. این اثر واقعی نیست.', 138, NULL, '4a349225102dddc4e4a38397e4d953065a82a953cc1ea468c77cf36c32db29e0', jsonb_build_object('fixture_key', 'qa-historic-05', 'chunk_role', 'overview', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-historic-05'), 1, 'ویژگی‌های آزمایشی محوطه تاریخی آزمایشی QA-05: نوع مقصد historical_site؛ دشواری آسان؛ دسترسی خودرو و پیاده‌روی سبک؛ فصل پیشنهادی در سناریوی ساختگی بهار و پاییز. این داده صرفاً برای آزمون ذخیره و بازیابی است.', 206, NULL, 'a2d0517d56a79e5afed86b436e5c7bc4f180b37b5750ef30e355692c6faff625', jsonb_build_object('fixture_key', 'qa-historic-05', 'chunk_role', 'attributes', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-coast-06'), 0, 'ساحل آزمایشی آبی QA-06: داده مصنوعی QA: ساحل آزمایشی آبی برای آزمون جست‌وجوی ساحل، استراحت و تفریحات آبی طراحی شده است. این مکان واقعی نیست.', 140, NULL, 'e80e1e77dc3449a641805f50d37d4727d27fc4ab04540f156e164535899c33d0', jsonb_build_object('fixture_key', 'qa-coast-06', 'chunk_role', 'overview', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-coast-06'), 1, 'ویژگی‌های آزمایشی ساحل آزمایشی آبی QA-06: نوع مقصد coastal_area؛ دشواری آسان؛ دسترسی خودرو؛ فصل پیشنهادی در سناریوی ساختگی بهار و تابستان. این داده صرفاً برای آزمون ذخیره و بازیابی است.', 185, NULL, '662b9e24d82e3b156131c12a72ae3691d33237782b9713435327fb68b736cb97', jsonb_build_object('fixture_key', 'qa-coast-06', 'chunk_role', 'attributes', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-lake-07'), 0, 'دریاچه آزمایشی نیلوفر QA-07: داده مصنوعی QA: دریاچه آزمایشی نیلوفر نمونه‌ای غیرواقعی برای آزمون جست‌وجوی دریاچه، قایق‌سواری و عکاسی است.', 136, NULL, '02ca7a878a7484e784c0a47a311832b244709afb23841b330a88afd1c2220cbe', jsonb_build_object('fixture_key', 'qa-lake-07', 'chunk_role', 'overview', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-lake-07'), 1, 'ویژگی‌های آزمایشی دریاچه آزمایشی نیلوفر QA-07: نوع مقصد lake؛ دشواری آسان؛ دسترسی خودرو و پیاده‌روی سبک؛ فصل پیشنهادی در سناریوی ساختگی بهار و تابستان. این داده صرفاً برای آزمون ذخیره و بازیابی است.', 198, NULL, 'a842572645d0d46c83cf103cb1731e29563fe30bd3636664c90ac2278b1c972d', jsonb_build_object('fixture_key', 'qa-lake-07', 'chunk_role', 'attributes', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-ecotourism-08'), 0, 'اقامتگاه بوم‌گردی آزمایشی QA-08: داده مصنوعی QA: اقامتگاه بوم‌گردی آزمایشی برای آزمون سفر خانوادگی، تجربه محلی و اقامت دو شبه تعریف شده است. این اقامتگاه وجود خارجی ندارد.', 171, NULL, '4357b407890a94831d377231748ae00cb34c85ca4a02c9f6db21d53d56016acc', jsonb_build_object('fixture_key', 'qa-ecotourism-08', 'chunk_role', 'overview', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-ecotourism-08'), 1, 'ویژگی‌های آزمایشی اقامتگاه بوم‌گردی آزمایشی QA-08: نوع مقصد ecotourism_lodge؛ دشواری آسان؛ دسترسی خودرو؛ فصل پیشنهادی در سناریوی ساختگی تمام فصل‌ها در داده آزمایشی. این داده صرفاً برای آزمون ذخیره و بازیابی است.', 211, NULL, 'ff6f933e40da820a7f95b2f4f43d8159e273e8cc9e63b8b8eef5239a52661c8f', jsonb_build_object('fixture_key', 'qa-ecotourism-08', 'chunk_role', 'attributes', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-geology-09'), 0, 'پدیده زمین‌شناسی آزمایشی QA-09: داده مصنوعی QA: پدیده زمین‌شناسی آزمایشی برای آزمون جست‌وجوی ساختارهای طبیعی و ژئوتوریسم است. اطلاعات و مختصات ساختگی‌اند.', 154, NULL, '2008aa9c7552c95612694093977aac2b59b744bebcc74d0f3316669511350f99', jsonb_build_object('fixture_key', 'qa-geology-09', 'chunk_role', 'overview', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-geology-09'), 1, 'ویژگی‌های آزمایشی پدیده زمین‌شناسی آزمایشی QA-09: نوع مقصد geological_site؛ دشواری آسان؛ دسترسی خودرو و پیاده‌روی؛ فصل پیشنهادی در سناریوی ساختگی بهار و پاییز. این داده صرفاً برای آزمون ذخیره و بازیابی است.', 206, NULL, 'ecf6b015a30cc9d2bc2ba86244797c2d3d8fec25f9ee9a78ddc0b608a44b10e5', jsonb_build_object('fixture_key', 'qa-geology-09', 'chunk_role', 'attributes', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-family-10'), 0, 'پارک خانوادگی آزمایشی QA-10: داده مصنوعی QA: پارک خانوادگی آزمایشی برای سنجش سفر با کودک، مسیر آسان و امکانات خانوادگی ساخته شده است. این پارک واقعی نیست.', 154, NULL, '035817e7c71bf53d08a09261bea074338a6b85aafde242d8acf593cd2ca64b78', jsonb_build_object('fixture_key', 'qa-family-10', 'chunk_role', 'overview', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-family-10'), 1, 'ویژگی‌های آزمایشی پارک خانوادگی آزمایشی QA-10: نوع مقصد family_park؛ دشواری آسان؛ دسترسی خودرو و حمل‌ونقل عمومی؛ فصل پیشنهادی در سناریوی ساختگی تمام فصل‌ها در داده آزمایشی. این داده صرفاً برای آزمون ذخیره و بازیابی است.', 219, NULL, '28a9acf43d2bae83449fd32cbc105dc23297461d6050356734542c44de447278', jsonb_build_object('fixture_key', 'qa-family-10', 'chunk_role', 'attributes', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-wildlife-11'), 0, 'زیستگاه پرندگان آزمایشی QA-11: داده مصنوعی QA: زیستگاه پرندگان آزمایشی برای آزمون جست‌وجوی پرنده‌نگری، سکوت و طبیعت محافظت‌شده تعریف شده است. این محدوده واقعی نیست.', 164, NULL, 'f1a5881b7d2fda80ce31675d7874bbe76de8d09f9ad3bfb1337ff9085861f561', jsonb_build_object('fixture_key', 'qa-wildlife-11', 'chunk_role', 'overview', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-wildlife-11'), 1, 'ویژگی‌های آزمایشی زیستگاه پرندگان آزمایشی QA-11: نوع مقصد birdwatching_area؛ دشواری آسان تا متوسط؛ دسترسی خودرو و پیاده‌روی؛ فصل پیشنهادی در سناریوی ساختگی پاییز و زمستان. این داده صرفاً برای آزمون ذخیره و بازیابی است.', 218, NULL, 'f90df555fa89e70ab57be3cccc3c726f3389f9f133a3dcf3731fb413aa4977cd', jsonb_build_object('fixture_key', 'qa-wildlife-11', 'chunk_role', 'attributes', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-adventure-12'), 0, 'مسیر ماجراجویی آزمایشی QA-12: داده مصنوعی QA: مسیر ماجراجویی آزمایشی برای آزمون فعالیت‌های پرتحرک و پیاده‌روی چالشی است. این مسیر و مختصات واقعی نیستند.', 152, NULL, '5e1c6816522c08d72fb0b14eabfc3d842fb5736e733b9d3ddc9f767d80683531', jsonb_build_object('fixture_key', 'qa-adventure-12', 'chunk_role', 'overview', 'synthetic', TRUE), TRUE),
((SELECT document_id FROM knowledge.knowledge_documents WHERE document_key = 'qa-adventure-12'), 1, 'ویژگی‌های آزمایشی مسیر ماجراجویی آزمایشی QA-12: نوع مقصد adventure_route؛ دشواری سخت؛ دسترسی خودرو و پیاده‌روی؛ فصل پیشنهادی در سناریوی ساختگی بهار و پاییز. این داده صرفاً برای آزمون ذخیره و بازیابی است.', 203, NULL, 'cf3c05fcc4897e984bb229f913cac5f196c5c474ad52a79131834dbc3470b729', jsonb_build_object('fixture_key', 'qa-adventure-12', 'chunk_role', 'attributes', 'synthetic', TRUE), TRUE)
ON CONFLICT (document_id, chunk_index) DO UPDATE SET
    content = EXCLUDED.content,
    char_count = EXCLUDED.char_count,
    content_sha256 = EXCLUDED.content_sha256,
    metadata = EXCLUDED.metadata,
    is_synthetic = TRUE;

-- Register the pre-existing 15-record source import and this synthetic batch.
INSERT INTO operations.dataset_import_batches
    (batch_key, data_class, source_id, record_counts, notes)
VALUES
    ('legacy-user-supplied-destinations-v1', 'user_supplied_unverified',
     (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'Supplied tourism-points dataset (project attachment)'),
     '{"destinations":15,"sources":1}'::JSONB,
     'Imported from the existing project SQL. All 15 remain needs_review/pending and have no verified coordinates.'),
    ('synthetic-knowledge-fixtures-v1', 'synthetic_fixture',
     (SELECT source_id FROM knowledge.knowledge_sources WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'),
     '{"destinations":12,"documents":12,"chunks":24,"categories":12,"category_mappings":12}'::JSONB,
     'Fabricated QA data only; all destination rows have status=test_only and no claim of real-world truth.')
ON CONFLICT (batch_key) DO UPDATE SET
    data_class = EXCLUDED.data_class,
    source_id = EXCLUDED.source_id,
    record_counts = EXCLUDED.record_counts,
    notes = EXCLUDED.notes;

INSERT INTO system.schema_migrations (migration_id, sha256)
VALUES ('0002_synthetic_knowledge_seed', :'migration_hash')
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;
