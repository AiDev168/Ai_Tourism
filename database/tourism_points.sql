-- Ai_Tourism — Tourism Points Database
-- PostgreSQL / pgvector-compatible baseline
--
-- Purpose:
--   Canonical schema + seed data for tourism points supplied by the project team.
--   This file intentionally keeps source/provenance separate from the tourism entity.
--   Geographic coordinates are nullable because the supplied source data did not
--   contain coordinates for the current records.
--
-- Architecture alignment:
--   knowledge schema -> destinations -> destination_localizations
--   knowledge schema -> knowledge_sources
--   knowledge schema -> destination_sources
--   knowledge schema -> destination_tags
--
-- The data below is transcribed from the supplied 16-line CSV/text attachment.
-- Source status "در دست جستجو" is preserved as-is and MUST NOT be treated as verified.

BEGIN;

CREATE SCHEMA IF NOT EXISTS knowledge;

CREATE TABLE IF NOT EXISTS knowledge.knowledge_sources (
    source_id           BIGSERIAL PRIMARY KEY,
    source_name         TEXT NOT NULL,
    source_type         TEXT NOT NULL DEFAULT 'research_pending',
    verification_status TEXT NOT NULL DEFAULT 'pending',
    reliability_score   NUMERIC(5,4),
    url                 TEXT,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_source_status
        CHECK (verification_status IN ('pending','verified','rejected','stale')),
    CONSTRAINT chk_source_reliability
        CHECK (reliability_score IS NULL OR (reliability_score >= 0 AND reliability_score <= 1))
);

CREATE TABLE IF NOT EXISTS knowledge.destinations (
    destination_id      BIGSERIAL PRIMARY KEY,
    canonical_name      TEXT NOT NULL,
    destination_type    TEXT NOT NULL DEFAULT 'tourism_point',
    province_name       TEXT NOT NULL,
    city_name           TEXT,
    description         TEXT NOT NULL,
    difficulty          TEXT,
    suitable_transport  TEXT,
    local_language      TEXT,
    local_food          TEXT,
    local_souvenirs     TEXT,
    best_travel_time    TEXT,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    status               TEXT NOT NULL DEFAULT 'draft',
    data_confidence     NUMERIC(5,4) NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_destination_canonical UNIQUE (canonical_name, province_name, city_name),
    CONSTRAINT chk_destination_status
        CHECK (status IN ('draft','active','inactive','archived','needs_review')),
    CONSTRAINT chk_destination_confidence
        CHECK (data_confidence >= 0 AND data_confidence <= 1),
    CONSTRAINT chk_latitude
        CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    CONSTRAINT chk_longitude
        CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
);

CREATE TABLE IF NOT EXISTS knowledge.destination_sources (
    destination_id  BIGINT NOT NULL REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE,
    source_id       BIGINT NOT NULL REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT,
    source_role     TEXT NOT NULL DEFAULT 'primary',
    evidence_note   TEXT,
    retrieved_at    TIMESTAMPTZ,
    valid_from      TIMESTAMPTZ,
    valid_until     TIMESTAMPTZ,
    PRIMARY KEY (destination_id, source_id),
    CONSTRAINT chk_source_role
        CHECK (source_role IN ('primary','secondary','verification','discovery'))
);

CREATE TABLE IF NOT EXISTS knowledge.destination_tags (
    destination_id BIGINT NOT NULL REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE,
    tag             TEXT NOT NULL,
    PRIMARY KEY (destination_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_destinations_province
    ON knowledge.destinations (province_name);
CREATE INDEX IF NOT EXISTS idx_destinations_city
    ON knowledge.destinations (city_name);
CREATE INDEX IF NOT EXISTS idx_destinations_status
    ON knowledge.destinations (status);
CREATE INDEX IF NOT EXISTS idx_destinations_geo
    ON knowledge.destinations (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_destination_tags_tag
    ON knowledge.destination_tags (tag);

-- Seed source record for the supplied attachment.
INSERT INTO knowledge.knowledge_sources (
    source_name, source_type, verification_status, notes
)
VALUES (
    'Supplied tourism-points dataset (project attachment)',
    'project_supplied_dataset',
    'pending',
    'All records were supplied with source status «در دست جستجو». External verification is required before production use.'
)
ON CONFLICT DO NOTHING;

-- Seed tourism points.
INSERT INTO knowledge.destinations (
    canonical_name,
    destination_type,
    province_name,
    city_name,
    description,
    difficulty,
    suitable_transport,
    local_language,
    local_food,
    local_souvenirs,
    best_travel_time,
    latitude,
    longitude,
    status,
    data_confidence
)
VALUES
(
    'رصدخانه مراغه', 'historical_astronomical_site', 'آذربایجان شرقی', 'مراغه',
    'یکی از مهم‌ترین رصدخانه‌های تاریخی جهان که در قرن هفتم هجری توسط خواجه نصیرالدین طوسی ساخته شده است. این رصدخانه در دوران خود بزرگ‌ترین و پیشرفته‌ترین مرکز نجوم جهان بود و دانشمندان بزرگی از سراسر جهان در آن فعالیت می‌کردند. بقایای این رصدخانه شامل دیوارها و پایه‌های سنگی در شهر مراغه در استان آذربایجان شرقی قرار دارد و یکی از جاذبه‌های تاریخی مهم ایران محسوب می‌شود.',
    'آسان', 'سواری', 'ترکی آذربایجانی', 'غذاهای محلی آذربایجان مانند ساج قاورماسی و پیچاق قیمه', 'صنایع دستی آذربایجان و عسل سبلان', 'بهار و پاییز', NULL, NULL, 'needs_review', 0
),
(
    'شهرستانک', 'historical_village', 'البرز', 'کرج',
    'روستایی تاریخی و ییلاقی در جاده کرج-چالوس که به دلیل معماری سنتی باغ‌های میوه و طبیعت زیبا مقصدی محبوب برای تهرانی‌ها است. شهرستانک در دامنه‌های البرز و در ارتفاع مناسب قرار دارد و با آب‌وهوای خنک و مناظر سرسبز مقصدی ایده‌آل برای فرار از گرمای تابستان است. کاخ شهرستانک که در دوران قاجار ساخته شده نیز یکی از جاذبه‌های تاریخی این روستا است.',
    'آسان', 'سواری', 'فارسی', 'غذاهای محلی البرز و کرج', 'میوه‌های باغی و محصولات محلی', 'بهار و تابستان', NULL, NULL, 'needs_review', 0
),
(
    'دره زمان', 'nature_valley', 'تهران', 'تهران',
    'یکی از دره‌های زیبا و بکر اطراف تهران که با طبیعت سرسبز چشم‌اندازهای کوهستانی و هوای خنک مقصدی محبوب برای طبیعت‌گردان است. دره زمان در دامنه‌های البرز و در نزدیکی فیروزکوه قرار دارد و با مسیرهای پیاده‌روی جذاب و چشمه‌های سرد یکی از مقاصد مناسب برای فرار از شلوغی شهر است.',
    'متوسط', 'پیاده‌روی', 'مازندرانی', 'غذاهای محلی مازندران', 'محصولات جنگلی و لبنیات محلی', 'بهار و تابستان', NULL, NULL, 'needs_review', 0
),
(
    'دشت لار', 'nature_plain', 'تهران', 'تهران',
    'دشتی وسیع و زیبا در ارتفاعات البرز و در نزدیکی دماوند که با چشم‌اندازهای وسیع از قله دماوند و طبیعت بکر مقصدی محبوب برای طبیعت‌گردان است. دشت لار با چمنزارهای سرسبز چشمه‌های سرد و هوای خنک کوهستانی یکی از مقاصد مناسب برای کمپینگ و پیک‌نیک است.',
    'آسان', 'سواری', 'فارسی', 'غذاهای محلی مازندران و دماوند', 'محصولات لبنی و سبزی‌های کوهی', 'بهار و تابستان', NULL, NULL, 'needs_review', 0
),
(
    'تهران گردی', 'city_tour', 'تهران', 'تهران',
    'برنامه‌ای جامع برای آشنایی با جاذبه‌های تاریخی فرهنگی و طبیعی شهر تهران. این برنامه شامل بازدید از کاخ گلستان (ثبت یونسکو) بازار بزرگ تهران موزه ملی ایران برج آزادی پل طبیعت پارک‌ها و باغ‌های تاریخی و دیگر جاذبه‌های پایتخت است. تهران گردی برای علاقه‌مندان به تاریخ فرهنگ و معماری ایرانی مقصدی ایده‌آل است.',
    'آسان', 'سواری', 'فارسی', 'غذاهای متنوع تهرانی و سنتی ایرانی', 'صنایع دستی و سوغات تهران', 'بهار و پاییز', NULL, NULL, 'needs_review', 0
),
(
    'جنگل ابر', 'hyrcanian_forest', 'سمنان', 'شاهرود',
    'یکی از زیباترین و بکرترین جنگل‌های ایران که در ارتفاعات شاهرود و در مسیر جاده شاهرود به آزادشهر قرار دارد. این جنگل به دلیل قرار گرفتن در ارتفاعات و پوشیده شدن مکرر توسط ابرها به «جنگل ابر» معروف است. جنگل ابر بخشی از جنگل‌های هیرکانی است و با تنوع زیستی بالا چشم‌اندازهای مه‌آلود و هوای خنک مقصدی محبوب برای طبیعت‌گردان و عکاسان است.',
    'متوسط', 'سواری/پیاده‌روی', 'فارسی', 'غذاهای محلی سمنان و شاهرود', 'محصولات جنگلی و لبنیات محلی', 'بهار و تابستان', NULL, NULL, 'needs_review', 0
),
(
    'سافاری اوپرت تا اولنگ', 'off_road_safari', 'سمنان', 'شاهرود',
    'سفری ماجراجویانه با خودروهای آفرود در کویر و مناطق بکر شاهرود. اوپرت و اولنگ دو منطقه کویری با چشم‌اندازهای فرازمینی تپه‌های شنی و سکوت مطلق هستند. این سفر برای علاقه‌مندان به سافاری و تجربه‌های کویری بسیار مناسب است و با خودروهای آفرود و راهنمایان محلی انجام می‌شود.',
    'متوسط تا سخت', 'آفرود', 'فارسی', 'غذاهای محلی کویری و سمنان', 'محصولات محلی کویری', 'پاییز و زمستان', NULL, NULL, 'needs_review', 0
),
(
    'کالپوش تا آبشار لوه', 'nature_waterfall_trip', 'سمنان', 'دامغان',
    'سفری به منطقه کالپوش با طبیعت بکر و آبشار لوه. کالپوش منطقه‌ای کوهستانی با پوشش گیاهی متنوع و چشم‌اندازهای زیبا است که آبشار لوه یکی از جاذبه‌های طبیعی آن محسوب می‌شود. این منطقه برای علاقه‌مندان به طبیعت‌گردی در مسیرهای بکر و کم‌تردد بسیار مناسب است.',
    'متوسط', 'پیاده‌روی', 'فارسی', 'غذاهای محلی سمنان و دامغان', 'محصولات محلی و لبنیات', 'بهار و تابستان', NULL, NULL, 'needs_review', 0
),
(
    'کویر حاج علی قلی', 'desert', 'سمنان', 'سمنان',
    'کویری بکر با تپه‌های شنی و چشم‌اندازهای فرازمینی در نزدیکی سمنان. این کویر با آسمان پرستاره و سکوت مطلق مقصدی محبوب برای کویرگردی و عکاسی شبانه است. کویر حاج علی قلی یکی از کویرهای کمتر شناخته‌شده اما بسیار زیبای ایران است که برای علاقه‌مندان به مناطق بکر مناسب است.',
    'متوسط', 'آفرود', 'فارسی', 'غذاهای محلی کویری', 'محصولات محلی کویری', 'پاییز و زمستان', NULL, NULL, 'needs_review', 0
),
(
    'باداب سورت', 'geological_site', 'مازندران', 'ساری',
    'دومین اثر طبیعی ملی ایران و یکی از منحصربه‌فردترین پدیده‌های زمین‌شناسی جهان. باداب سورت مجموعه‌ای از حوضچه‌های پلکانی آبگرم معدنی است که در طول هزاران سال بر اثر رسوب املاح معدنی شکل گرفته‌اند. این پدیده در روستای ارست در شهرستان ساری قرار دارد و با رنگ‌های متنوع نارنجی زرد و سفید منظره‌ای شگفت‌انگیز ایجاد کرده است. باداب سورت پس از پاموک‌کاله ترکیه دومین نمونه بزرگ این پدیده در جهان است.',
    'آسان', 'سواری', 'مازندرانی', 'غذاهای محلی مازندران', 'محصولات محلی و لبنیات', 'بهار و تابستان', NULL, NULL, 'needs_review', 0
),
(
    'رامسر و شمال', 'coastal_city_tour', 'مازندران', 'رامسر',
    'سفری به عروس شمال ایران. رامسر یکی از زیباترین شهرهای ساحلی مازندران است که با ترکیب جنگل و دریا آب‌وهوای معتدل و جاذبه‌های تاریخی و طبیعی مقصدی محبوب برای گردشگران است. کاخ مرمر رامسر تله‌کابین رامسر باغ‌های چای و سواحل زیبا از جاذبه‌های اصلی این شهر هستند.',
    'آسان', 'سواری', 'مازندرانی', 'ماهی و غذاهای دریایی غذاهای محلی مازندران', 'چای رامسر مرکبات و صنایع دستی', 'بهار و تابستان', NULL, NULL, 'needs_review', 0
),
(
    'آبشار عروس دامن', 'forest_waterfall', 'مازندران', 'ساری',
    'آبشاری زیبا با حوضچه‌های متعدد در دل جنگل‌های مازندران که به دلیل فرم پلکانی و آب زلالش به «عروس دامن» معروف است. این آبشار یکی از جاذبه‌های طبیعی کم‌نظیر مازندران است که با دسترسی نسبتاً آسان مقصدی محبوب برای طبیعت‌گردان و عکاسان است.',
    'آسان تا متوسط', 'پیاده‌روی', 'مازندرانی', 'غذاهای محلی مازندران', 'محصولات جنگلی', 'بهار و تابستان', NULL, NULL, 'needs_review', 0
),
(
    'آبشار گزو', 'forest_waterfall', 'مازندران', 'مازندران',
    'آبشاری مرتفع و زیبا در جنگل‌های مازندران که با ارتفاع زیاد و پوشش گیاهی غنی اطرافش مقصدی محبوب برای طبیعت‌گردان حرفه‌ای است. مسیر دسترسی به این آبشار از میان جنگل‌های انبوه می‌گذرد و نیاز به آمادگی بدنی متوسط دارد.',
    'متوسط', 'پیاده‌روی', 'مازندرانی', 'غذاهای محلی مازندران', 'محصولات جنگلی', 'بهار و تابستان', NULL, NULL, 'needs_review', 0
),
(
    'دشت دریاسر', 'mountain_plain', 'مازندران', 'ساری',
    'دشتی وسیع و زیبا در ارتفاعات مازندران که با چشم‌اندازهای وسیع از کوه‌ها و دره‌ها هوای پاک و طبیعت بکر مقصدی محبوب برای طبیعت‌گردان و کمپینگ است. دشت دریاسر با چمنزارهای سرسبز و چشمه‌های سرد یکی از مقاصد مناسب برای فرار از شلوغی شهر است.',
    'آسان', 'سواری', 'مازندرانی', 'غذاهای محلی مازندران', 'محصولات لبنی و سبزی‌های کوهی', 'بهار و تابستان', NULL, NULL, 'needs_review', 0
),
(
    'همدان', 'historical_city', 'همدان', 'همدان',
    'مرکز استان همدان در غرب ایران و یکی از قدیمی‌ترین شهرهای جهان که به «پایتخت تاریخ و تمدن ایران» معروف است. همدان با قدمت بیش از ۳۰۰۰ سال میزبان تمدن‌های مختلفی از جمله مادها هخامنشیان و ساسانیان بوده است. غار علیصدر (بزرگ‌ترین غار آبی جهان) آرامگاه بوعلی سینا آرامگاه باباطاهر سنگ‌نگاره گنج‌نامه و بازار سنتی همدان از جاذبه‌های اصلی این شهر هستند. همدان به دلیل قرار گرفتن در ارتفاع ۱۷۵۰ متری از سطح دریا یکی از سردترین شهرهای ایران است و به «شهر سردسیر» معروف است.',
    'آسان', 'سواری', 'ترکی آذربایجانی/فارسی', 'آبگوشت همدانی کباب همدانی و آش‌های محلی', 'سفال همدان و صنایع دستی', 'بهار و تابستان', NULL, NULL, 'needs_review', 0
)
ON CONFLICT (canonical_name, province_name, city_name) DO UPDATE SET
    description = EXCLUDED.description,
    difficulty = EXCLUDED.difficulty,
    suitable_transport = EXCLUDED.suitable_transport,
    local_language = EXCLUDED.local_language,
    local_food = EXCLUDED.local_food,
    local_souvenirs = EXCLUDED.local_souvenirs,
    best_travel_time = EXCLUDED.best_travel_time,
    updated_at = NOW();

-- Preserve the supplied "در دست جستجو" provenance for every seeded destination.
INSERT INTO knowledge.destination_sources (
    destination_id, source_id, source_role, evidence_note
)
SELECT
    d.destination_id,
    s.source_id,
    'discovery',
    'Source field in supplied dataset: در دست جستجو'
FROM knowledge.destinations d
CROSS JOIN LATERAL (
    SELECT source_id
    FROM knowledge.knowledge_sources
    WHERE source_name = 'Supplied tourism-points dataset (project attachment)'
    ORDER BY source_id
    LIMIT 1
) s
WHERE d.status = 'needs_review'
ON CONFLICT (destination_id, source_id) DO UPDATE SET
    evidence_note = EXCLUDED.evidence_note;

-- Lightweight tags derived ONLY from the supplied categorical fields.
INSERT INTO knowledge.destination_tags (destination_id, tag)
SELECT destination_id, LOWER(REPLACE(difficulty, ' ', '_'))
FROM knowledge.destinations
WHERE difficulty IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO knowledge.destination_tags (destination_id, tag)
SELECT destination_id, 'province:' || province_name
FROM knowledge.destinations
ON CONFLICT DO NOTHING;

INSERT INTO knowledge.destination_tags (destination_id, tag)
SELECT destination_id, 'transport:' || suitable_transport
FROM knowledge.destinations
WHERE suitable_transport IS NOT NULL
ON CONFLICT DO NOTHING;

COMMIT;

-- Verification queries:
-- SELECT COUNT(*) FROM knowledge.destinations;
-- SELECT destination_id, canonical_name, province_name, city_name, status FROM knowledge.destinations ORDER BY destination_id;
-- SELECT d.canonical_name, s.verification_status, ds.evidence_note
-- FROM knowledge.destinations d
-- JOIN knowledge.destination_sources ds ON ds.destination_id = d.destination_id
-- JOIN knowledge.knowledge_sources s ON s.source_id = ds.source_id;
