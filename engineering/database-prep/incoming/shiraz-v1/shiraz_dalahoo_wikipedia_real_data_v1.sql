\set ON_ERROR_STOP on
-- Ai_Tourism — Shiraz factual data enrichment v1
-- Generated from the companion JSON dataset. Additive and idempotent.
-- All factual candidate records are NON-SYNTHETIC but remain needs_review.
-- No production publication, schema migration, embeddings, or application code is performed.
BEGIN;

-- Guard the expected schema contract before any data changes.
DO $$
BEGIN
    IF to_regclass('knowledge.destinations') IS NULL
       OR to_regclass('knowledge.knowledge_sources') IS NULL
       OR to_regclass('knowledge.destination_sources') IS NULL
       OR to_regclass('knowledge.destination_tags') IS NULL
       OR to_regclass('knowledge.destination_categories') IS NULL
       OR to_regclass('knowledge.destination_category_map') IS NULL
       OR to_regclass('operations.dataset_import_batches') IS NULL THEN
        RAISE EXCEPTION 'Expected Ai_Tourism MVP knowledge/import schema is not present; aborting.';
    END IF;
END $$;

-- Source registry: verified refers to the source URL being inspected, not automatic
-- editorial approval of each tourism record.
CREATE TEMP TABLE _shiraz_sources (
    source_key TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_role TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    url TEXT NOT NULL,
    notes TEXT NOT NULL
) ON COMMIT DROP;

INSERT INTO _shiraz_sources VALUES
('dalahoo-destination-index', 'Dalahoo domestic destination index', 'tourism_editorial_discovery', 'discovery', 'verified', 'https://dalahoo.com/destinationlist.cfm', 'Dalahoo destination index used only to discover listed Iranian destinations and provincial grouping. Presence in this index does not verify detailed descriptions, coordinates, opening hours, access, safety, prices, or suitability. Accessed 2026-11-05.'),
('dalahoo-shiraz-guide', 'Dalahoo Shiraz destination guide', 'tourism_editorial_guide', 'discovery', 'verified', 'https://dalahoo.com/destination.cfm?id=17785&loc=1', 'Dalahoo Shiraz destination guide used for place and local-food discovery and limited visitor-oriented context. Descriptions are independently paraphrased. Tour-specific walking durations, ages, transport and itinerary details are NOT generalized to individual places. Accessed 2026-11-05.'),
('wikipedia-shiraz', 'Wikipedia — Shiraz', 'encyclopedia_reference', 'secondary', 'verified', 'https://en.wikipedia.org/wiki/Shiraz', 'Secondary reference for Shiraz identity, location and representative city coordinate. Coordinate is a city reference point, not an entrance or user-position point. Cross-check against authoritative mapping before publication. Accessed 2026-11-05.'),
('wikipedia-hafez', 'Wikipedia — Tomb of Hafez', 'encyclopedia_reference', 'secondary', 'verified', 'https://en.wikipedia.org/wiki/Tomb_of_Hafez', 'Secondary identity/location reference and article coordinate for the Hafezieh site. Coordinate is stored as a representative point, not an entrance. Accessed 2026-11-05.'),
('wikipedia-saadi', 'Wikipedia — Tomb of Saadi', 'encyclopedia_reference', 'secondary', 'verified', 'https://en.wikipedia.org/wiki/Tomb_of_Saadi', 'Secondary identity/location reference and article coordinate for Saadieh. Coordinate is stored as a representative point, not an entrance. Accessed 2026-11-05.'),
('wikipedia-arg-karim-khan', 'Wikipedia — Arg of Karim Khan', 'encyclopedia_reference', 'secondary', 'verified', 'https://en.wikipedia.org/wiki/Arg_of_Karim_Khan', 'Secondary historical/identity reference and article coordinate. Coordinate is stored as a representative point, not a visitor entrance. Article contains citation-quality limitations; owner review remains required. Accessed 2026-11-05.'),
('wikipedia-qavam-house', 'Wikipedia — Qavam House', 'encyclopedia_reference', 'secondary', 'verified', 'https://en.wikipedia.org/wiki/Qavam_House', 'Secondary identity/location and coordinate reference for Qavam House/Narenjestan-e Qavam. Coordinate is a representative point, not an entrance. Accessed 2026-11-05.'),
('wikipedia-eram-garden', 'Wikipedia — Eram Garden', 'encyclopedia_reference', 'secondary', 'verified', 'https://en.wikipedia.org/wiki/Eram_Garden', 'Secondary identity/location and coordinate reference for Eram Garden. Coordinate is a representative point, not an entrance. Accessed 2026-11-05.'),
('wikipedia-delgosha-garden', 'Wikipedia — Delgosha Garden', 'encyclopedia_reference', 'secondary', 'verified', 'https://en.wikipedia.org/wiki/Delgosha_Garden', 'Secondary identity/location and coordinate reference for Delgosha Garden. Coordinate is a representative point, not an entrance. Accessed 2026-11-05.'),
('wikipedia-vakil-bathhouse', 'Wikipedia — Vakil Bathhouse', 'encyclopedia_reference', 'secondary', 'verified', 'https://en.wikipedia.org/wiki/Vakil_Bathhouse', 'Secondary identity/location and coordinate reference for Vakil Bathhouse. Coordinate is a representative point, not an entrance. Accessed 2026-11-05.'),
('wikipedia-shah-cheragh', 'Wikipedia — Shah Cheragh', 'encyclopedia_reference', 'secondary', 'verified', 'https://en.wikipedia.org/wiki/Shah_Cheragh', 'Secondary identity/location and coordinate reference for the Shah Cheragh complex. Coordinate is a representative point, not an entrance. Accessed 2026-11-05.'),
('wikipedia-vakil-bazaar', 'Wikipedia — Vakil Bazaar', 'encyclopedia_reference', 'secondary', 'verified', 'https://en.wikipedia.org/wiki/Vakil_Bazaar', 'Secondary identity/location and coordinate reference for Vakil Bazaar. Coordinate is a representative point, not an entrance. Accessed 2026-11-05.'),
('wikipedia-nasir-ol-molk', 'Wikipedia — Nasir-ol-Molk Mosque', 'encyclopedia_reference', 'secondary', 'verified', 'https://en.wikipedia.org/wiki/Nasir-ol-Molk_Mosque', 'Secondary identity/location, coordinate and construction-period reference. Article notes the building was completed in 1888 and includes stained-glass features. Coordinate is a representative point, not an entrance. Accessed 2026-11-05.'),
('wikipedia-afifabad', 'Wikipedia — Afif-Abad Garden', 'encyclopedia_reference', 'secondary', 'verified', 'https://en.wikipedia.org/wiki/Afif-Abad_Garden', 'Secondary identity/location and coordinate reference. The article describes the site as a garden/museum complex in Shiraz. Coordinate is a representative point, not an entrance. Accessed 2026-11-05.'),
('wikipedia-naqsh-e-rostam', 'Wikipedia — Naqsh-e Rostam', 'encyclopedia_reference', 'secondary', 'verified', 'https://en.wikipedia.org/wiki/Naqsh-e_Rostam', 'Secondary identity/location and article coordinate reference. The site is in Marvdasht, Fars Province, about 13 km northwest of Persepolis; it is not inside urban Shiraz. Coordinate is a representative site point. Accessed 2026-11-05.'),
('dalahoo-maragheh-guide', 'Dalahoo Maragheh Observatory destination guide', 'tourism_editorial_guide', 'secondary', 'verified', 'https://dalahoo.com/destination.cfm?id=16333&loc=1', 'Dalahoo guide used for discovery and visitor-oriented description of Maragheh Observatory and nearby attractions. Tour itinerary durations and transport times are not generalized as permanent site attributes. Accessed 2026-11-05.'),
('astronomical-heritage-maragheh', 'UNESCO Portal to the Heritage of Astronomy — Maragheh Observatory', 'institutional_heritage_reference', 'primary', 'verified', 'https://web.astronomicalheritage.net/index.php/show-entity?identity=29&idsubentity=1&tmpl=system', 'Institutional astronomical-heritage reference for the observatory''s historical significance and published geographic position: 37°23′46″N, 46°12′33″E. Accessed 2026-11-05.'),
('mapcarta-maragheh', 'Mapcarta / OpenStreetMap — Maragheh Observatory', 'geographic_cross_check', 'verification', 'verified', 'https://mapcarta.com/W474626923', 'Map-based secondary cross-check based on OpenStreetMap/Wikidata and related sources. Coordinates differ by only a small offset from the institutional reference; use for cross-check only, not as the primary coordinate authority. Accessed 2026-11-05.');

INSERT INTO knowledge.knowledge_sources
    (source_name, source_type, verification_status, reliability_score, url, notes, is_synthetic)
SELECT source_name, source_type, verification_status, NULL, url, notes, FALSE
FROM _shiraz_sources
ON CONFLICT (source_name) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    verification_status = EXCLUDED.verification_status,
    url = EXCLUDED.url,
    notes = EXCLUDED.notes,
    is_synthetic = FALSE,
    updated_at = NOW();

CREATE TEMP TABLE _shiraz_entities (
    destination_key TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    destination_type TEXT NOT NULL,
    province_name TEXT NOT NULL,
    city_name TEXT,
    parent_key TEXT,
    description TEXT NOT NULL,
    aliases TEXT[] NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    coordinate_role TEXT NOT NULL,
    local_food TEXT,
    scope TEXT NOT NULL,
    tags TEXT[] NOT NULL,
    categories TEXT[] NOT NULL,
    source_keys TEXT[] NOT NULL,
    evidence_note TEXT NOT NULL
) ON COMMIT DROP;

INSERT INTO _shiraz_entities VALUES
('shiraz-city-v1', 'شیراز', 'city', 'فارس', 'شیراز', NULL, 'شیراز مرکز استان فارس در جنوب‌غرب ایران است. این شهر به‌واسطهٔ پیوندهای شناخته‌شده با شعر فارسی، باغ‌های تاریخی و آثار فرهنگی و معماری، یکی از مقصدهای مهم گردشگری فرهنگی ایران به‌شمار می‌رود.', ARRAY['Shiraz', 'Shīrāz', 'شهر شیراز']::TEXT[], 29.61, 52.5425, 'representative_point', 'شیرازی‌پلو، شکرپلو، قورمه‌به، دوپیازه‌آلو، کلم‌پلو شیرازی، رب‌پلو، مسقطی، کاک، عرق بیدمشک', 'city', ARRAY['pilot:shiraz', 'geographic_level:city', 'destination_scope:in_city', 'cultural_destination']::TEXT[], ARRAY['historical']::TEXT[], ARRAY['dalahoo-shiraz-guide', 'wikipedia-shiraz']::TEXT[], 'Dalahoo معرفی فرهنگی مقصد شیراز را ارائه می‌کند؛ مختصات نقطه مرجع شهر از مقاله Wikipedia — Shiraz استخراج شده است.'),
('shiraz-hafezieh-v1', 'آرامگاه حافظ (حافظیه)', 'historic_memorial', 'فارس', 'شیراز', 'shiraz-city-v1', 'آرامگاه حافظ، شاعر فارسی‌گوی سدهٔ هشتم هجری، در مجموعهٔ باغ مصلی در بخش شمالی شیراز قرار دارد. این مکان از جاذبه‌های شاخص فرهنگی شهر است.', ARRAY['حافظیه', 'آرامگاه خواجه شمس‌الدین حافظ شیرازی', 'Tomb of Hafez', 'Hafezieh']::TEXT[], 29.6254028, 52.5583194, 'representative_point', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'attraction', 'literary_heritage', 'historic_memorial']::TEXT[], ARRAY['historical']::TEXT[], ARRAY['dalahoo-shiraz-guide', 'wikipedia-hafez']::TEXT[], 'Dalahoo نام حافظیه را در فهرست جاذبه‌های شیراز آورده است؛ Wikipedia موقعیت شهری و مختصات مقاله را پشتیبانی می‌کند.'),
('shiraz-saadieh-v1', 'آرامگاه سعدی (سعدیه)', 'historic_memorial', 'فارس', 'شیراز', 'shiraz-city-v1', 'آرامگاه سعدی، شاعر و نویسندهٔ فارسی‌زبان سدهٔ هفتم هجری، در شیراز قرار دارد و از مکان‌های مهم میراث ادبی شهر محسوب می‌شود.', ARRAY['سعدیه', 'آرامگاه سعدی شیرازی', 'Tomb of Saadi', 'Saadieh']::TEXT[], 29.6225, 52.58306, 'representative_point', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'attraction', 'literary_heritage', 'historic_memorial']::TEXT[], ARRAY['historical']::TEXT[], ARRAY['dalahoo-shiraz-guide', 'wikipedia-saadi']::TEXT[], 'Dalahoo آرامگاه سعدی را در فهرست جاذبه‌های شیراز معرفی می‌کند؛ Wikipedia موقعیت و مختصات را پشتیبانی می‌کند.'),
('shiraz-arg-karim-khan-v1', 'ارگ کریم‌خان زند', 'historic_citadel', 'فارس', 'شیراز', 'shiraz-city-v1', 'ارگ کریم‌خان در مرکز شیراز از بناهای شاخص دورهٔ زندیه است. ساخت آن در دههٔ ۱۷۶۰ میلادی آغاز و در همان دوره تکمیل شد و در منابع تاریخی به‌عنوان ارگ و محل اقامت کریم‌خان زند معرفی می‌شود.', ARRAY['ارگ کریم خان', 'ارگ کریم‌خان', 'Karim Khan Citadel', 'Arg-e Karim Khan']::TEXT[], 29.6174, 52.5446, 'representative_point', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'attraction', 'zand_era', 'historic_citadel']::TEXT[], ARRAY['historical']::TEXT[], ARRAY['dalahoo-shiraz-guide', 'wikipedia-arg-karim-khan']::TEXT[], 'Dalahoo نام ارگ را در جاذبه‌های شیراز آورده؛ مقاله Wikipedia برای هویت تاریخی، دوره ساخت و مختصات استفاده شده است.'),
('shiraz-narenjestan-qavam-v1', 'نارنجستان قوام (خانه قوام)', 'historic_house_garden', 'فارس', 'شیراز', 'shiraz-city-v1', 'نارنجستان قوام یا خانهٔ قوام، مجموعه‌ای تاریخی از خانه و باغ در شیراز است که در دورهٔ قاجار و در نیمهٔ دوم سدهٔ نوزدهم ساخته شد.', ARRAY['نارنجستان قوام', 'خانه قوام', 'باغ قوام', 'Qavam House', 'Narenjestan-e Qavam']::TEXT[], 29.6078444, 52.5525694, 'representative_point', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'attraction', 'qajar_era', 'historic_house_garden']::TEXT[], ARRAY['historical']::TEXT[], ARRAY['dalahoo-shiraz-guide', 'wikipedia-qavam-house']::TEXT[], 'Dalahoo نام نارنجستان قوام را در جاذبه‌های شیراز آورده؛ Wikipedia هویت بنا و مختصات مقاله را پشتیبانی می‌کند.'),
('shiraz-eram-garden-v1', 'باغ ارم', 'historic_garden', 'فارس', 'شیراز', 'shiraz-city-v1', 'باغ ارم از باغ‌های تاریخی شناخته‌شدهٔ شیراز است و در مجموعهٔ میراث جهانی «باغ ایرانی» ثبت شده است. این رکورد به باغ اشاره دارد و مختصات آن نقطهٔ مرجع مکانی است، نه ورودی بازدیدکنندگان.', ARRAY['باغ ارم شیراز', 'Eram Garden', 'Bagh-e Eram']::TEXT[], 29.63583, 52.52528, 'representative_point', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'attraction', 'historic_garden', 'persian_garden']::TEXT[], ARRAY['historical', 'nature']::TEXT[], ARRAY['dalahoo-shiraz-guide', 'wikipedia-eram-garden']::TEXT[], 'Dalahoo باغ ارم را در جاذبه‌های شیراز فهرست می‌کند؛ Wikipedia برای هویت باغ و مختصات استفاده شده است.'),
('shiraz-delgosha-garden-v1', 'باغ دلگشا', 'historic_garden', 'فارس', 'شیراز', 'shiraz-city-v1', 'باغ دلگشا باغی تاریخی در شیراز و در نزدیکی آرامگاه سعدی است. مختصات ذخیره‌شده نقطهٔ مرجع مقالهٔ جغرافیایی است و به‌معنای ورودی باغ نیست.', ARRAY['باغ دلگشا شیراز', 'Delgosha Garden']::TEXT[], 29.6197, 52.5751, 'representative_point', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'attraction', 'historic_garden', 'persian_garden']::TEXT[], ARRAY['historical', 'nature']::TEXT[], ARRAY['dalahoo-shiraz-guide', 'wikipedia-delgosha-garden']::TEXT[], 'Dalahoo باغ دلگشا را در فهرست جاذبه‌های شیراز آورده؛ Wikipedia موقعیت نزدیک سعدیه و مختصات را پشتیبانی می‌کند.'),
('shiraz-vakil-bathhouse-v1', 'حمام وکیل', 'historic_bathhouse', 'فارس', 'شیراز', 'shiraz-city-v1', 'حمام وکیل از بناهای تاریخی مجموعهٔ وکیل در شیراز و متعلق به دورهٔ زندیه است. این بنا نمونه‌ای از حمام عمومی سنتی ایرانی در بافت تاریخی شهر به‌شمار می‌رود.', ARRAY['حمام وکیل شیراز', 'Vakil Bathhouse', 'Hammam-e Vakil']::TEXT[], 29.61477, 52.54512, 'representative_point', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'attraction', 'zand_era', 'historic_bathhouse']::TEXT[], ARRAY['historical']::TEXT[], ARRAY['dalahoo-shiraz-guide', 'wikipedia-vakil-bathhouse']::TEXT[], 'Dalahoo حمام وکیل را در فهرست جاذبه‌های شیراز آورده؛ Wikipedia برای هویت بنا، دوره تاریخی و مختصات استفاده شده است.'),
('shiraz-shah-cheragh-v1', 'شاه‌چراغ', 'religious_complex', 'فارس', 'شیراز', 'shiraz-city-v1', 'شاه‌چراغ مجموعه‌ای زیارتی و مذهبی در شیراز است که با آرامگاه احمد بن موسی شناخته می‌شود. مختصات این رکورد نقطهٔ مرجع مجموعه است و ورودی کنترل‌شده یا مسیر دسترسی را مشخص نمی‌کند.', ARRAY['آستان شاهچراغ', 'شاه چراغ', 'Shah Cheragh', 'Shah-e Cheragh']::TEXT[], 29.609611, 52.543306, 'representative_point', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'attraction', 'religious_heritage', 'religious_complex']::TEXT[], ARRAY['historical']::TEXT[], ARRAY['dalahoo-shiraz-guide', 'wikipedia-shah-cheragh']::TEXT[], 'Dalahoo شاه‌چراغ را در فهرست جاذبه‌های شیراز می‌آورد؛ Wikipedia هویت مجموعه و مختصات مقاله را پشتیبانی می‌کند.'),
('shiraz-vakil-bazaar-v1', 'بازار وکیل', 'historic_bazaar', 'فارس', 'شیراز', 'shiraz-city-v1', 'بازار وکیل از بازارهای تاریخی مرکز شیراز و از آثار مرتبط با دورهٔ زندیه است. مختصات ثبت‌شده نقطهٔ مرجع بازار است؛ برای مسیریابی دقیق باید ورودی یا گذر موردنظر جداگانه مشخص شود.', ARRAY['بازار وکیل شیراز', 'Vakil Bazaar', 'Bazar-e Vakil']::TEXT[], 29.6149806, 52.5467972, 'representative_point', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'attraction', 'zand_era', 'historic_bazaar', 'shopping']::TEXT[], ARRAY['historical']::TEXT[], ARRAY['dalahoo-shiraz-guide', 'wikipedia-vakil-bazaar']::TEXT[], 'Dalahoo بازار وکیل را در فهرست جاذبه‌های شیراز می‌آورد؛ Wikipedia برای موقعیت مرکزی و مختصات مقاله استفاده شده است.'),
('shiraz-nasir-ol-molk-v1', 'مسجد نصیرالملک', 'historic_mosque', 'فارس', 'شیراز', 'shiraz-city-v1', 'مسجد نصیرالملک در محلهٔ گود عربان شیراز قرار دارد. ساخت آن در دورهٔ قاجار آغاز شد و در سال ۱۸۸۸ میلادی تکمیل شد؛ شیشه‌های رنگی و آرایه‌های معماری آن از ویژگی‌های شناخته‌شدهٔ بنا هستند.', ARRAY['مسجد صورتی', 'مسجد نصیر الملک', 'Nasir al-Mulk Mosque', 'Pink Mosque']::TEXT[], 29.60861, 52.54833, 'representative_point', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'attraction', 'qajar_era', 'historic_mosque', 'architecture']::TEXT[], ARRAY['historical']::TEXT[], ARRAY['wikipedia-nasir-ol-molk']::TEXT[], 'صفحه Wikipedia — Nasir-ol-Molk Mosque موقعیت، دوره ساخت، سال تکمیل و مختصات را گزارش می‌کند؛ در فهرست صفحه اختصاصی دالاهو که بررسی شد نام این مسجد به‌طور قطعی در فهرست جاذبه‌ها احراز نشد، بنابراین منبع دالاهو به آن نسبت داده نشده است.'),
('shiraz-afifabad-garden-v1', 'باغ عفیف‌آباد (باغ گلشن)', 'historic_garden_museum', 'فارس', 'شیراز', 'shiraz-city-v1', 'باغ عفیف‌آباد که با نام باغ گلشن نیز شناخته می‌شود، مجموعه‌ای از باغ و عمارت تاریخی در شیراز است و در منابع معرفی‌شده کارکرد موزه‌ای نیز برای آن ذکر شده است.', ARRAY['باغ عفیف آباد', 'باغ گلشن', 'Afif-Abad Garden', 'Gulshan Garden']::TEXT[], 29.6231611, 52.498361, 'representative_point', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'attraction', 'historic_garden', 'museum']::TEXT[], ARRAY['historical', 'nature']::TEXT[], ARRAY['wikipedia-afifabad']::TEXT[], 'Wikipedia — Afif-Abad Garden هویت مجموعه، جایگاه آن در شیراز و مختصات را پشتیبانی می‌کند؛ Dalahoo Shiraz guide به‌عنوان منبع اختصاصی این رکورد استفاده نشده است.'),
('shiraz-naqsh-e-rostam-v1', 'نقش رستم', 'archaeological_necropolis', 'فارس', 'مرودشت', NULL, 'نقش رستم محوطه‌ای باستانی و آرامستان شاهی در شهرستان مرودشت استان فارس است؛ حدود ۱۳ کیلومتر شمال‌غرب تخت‌جمشید قرار دارد و آرامگاه‌های صخره‌ای هخامنشی و نقش‌برجسته‌های دورهٔ ساسانی را دربرمی‌گیرد. این مکان داخل محدودهٔ شهری شیراز نیست و باید به‌عنوان سفر جداگانهٔ اطراف شیراز در نظر گرفته شود.', ARRAY['نقش‌رستم', 'Naqsh-e Rostam', 'Naqsh-i Rustam']::TEXT[], 29.98889, 52.87472, 'representative_point', NULL, 'nearby_trip', ARRAY['pilot:shiraz', 'destination_scope:nearby_trip', 'outside_shiraz', 'archaeology', 'achaemenid', 'sassanid']::TEXT[], ARRAY['historical']::TEXT[], ARRAY['dalahoo-shiraz-guide', 'wikipedia-naqsh-e-rostam']::TEXT[], 'Wikipedia موقعیت نقش‌رستم در مرودشت و فاصله تقریبی آن تا تخت‌جمشید را گزارش می‌کند؛ Dalahoo آن را در محتوای مقصد شیراز/تورهای مرتبط فهرست می‌کند. این رابطه به‌معنای قرارگیری در شهر شیراز نیست.'),
('shiraz-shirazi-polo-v1', 'شیرازی‌پلو', 'food_dish', 'فارس', 'شیراز', 'shiraz-city-v1', 'دالاهو شیرازی‌پلو را در معرفی خوراک‌های محلی شیراز نام می‌برد و برای آن ترکیبی از برنج، مرغ، بادمجان و زرشک را ذکر می‌کند. این توصیف بازنویسی منبع است و جایگزین دستور پخت منطقه‌ای یا استاندارد واحد نیست.', ARRAY['شیرازی پلو', 'Shirazi Polo']::TEXT[], NULL, NULL, 'unknown', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'food_experience', 'local_dish', 'shiraz_cuisine']::TEXT[], ARRAY[]::TEXT[], ARRAY['dalahoo-shiraz-guide']::TEXT[], 'صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.'),
('shiraz-shakar-polo-v1', 'شکرپلو', 'food_dish', 'فارس', 'شیراز', 'shiraz-city-v1', 'دالاهو شکرپلو را از غذاهای محلی مرتبط با شیراز معرفی می‌کند و می‌گوید معمولاً در کنار خورش قیمه سرو می‌شود. جزئیات مواد اولیه و دستور تهیه در این رکورد فراتر از منبع گسترش داده نشده است.', ARRAY['شکر پلو', 'Shakar Polo']::TEXT[], NULL, NULL, 'unknown', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'food_experience', 'local_dish', 'shiraz_cuisine']::TEXT[], ARRAY[]::TEXT[], ARRAY['dalahoo-shiraz-guide']::TEXT[], 'صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.'),
('shiraz-ghormeh-beh-v1', 'قورمه‌به', 'food_dish', 'فارس', 'شیراز', 'shiraz-city-v1', 'نام قورمه‌به در فهرست غذاهای محلی معرفی‌شده برای شیراز در صفحهٔ دالاهو آمده است. مواد اولیه، دستور، شیوهٔ سرو و محل‌های ارائه در این منبع به‌اندازه‌ای مستند نشده که به‌صورت ویژگی قطعی ثبت شود.', ARRAY['قورمه به', 'Ghormeh Beh']::TEXT[], NULL, NULL, 'unknown', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'food_experience', 'local_dish', 'shiraz_cuisine']::TEXT[], ARRAY[]::TEXT[], ARRAY['dalahoo-shiraz-guide']::TEXT[], 'صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.'),
('shiraz-do-piazeh-aloo-v1', 'دوپیازه‌آلو', 'food_dish', 'فارس', 'شیراز', 'shiraz-city-v1', 'نام دوپیازه‌آلو در فهرست غذاهای محلی معرفی‌شده برای شیراز در صفحهٔ دالاهو آمده است. این رکورد فقط حضور نام در فهرست منبع را ثبت می‌کند و دربارهٔ مواد اولیه یا دستور تهیه ادعای مستقلی ندارد.', ARRAY['دو پیازه آلو', 'Do-piazeh Aloo']::TEXT[], NULL, NULL, 'unknown', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'food_experience', 'local_dish', 'shiraz_cuisine']::TEXT[], ARRAY[]::TEXT[], ARRAY['dalahoo-shiraz-guide']::TEXT[], 'صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.'),
('shiraz-kalam-polo-v1', 'کلم‌پلو شیرازی', 'food_dish', 'فارس', 'شیراز', 'shiraz-city-v1', 'کلم‌پلو شیرازی در فهرست خوراک‌های محلی صفحهٔ دالاهو برای شیراز ذکر شده است. این رکورد برای شناسایی تجربهٔ غذایی است؛ دستور، مواد اولیه و کیفیت رستوران‌ها جداگانه نیازمند منبع‌اند.', ARRAY['کلم پلو شیرازی', 'Kalam Polo Shirazi']::TEXT[], NULL, NULL, 'unknown', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'food_experience', 'local_dish', 'shiraz_cuisine']::TEXT[], ARRAY[]::TEXT[], ARRAY['dalahoo-shiraz-guide']::TEXT[], 'صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.'),
('shiraz-rob-polo-v1', 'رب‌پلو', 'food_dish', 'فارس', 'شیراز', 'shiraz-city-v1', 'رب‌پلو در فهرست خوراک‌های محلی صفحهٔ دالاهو برای شیراز ذکر شده است. جزئیات دستور و ترکیب مواد در رکورد فعلی تأیید نشده و عمداً حدس زده نشده است.', ARRAY['رب پلو', 'Rob Polo']::TEXT[], NULL, NULL, 'unknown', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'food_experience', 'local_dish', 'shiraz_cuisine']::TEXT[], ARRAY[]::TEXT[], ARRAY['dalahoo-shiraz-guide']::TEXT[], 'صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.'),
('shiraz-masghati-v1', 'مسقطی', 'local_sweet', 'فارس', 'شیراز', 'shiraz-city-v1', 'مسقطی در بخش خوراکی‌ها و سوغات مرتبط با شیراز در صفحهٔ دالاهو نام برده شده است. این رکورد نوع خوراکی را ثبت می‌کند؛ تولیدکننده، فروشگاه و دستور دقیق آن هنوز مستند نشده‌اند.', ARRAY['مسقطی شیرازی', 'Masghati']::TEXT[], NULL, NULL, 'unknown', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'food_experience', 'local_sweet', 'souvenir_food']::TEXT[], ARRAY[]::TEXT[], ARRAY['dalahoo-shiraz-guide']::TEXT[], 'صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.'),
('shiraz-kak-v1', 'کاک', 'local_sweet', 'فارس', 'شیراز', 'shiraz-city-v1', 'کاک در فهرست خوراکی‌ها و سوغات مرتبط با شیراز در صفحهٔ دالاهو نام برده شده است. این رکورد تنها نام محصول را به مقصد مرتبط می‌کند و دربارهٔ مواد اولیه یا فروشندگان ادعایی ندارد.', ARRAY['کاک شیرازی', 'کاک']::TEXT[], NULL, NULL, 'unknown', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'food_experience', 'local_sweet', 'souvenir_food']::TEXT[], ARRAY[]::TEXT[], ARRAY['dalahoo-shiraz-guide']::TEXT[], 'صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.'),
('shiraz-bidmeshk-distillate-v1', 'عرق بیدمشک', 'local_drink', 'فارس', 'شیراز', 'shiraz-city-v1', 'عرق بیدمشک در بخش عرقیات و خوراکی‌های محلی/سوغات صفحهٔ دالاهو برای شیراز ذکر شده است. این رکورد به محصول محلی اشاره دارد و محل تولید، فروشنده یا ویژگی‌های درمانی را ادعا نمی‌کند.', ARRAY['عرق بیدمشک', 'Bidmeshk']::TEXT[], NULL, NULL, 'unknown', NULL, 'in_city', ARRAY['pilot:shiraz', 'destination_scope:in_city', 'food_experience', 'local_drink', 'souvenir_food']::TEXT[], ARRAY[]::TEXT[], ARRAY['dalahoo-shiraz-guide']::TEXT[], 'صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.');

-- 1) Insert/update the Shiraz city parent first.
INSERT INTO knowledge.destinations
    (destination_key, country_code, canonical_name, destination_type, province_name, city_name,
     parent_destination_id, description, aliases, latitude, longitude, coordinate_role,
     status, data_confidence, record_origin, verification_status, is_synthetic, local_food)
SELECT e.destination_key, 'IR', e.canonical_name, e.destination_type, e.province_name, e.city_name,
       NULL, e.description, e.aliases, e.latitude, e.longitude, e.coordinate_role,
       'needs_review', 0, 'verified_external', 'verified', FALSE, e.local_food
FROM _shiraz_entities e
WHERE e.destination_key = 'shiraz-city-v1'
ON CONFLICT DO NOTHING;

UPDATE knowledge.destinations d
SET destination_type = e.destination_type,
    description = e.description,
    aliases = (
        SELECT ARRAY(SELECT DISTINCT a
                     FROM unnest(COALESCE(d.aliases, ARRAY[]::TEXT[]) || e.aliases) AS a
                     ORDER BY a)
    ),
    latitude = e.latitude,
    longitude = e.longitude,
    coordinate_role = e.coordinate_role,
    local_food = e.local_food,
    status = 'needs_review',
    data_confidence = 0,
    record_origin = 'verified_external',
    verification_status = 'verified',
    is_synthetic = FALSE,
    updated_at = NOW()
FROM _shiraz_entities e
WHERE e.destination_key = 'shiraz-city-v1'
  AND (d.destination_key = e.destination_key
       OR (d.canonical_name=e.canonical_name AND d.province_name=e.province_name
           AND COALESCE(d.city_name,'')=COALESCE(e.city_name,'')))
  AND d.status IN ('draft','needs_review')
  AND d.is_synthetic = FALSE
  AND d.record_origin IN ('user_supplied_unverified','verified_external');

-- 2) Insert all other city attractions, the nearby day-trip candidate, and food experiences.
INSERT INTO knowledge.destinations
    (destination_key, country_code, canonical_name, destination_type, province_name, city_name,
     parent_destination_id, description, aliases, latitude, longitude, coordinate_role,
     status, data_confidence, record_origin, verification_status, is_synthetic)
SELECT e.destination_key, 'IR', e.canonical_name, e.destination_type, e.province_name, e.city_name,
       CASE WHEN e.parent_key IS NULL THEN NULL ELSE p.destination_id END,
       e.description, e.aliases, e.latitude, e.longitude, e.coordinate_role,
       'needs_review', 0, 'verified_external', 'verified', FALSE
FROM _shiraz_entities e
LEFT JOIN knowledge.destinations p
  ON p.destination_key=e.parent_key
  OR (e.parent_key='shiraz-city-v1'
      AND p.canonical_name='شیراز' AND p.province_name='فارس' AND p.city_name='شیراز')
WHERE e.destination_key <> 'shiraz-city-v1'
ON CONFLICT DO NOTHING;

UPDATE knowledge.destinations d
SET destination_type = e.destination_type,
    description = e.description,
    aliases = (
        SELECT ARRAY(SELECT DISTINCT a
                     FROM unnest(COALESCE(d.aliases, ARRAY[]::TEXT[]) || e.aliases) AS a
                     ORDER BY a)
    ),
    latitude = e.latitude,
    longitude = e.longitude,
    coordinate_role = e.coordinate_role,
    parent_destination_id = CASE
        WHEN d.parent_destination_id IS NULL THEN p.destination_id
        ELSE d.parent_destination_id
    END,
    status = 'needs_review',
    data_confidence = 0,
    record_origin = 'verified_external',
    verification_status = 'verified',
    is_synthetic = FALSE,
    updated_at = NOW()
FROM _shiraz_entities e
LEFT JOIN knowledge.destinations p
  ON p.destination_key=e.parent_key
  OR (e.parent_key='shiraz-city-v1'
      AND p.canonical_name='شیراز' AND p.province_name='فارس' AND p.city_name='شیراز')
WHERE e.destination_key <> 'shiraz-city-v1'
  AND (d.destination_key = e.destination_key
       OR (d.canonical_name=e.canonical_name AND d.province_name=e.province_name
           AND COALESCE(d.city_name,'')=COALESCE(e.city_name,'')))
  AND d.status IN ('draft','needs_review')
  AND d.is_synthetic = FALSE
  AND d.record_origin IN ('user_supplied_unverified','verified_external');

-- 3) Enrich the existing Maragheh Observatory legacy row. The old unsourced
-- difficulty/transport/food/season claims are cleared rather than promoted.
-- If the known legacy identity is absent, a new source-backed row is added.
INSERT INTO knowledge.destinations
    (destination_key, country_code, canonical_name, destination_type, province_name, city_name,
     description, aliases, difficulty, suitable_transport, local_language, local_food,
     local_souvenirs, best_travel_time, latitude, longitude, coordinate_role,
     status, data_confidence, record_origin, verification_status, is_synthetic)
VALUES
    ('maragheh-observatory-v1','IR','رصدخانه مراغه','historical_astronomical_site','آذربایجان شرقی','مراغه',
     'رصدخانهٔ مراغه در تپهٔ رصد داغی در شمال‌غرب شهر مراغه قرار دارد و در سدهٔ هفتم هجری به فرمان هلاکوخان و با سرپرستی خواجه نصیرالدین طوسی ساخته شد. این مجموعه از مراکز مهم رصد و پژوهش نجومی در جهان اسلام در سدهٔ میانه بود.',
     ARRAY['رصدخانه مراغه','Maragheh Observatory','Maragha Observatory']::TEXT[],
     NULL,NULL,NULL,NULL,NULL,NULL,37.396111,46.209167,'representative_point',
     'needs_review',0,'verified_external','verified',FALSE)
ON CONFLICT DO NOTHING;

UPDATE knowledge.destinations d
SET destination_type='historical_astronomical_site',
    description='رصدخانهٔ مراغه در تپهٔ رصد داغی در شمال‌غرب شهر مراغه قرار دارد و در سدهٔ هفتم هجری به فرمان هلاکوخان و با سرپرستی خواجه نصیرالدین طوسی ساخته شد. این مجموعه از مراکز مهم رصد و پژوهش نجومی در جهان اسلام در سدهٔ میانه بود.',
    aliases=(SELECT ARRAY(SELECT DISTINCT a FROM unnest(COALESCE(d.aliases,ARRAY[]::TEXT[]) || ARRAY['رصدخانه مراغه','Maragheh Observatory','Maragha Observatory']::TEXT[]) AS a ORDER BY a)),
    difficulty=NULL, suitable_transport=NULL, local_language=NULL, local_food=NULL,
    local_souvenirs=NULL, best_travel_time=NULL,
    latitude=37.396111, longitude=46.209167, coordinate_role='representative_point',
    status='needs_review', data_confidence=0, record_origin='verified_external',
    verification_status='verified', is_synthetic=FALSE, updated_at=NOW()
WHERE d.canonical_name='رصدخانه مراغه'
  AND d.province_name='آذربایجان شرقی'
  AND d.city_name='مراغه'
  AND d.status IN ('draft','needs_review')
  AND d.is_synthetic=FALSE
  AND d.record_origin IN ('user_supplied_unverified','verified_external');

-- The original Maragheh row carried generic legacy difficulty/transport tags.
-- Remove only those now-unsupported tags; retain its province tag and legacy source history.
DELETE FROM knowledge.destination_tags t
USING knowledge.destinations d
WHERE t.destination_id=d.destination_id
  AND d.canonical_name='رصدخانه مراغه'
  AND d.province_name='آذربایجان شرقی'
  AND d.city_name='مراغه'
  AND t.tag IN ('آسان','transport:سواری');

INSERT INTO knowledge.destination_tags (destination_id, tag)
SELECT d.destination_id, x.tag
FROM knowledge.destinations d
CROSS JOIN (VALUES ('astronomy'),('observatory'),('historical'),('source_enriched')) AS x(tag)
WHERE d.canonical_name='رصدخانه مراغه'
  AND d.province_name='آذربایجان شرقی'
  AND d.city_name='مراغه'
  AND d.status='needs_review'
  AND d.record_origin='verified_external'
  AND d.is_synthetic=FALSE
ON CONFLICT DO NOTHING;

INSERT INTO knowledge.destination_category_map
    (destination_id, category_id, mapping_source, is_synthetic)
SELECT d.destination_id, c.category_id, 'curated_astronomy_heritage_v1', FALSE
FROM knowledge.destinations d
JOIN knowledge.destination_categories c ON c.category_key='historical'
WHERE d.canonical_name='رصدخانه مراغه'
  AND d.province_name='آذربایجان شرقی'
  AND d.city_name='مراغه'
  AND d.status='needs_review'
  AND d.record_origin='verified_external'
  AND d.is_synthetic=FALSE
ON CONFLICT (destination_id, category_id) DO UPDATE SET
    mapping_source=EXCLUDED.mapping_source,
    is_synthetic=FALSE;

-- 4) Attach Dalahoo index entries to existing legacy rows as discovery evidence only.
-- This does not upgrade the legacy rows to verified_external.
INSERT INTO knowledge.destination_sources
    (destination_id, source_id, source_role, evidence_note, retrieved_at)
SELECT d.destination_id, s.source_id, 'discovery',
       'Dalahoo domestic destination index lists this name in the stated province/city context. Discovery evidence only; it does not validate detailed description, access, safety, coordinates, price, hours or seasonality.',
       NOW()
FROM (VALUES

('رصدخانه مراغه', 'آذربایجان شرقی', 'مراغه'),
('شهرستانک', 'البرز', 'کرج'),
('دره زمان', 'تهران', 'تهران'),
('دشت لار', 'تهران', 'تهران'),
('جنگل ابر', 'سمنان', 'شاهرود'),
('سافاری اوپرت تا اولنگ', 'سمنان', 'شاهرود'),
('کالپوش تا آبشار لوه', 'سمنان', 'دامغان'),
('باداب سورت', 'مازندران', 'ساری'),
('رامسر و شمال', 'مازندران', 'رامسر'),
('آبشار عروس دامن', 'مازندران', 'ساری'),
('آبشار گزو', 'مازندران', 'مازندران'),
('دشت دریاسر', 'مازندران', 'ساری'),
('همدان', 'همدان', 'همدان')
) AS x(canonical_name, province_name, city_name)
JOIN knowledge.destinations d
  ON d.canonical_name=x.canonical_name
 AND d.province_name=x.province_name
 AND COALESCE(d.city_name,'')=COALESCE(x.city_name,'')
JOIN knowledge.knowledge_sources s
  ON s.source_name='Dalahoo domestic destination index'
WHERE d.is_synthetic=FALSE
  AND d.status='needs_review'
  AND (
      d.record_origin='user_supplied_unverified'
      OR (d.canonical_name='رصدخانه مراغه'
          AND d.province_name='آذربایجان شرقی' AND d.city_name='مراغه')
  )
ON CONFLICT (destination_id, source_id) DO UPDATE SET
    source_role=EXCLUDED.source_role,
    evidence_note=EXCLUDED.evidence_note,
    retrieved_at=EXCLUDED.retrieved_at;

-- 5) Add source-specific provenance for all new/curated place and food records.
INSERT INTO knowledge.destination_sources
    (destination_id, source_id, source_role, evidence_note, retrieved_at)
SELECT d.destination_id, s.source_id,
       CASE
         WHEN src.source_key IN ('dalahoo-shiraz-guide','dalahoo-maragheh-guide') THEN
           CASE WHEN d.destination_type IN ('food_dish','local_sweet','local_drink')
                THEN 'primary' ELSE 'discovery' END
         ELSE src.source_role
       END,
       e.evidence_note || ' Source: ' || s.url,
       NOW()
FROM _shiraz_entities e
JOIN knowledge.destinations d
  ON d.destination_key=e.destination_key
  OR (d.canonical_name=e.canonical_name AND d.province_name=e.province_name
      AND COALESCE(d.city_name,'')=COALESCE(e.city_name,''))
CROSS JOIN LATERAL unnest(e.source_keys) AS sk(source_key)
JOIN _shiraz_sources src ON src.source_key=sk.source_key
JOIN knowledge.knowledge_sources s ON s.source_name=src.source_name
WHERE d.is_synthetic=FALSE
  AND d.status='needs_review'
ON CONFLICT (destination_id, source_id) DO UPDATE SET
    source_role=EXCLUDED.source_role,
    evidence_note=EXCLUDED.evidence_note,
    retrieved_at=EXCLUDED.retrieved_at;

-- Maragheh Observatory source links.
INSERT INTO knowledge.destination_sources
    (destination_id, source_id, source_role, evidence_note, retrieved_at)
SELECT d.destination_id, s.source_id, x.source_role, x.evidence_note, NOW()
FROM knowledge.destinations d
CROSS JOIN (VALUES
 ('Dalahoo Maragheh Observatory destination guide','secondary','Dalahoo guide provides a visitor-oriented introduction and mentions the observatory and its historical context; tour-specific durations are not treated as permanent site properties.'),
 ('UNESCO Portal to the Heritage of Astronomy — Maragheh Observatory','primary','Institutional astronomy-heritage source supports historical significance and publishes geographic position 37°23′46″N, 46°12′33″E.'),
 ('Mapcarta / OpenStreetMap — Maragheh Observatory','verification','Independent map-based coordinate cross-check; approximate point differs slightly from the institutional reference and is not treated as an entrance.')
) AS x(source_name,source_role,evidence_note)
JOIN knowledge.knowledge_sources s ON s.source_name=x.source_name
WHERE d.canonical_name='رصدخانه مراغه'
  AND d.province_name='آذربایجان شرقی'
  AND d.city_name='مراغه'
  AND d.status='needs_review'
ON CONFLICT (destination_id, source_id) DO UPDATE SET
    source_role=EXCLUDED.source_role,
    evidence_note=EXCLUDED.evidence_note,
    retrieved_at=EXCLUDED.retrieved_at;

-- 6) Link already-existing UNESCO records to the Dalahoo Shiraz discovery context.
-- Do NOT duplicate or overwrite UNESCO identities, descriptions or official coordinates.
INSERT INTO knowledge.destination_sources
    (destination_id, source_id, source_role, evidence_note, retrieved_at)
SELECT d.destination_id, s.source_id, 'discovery',
       'Dalahoo Shiraz destination guide mentions this as a destination associated with a Shiraz trip area; the place remains geographically separate from urban Shiraz and retains its existing UNESCO record/coordinates.',
       NOW()
FROM knowledge.destinations d
JOIN knowledge.knowledge_sources s
  ON s.source_name='Dalahoo Shiraz destination guide'
WHERE d.destination_key IN ('unesco-persepolis-v1','unesco-pasargadae-v1')
  AND d.is_synthetic=FALSE
ON CONFLICT (destination_id, source_id) DO UPDATE SET
    source_role=EXCLUDED.source_role,
    evidence_note=EXCLUDED.evidence_note,
    retrieved_at=EXCLUDED.retrieved_at;

-- 7) Add non-synthetic tags and controlled category mappings.
INSERT INTO knowledge.destination_tags (destination_id, tag)
SELECT d.destination_id, tag
FROM _shiraz_entities e
JOIN knowledge.destinations d
  ON d.destination_key=e.destination_key
  OR (d.canonical_name=e.canonical_name AND d.province_name=e.province_name
      AND COALESCE(d.city_name,'')=COALESCE(e.city_name,''))
CROSS JOIN LATERAL unnest(e.tags) AS t(tag)
WHERE d.status='needs_review' AND d.is_synthetic=FALSE
ON CONFLICT DO NOTHING;

INSERT INTO knowledge.destination_category_map
    (destination_id, category_id, mapping_source, is_synthetic)
SELECT d.destination_id, c.category_id, 'curated_external_source_v1', FALSE
FROM _shiraz_entities e
JOIN knowledge.destinations d
  ON d.destination_key=e.destination_key
  OR (d.canonical_name=e.canonical_name AND d.province_name=e.province_name
      AND COALESCE(d.city_name,'')=COALESCE(e.city_name,''))
CROSS JOIN LATERAL unnest(e.categories) AS ck(category_key)
JOIN knowledge.destination_categories c ON c.category_key=ck.category_key
WHERE d.status='needs_review' AND d.is_synthetic=FALSE
ON CONFLICT (destination_id, category_id) DO UPDATE SET
    mapping_source=EXCLUDED.mapping_source,
    is_synthetic=FALSE;

-- Explicitly classify the existing nearby UNESCO sites in the Shiraz trip context.
INSERT INTO knowledge.destination_tags (destination_id, tag)
SELECT d.destination_id, x.tag
FROM knowledge.destinations d
CROSS JOIN (VALUES
    ('unesco-persepolis-v1','pilot:shiraz'),
    ('unesco-persepolis-v1','destination_scope:nearby_trip'),
    ('unesco-persepolis-v1','outside_shiraz'),
    ('unesco-pasargadae-v1','pilot:shiraz'),
    ('unesco-pasargadae-v1','destination_scope:nearby_trip'),
    ('unesco-pasargadae-v1','outside_shiraz')
) AS x(destination_key,tag)
WHERE d.destination_key=x.destination_key AND d.is_synthetic=FALSE
ON CONFLICT DO NOTHING;

-- 8) Add one compact Persian knowledge document and one chunk per real candidate record.
-- No embeddings are created; embedding_spaces/chunk_embeddings remain untouched.
CREATE TEMP TABLE _shiraz_docs (
    destination_key TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    province_name TEXT NOT NULL,
    city_name TEXT,
    destination_type TEXT NOT NULL,
    source_key TEXT NOT NULL,
    document_key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    raw_content TEXT NOT NULL,
    content_sha256 CHAR(64) NOT NULL,
    char_count INTEGER NOT NULL,
    scope TEXT NOT NULL,
    coordinate_role TEXT NOT NULL
) ON COMMIT DROP;

INSERT INTO _shiraz_docs VALUES
('shiraz-city-v1', 'شیراز', 'فارس', 'شیراز', 'city', 'wikipedia-shiraz', 'shiraz-city-v1-doc', 'پرونده دانش گردشگری: شیراز', 'https://en.wikipedia.org/wiki/Shiraz', 'نام: شیراز
نام انگلیسی: Shiraz
نوع رکورد: city
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: city
توضیح: شیراز مرکز استان فارس در جنوب‌غرب ایران است. این شهر به‌واسطهٔ پیوندهای شناخته‌شده با شعر فارسی، باغ‌های تاریخی و آثار فرهنگی و معماری، یکی از مقصدهای مهم گردشگری فرهنگی ایران به‌شمار می‌رود.
نقطه مرجع جغرافیایی: عرض 29.61, طول 52.5425
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: Dalahoo معرفی فرهنگی مقصد شیراز را ارائه می‌کند؛ مختصات نقطه مرجع شهر از مقاله Wikipedia — Shiraz استخراج شده است.', '25042d6524d9e30d52e163bbb8d2508e12801fc9f56a06f05c87c6fe2dd65e2c', 540, 'city', 'representative_point'),
('shiraz-hafezieh-v1', 'آرامگاه حافظ (حافظیه)', 'فارس', 'شیراز', 'historic_memorial', 'wikipedia-hafez', 'shiraz-hafezieh-v1-doc', 'پرونده دانش گردشگری: آرامگاه حافظ (حافظیه)', 'https://en.wikipedia.org/wiki/Tomb_of_Hafez', 'نام: آرامگاه حافظ (حافظیه)
نام انگلیسی: Tomb of Hafez / Hafezieh
نوع رکورد: historic_memorial
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: آرامگاه حافظ، شاعر فارسی‌گوی سدهٔ هشتم هجری، در مجموعهٔ باغ مصلی در بخش شمالی شیراز قرار دارد. این مکان از جاذبه‌های شاخص فرهنگی شهر است.
نقطه مرجع جغرافیایی: عرض 29.6254028, طول 52.5583194
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: Dalahoo نام حافظیه را در فهرست جاذبه‌های شیراز آورده است؛ Wikipedia موقعیت شهری و مختصات مقاله را پشتیبانی می‌کند.', '7e6dbd961d6ab9fc70e200b15715073118dc6bd1a74891585df5d9725c7a0091', 544, 'in_city', 'representative_point'),
('shiraz-saadieh-v1', 'آرامگاه سعدی (سعدیه)', 'فارس', 'شیراز', 'historic_memorial', 'wikipedia-saadi', 'shiraz-saadieh-v1-doc', 'پرونده دانش گردشگری: آرامگاه سعدی (سعدیه)', 'https://en.wikipedia.org/wiki/Tomb_of_Saadi', 'نام: آرامگاه سعدی (سعدیه)
نام انگلیسی: Tomb of Saadi / Saadieh
نوع رکورد: historic_memorial
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: آرامگاه سعدی، شاعر و نویسندهٔ فارسی‌زبان سدهٔ هفتم هجری، در شیراز قرار دارد و از مکان‌های مهم میراث ادبی شهر محسوب می‌شود.
نقطه مرجع جغرافیایی: عرض 29.6225, طول 52.58306
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: Dalahoo آرامگاه سعدی را در فهرست جاذبه‌های شیراز معرفی می‌کند؛ Wikipedia موقعیت و مختصات را پشتیبانی می‌کند.', 'f5fd7162e709d83bf7a3c60455404c17a15d140a141d620a43ee4c42d8ce2e16', 516, 'in_city', 'representative_point'),
('shiraz-arg-karim-khan-v1', 'ارگ کریم‌خان زند', 'فارس', 'شیراز', 'historic_citadel', 'wikipedia-arg-karim-khan', 'shiraz-arg-karim-khan-v1-doc', 'پرونده دانش گردشگری: ارگ کریم‌خان زند', 'https://en.wikipedia.org/wiki/Arg_of_Karim_Khan', 'نام: ارگ کریم‌خان زند
نام انگلیسی: Arg of Karim Khan / Karim Khan Citadel
نوع رکورد: historic_citadel
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: ارگ کریم‌خان در مرکز شیراز از بناهای شاخص دورهٔ زندیه است. ساخت آن در دههٔ ۱۷۶۰ میلادی آغاز و در همان دوره تکمیل شد و در منابع تاریخی به‌عنوان ارگ و محل اقامت کریم‌خان زند معرفی می‌شود.
نقطه مرجع جغرافیایی: عرض 29.6174, طول 52.5446
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: Dalahoo نام ارگ را در جاذبه‌های شیراز آورده؛ مقاله Wikipedia برای هویت تاریخی، دوره ساخت و مختصات استفاده شده است.', 'ed4ddbbbf493a0f9712a46d2307c547b6f81b8cec8cf1ac3ff86b87d9e0ca270', 594, 'in_city', 'representative_point'),
('shiraz-narenjestan-qavam-v1', 'نارنجستان قوام (خانه قوام)', 'فارس', 'شیراز', 'historic_house_garden', 'wikipedia-qavam-house', 'shiraz-narenjestan-qavam-v1-doc', 'پرونده دانش گردشگری: نارنجستان قوام (خانه قوام)', 'https://en.wikipedia.org/wiki/Qavam_House', 'نام: نارنجستان قوام (خانه قوام)
نام انگلیسی: Qavam House / Narenjestan-e Qavam
نوع رکورد: historic_house_garden
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: نارنجستان قوام یا خانهٔ قوام، مجموعه‌ای تاریخی از خانه و باغ در شیراز است که در دورهٔ قاجار و در نیمهٔ دوم سدهٔ نوزدهم ساخته شد.
نقطه مرجع جغرافیایی: عرض 29.6078444, طول 52.5525694
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: Dalahoo نام نارنجستان قوام را در جاذبه‌های شیراز آورده؛ Wikipedia هویت بنا و مختصات مقاله را پشتیبانی می‌کند.', 'b7c08344902cdec7fdf8abe3479fff336d28259de09355ee2e9446c8e401fb87', 548, 'in_city', 'representative_point'),
('shiraz-eram-garden-v1', 'باغ ارم', 'فارس', 'شیراز', 'historic_garden', 'wikipedia-eram-garden', 'shiraz-eram-garden-v1-doc', 'پرونده دانش گردشگری: باغ ارم', 'https://en.wikipedia.org/wiki/Eram_Garden', 'نام: باغ ارم
نام انگلیسی: Eram Garden
نوع رکورد: historic_garden
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: باغ ارم از باغ‌های تاریخی شناخته‌شدهٔ شیراز است و در مجموعهٔ میراث جهانی «باغ ایرانی» ثبت شده است. این رکورد به باغ اشاره دارد و مختصات آن نقطهٔ مرجع مکانی است، نه ورودی بازدیدکنندگان.
نقطه مرجع جغرافیایی: عرض 29.63583, طول 52.52528
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: Dalahoo باغ ارم را در جاذبه‌های شیراز فهرست می‌کند؛ Wikipedia برای هویت باغ و مختصات استفاده شده است.', '9c3ee65d5d30eacc736d38890846ab62a615ad48d3dc6726d88a24d75a1ccfbb', 545, 'in_city', 'representative_point'),
('shiraz-delgosha-garden-v1', 'باغ دلگشا', 'فارس', 'شیراز', 'historic_garden', 'wikipedia-delgosha-garden', 'shiraz-delgosha-garden-v1-doc', 'پرونده دانش گردشگری: باغ دلگشا', 'https://en.wikipedia.org/wiki/Delgosha_Garden', 'نام: باغ دلگشا
نام انگلیسی: Delgosha Garden
نوع رکورد: historic_garden
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: باغ دلگشا باغی تاریخی در شیراز و در نزدیکی آرامگاه سعدی است. مختصات ذخیره‌شده نقطهٔ مرجع مقالهٔ جغرافیایی است و به‌معنای ورودی باغ نیست.
نقطه مرجع جغرافیایی: عرض 29.6197, طول 52.5751
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: Dalahoo باغ دلگشا را در فهرست جاذبه‌های شیراز آورده؛ Wikipedia موقعیت نزدیک سعدیه و مختصات را پشتیبانی می‌کند.', '218e58fabc048fe291b9a9a4338ff1abaf1f6983bc6563d28c044c96da3cd2da', 510, 'in_city', 'representative_point'),
('shiraz-vakil-bathhouse-v1', 'حمام وکیل', 'فارس', 'شیراز', 'historic_bathhouse', 'wikipedia-vakil-bathhouse', 'shiraz-vakil-bathhouse-v1-doc', 'پرونده دانش گردشگری: حمام وکیل', 'https://en.wikipedia.org/wiki/Vakil_Bathhouse', 'نام: حمام وکیل
نام انگلیسی: Vakil Bathhouse
نوع رکورد: historic_bathhouse
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: حمام وکیل از بناهای تاریخی مجموعهٔ وکیل در شیراز و متعلق به دورهٔ زندیه است. این بنا نمونه‌ای از حمام عمومی سنتی ایرانی در بافت تاریخی شهر به‌شمار می‌رود.
نقطه مرجع جغرافیایی: عرض 29.61477, طول 52.54512
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: Dalahoo حمام وکیل را در فهرست جاذبه‌های شیراز آورده؛ Wikipedia برای هویت بنا، دوره تاریخی و مختصات استفاده شده است.', 'a9d9fca9a415b6caaa38a4792c3de484109e30f9ed8df8985d2881515b97fe70', 538, 'in_city', 'representative_point'),
('shiraz-shah-cheragh-v1', 'شاه‌چراغ', 'فارس', 'شیراز', 'religious_complex', 'wikipedia-shah-cheragh', 'shiraz-shah-cheragh-v1-doc', 'پرونده دانش گردشگری: شاه‌چراغ', 'https://en.wikipedia.org/wiki/Shah_Cheragh', 'نام: شاه‌چراغ
نام انگلیسی: Shah Cheragh
نوع رکورد: religious_complex
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: شاه‌چراغ مجموعه‌ای زیارتی و مذهبی در شیراز است که با آرامگاه احمد بن موسی شناخته می‌شود. مختصات این رکورد نقطهٔ مرجع مجموعه است و ورودی کنترل‌شده یا مسیر دسترسی را مشخص نمی‌کند.
نقطه مرجع جغرافیایی: عرض 29.609611, طول 52.543306
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: Dalahoo شاه‌چراغ را در فهرست جاذبه‌های شیراز می‌آورد؛ Wikipedia هویت مجموعه و مختصات مقاله را پشتیبانی می‌کند.', '65d5f17ff21dc794cbe167cf2490aa6fd8974660690eac788cf43810b74b9338', 553, 'in_city', 'representative_point'),
('shiraz-vakil-bazaar-v1', 'بازار وکیل', 'فارس', 'شیراز', 'historic_bazaar', 'wikipedia-vakil-bazaar', 'shiraz-vakil-bazaar-v1-doc', 'پرونده دانش گردشگری: بازار وکیل', 'https://en.wikipedia.org/wiki/Vakil_Bazaar', 'نام: بازار وکیل
نام انگلیسی: Vakil Bazaar
نوع رکورد: historic_bazaar
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: بازار وکیل از بازارهای تاریخی مرکز شیراز و از آثار مرتبط با دورهٔ زندیه است. مختصات ثبت‌شده نقطهٔ مرجع بازار است؛ برای مسیریابی دقیق باید ورودی یا گذر موردنظر جداگانه مشخص شود.
نقطه مرجع جغرافیایی: عرض 29.6149806, طول 52.5467972
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: Dalahoo بازار وکیل را در فهرست جاذبه‌های شیراز می‌آورد؛ Wikipedia برای موقعیت مرکزی و مختصات مقاله استفاده شده است.', '0734075a463d821d1674afd0e112fd91ba5bfbba3252fc31fc6148bc9867a4a3', 559, 'in_city', 'representative_point'),
('shiraz-nasir-ol-molk-v1', 'مسجد نصیرالملک', 'فارس', 'شیراز', 'historic_mosque', 'wikipedia-nasir-ol-molk', 'shiraz-nasir-ol-molk-v1-doc', 'پرونده دانش گردشگری: مسجد نصیرالملک', 'https://en.wikipedia.org/wiki/Nasir-ol-Molk_Mosque', 'نام: مسجد نصیرالملک
نام انگلیسی: Nasir-ol-Molk Mosque / Pink Mosque
نوع رکورد: historic_mosque
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: مسجد نصیرالملک در محلهٔ گود عربان شیراز قرار دارد. ساخت آن در دورهٔ قاجار آغاز شد و در سال ۱۸۸۸ میلادی تکمیل شد؛ شیشه‌های رنگی و آرایه‌های معماری آن از ویژگی‌های شناخته‌شدهٔ بنا هستند.
نقطه مرجع جغرافیایی: عرض 29.60861, طول 52.54833
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: صفحه Wikipedia — Nasir-ol-Molk Mosque موقعیت، دوره ساخت، سال تکمیل و مختصات را گزارش می‌کند؛ در فهرست صفحه اختصاصی دالاهو که بررسی شد نام این مسجد به‌طور قطعی در فهرست جاذبه‌ها احراز نشد، بنابراین منبع دالاهو به آن نسبت داده نشده است.', '1bd686f2bf690664c21d13b7d57eccdbcb26b5e95d0cc7f862ad4b4418c21587', 708, 'in_city', 'representative_point'),
('shiraz-afifabad-garden-v1', 'باغ عفیف‌آباد (باغ گلشن)', 'فارس', 'شیراز', 'historic_garden_museum', 'wikipedia-afifabad', 'shiraz-afifabad-garden-v1-doc', 'پرونده دانش گردشگری: باغ عفیف‌آباد (باغ گلشن)', 'https://en.wikipedia.org/wiki/Afif-Abad_Garden', 'نام: باغ عفیف‌آباد (باغ گلشن)
نام انگلیسی: Afif-Abad Garden / Gulshan Garden
نوع رکورد: historic_garden_museum
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: باغ عفیف‌آباد که با نام باغ گلشن نیز شناخته می‌شود، مجموعه‌ای از باغ و عمارت تاریخی در شیراز است و در منابع معرفی‌شده کارکرد موزه‌ای نیز برای آن ذکر شده است.
نقطه مرجع جغرافیایی: عرض 29.6231611, طول 52.498361
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: Wikipedia — Afif-Abad Garden هویت مجموعه، جایگاه آن در شیراز و مختصات را پشتیبانی می‌کند؛ Dalahoo Shiraz guide به‌عنوان منبع اختصاصی این رکورد استفاده نشده است.', 'bc0c85313adadb7d798b1b35b3fa882f3d33c6393c1dd63a3deb678ed0fa2289', 626, 'in_city', 'representative_point'),
('shiraz-naqsh-e-rostam-v1', 'نقش رستم', 'فارس', 'مرودشت', 'archaeological_necropolis', 'wikipedia-naqsh-e-rostam', 'shiraz-naqsh-e-rostam-v1-doc', 'پرونده دانش گردشگری: نقش رستم', 'https://en.wikipedia.org/wiki/Naqsh-e_Rostam', 'نام: نقش رستم
نام انگلیسی: Naqsh-e Rostam
نوع رکورد: archaeological_necropolis
استان: فارس
شهر/محدوده: مرودشت
دامنه مکانی: nearby_trip
توضیح: نقش رستم محوطه‌ای باستانی و آرامستان شاهی در شهرستان مرودشت استان فارس است؛ حدود ۱۳ کیلومتر شمال‌غرب تخت‌جمشید قرار دارد و آرامگاه‌های صخره‌ای هخامنشی و نقش‌برجسته‌های دورهٔ ساسانی را دربرمی‌گیرد. این مکان داخل محدودهٔ شهری شیراز نیست و باید به‌عنوان سفر جداگانهٔ اطراف شیراز در نظر گرفته شود.
نقطه مرجع جغرافیایی: عرض 29.98889, طول 52.87472
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: Wikipedia موقعیت نقش‌رستم در مرودشت و فاصله تقریبی آن تا تخت‌جمشید را گزارش می‌کند؛ Dalahoo آن را در محتوای مقصد شیراز/تورهای مرتبط فهرست می‌کند. این رابطه به‌معنای قرارگیری در شهر شیراز نیست.', 'a91a4a3908378b5c1ba632bbb7c1f3e46db542dad278a3b175629f9361196ed2', 764, 'nearby_trip', 'representative_point'),
('shiraz-shirazi-polo-v1', 'شیرازی‌پلو', 'فارس', 'شیراز', 'food_dish', 'dalahoo-shiraz-guide', 'shiraz-shirazi-polo-v1-doc', 'پرونده دانش گردشگری: شیرازی‌پلو', 'https://dalahoo.com/destination.cfm?id=17785&loc=1', 'نام: شیرازی‌پلو
نام انگلیسی: Shirazi Polo
نوع رکورد: food_dish
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: دالاهو شیرازی‌پلو را در معرفی خوراک‌های محلی شیراز نام می‌برد و برای آن ترکیبی از برنج، مرغ، بادمجان و زرشک را ذکر می‌کند. این توصیف بازنویسی منبع است و جایگزین دستور پخت منطقه‌ای یا استاندارد واحد نیست.
یادداشت شواهد: صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.', '28580753336d4245af47911e503fde532eb3aea829b0878a72f7874ea6805214', 517, 'in_city', 'unknown'),
('shiraz-shakar-polo-v1', 'شکرپلو', 'فارس', 'شیراز', 'food_dish', 'dalahoo-shiraz-guide', 'shiraz-shakar-polo-v1-doc', 'پرونده دانش گردشگری: شکرپلو', 'https://dalahoo.com/destination.cfm?id=17785&loc=1', 'نام: شکرپلو
نام انگلیسی: Shakar Polo
نوع رکورد: food_dish
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: دالاهو شکرپلو را از غذاهای محلی مرتبط با شیراز معرفی می‌کند و می‌گوید معمولاً در کنار خورش قیمه سرو می‌شود. جزئیات مواد اولیه و دستور تهیه در این رکورد فراتر از منبع گسترش داده نشده است.
یادداشت شواهد: صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.', 'f6a94ed0ff3a7180a1aca315f0e0f3c05ecab04b407bdabdaa2cfbbc6e217f96', 495, 'in_city', 'unknown'),
('shiraz-ghormeh-beh-v1', 'قورمه‌به', 'فارس', 'شیراز', 'food_dish', 'dalahoo-shiraz-guide', 'shiraz-ghormeh-beh-v1-doc', 'پرونده دانش گردشگری: قورمه‌به', 'https://dalahoo.com/destination.cfm?id=17785&loc=1', 'نام: قورمه‌به
نام انگلیسی: Ghormeh Beh
نوع رکورد: food_dish
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: نام قورمه‌به در فهرست غذاهای محلی معرفی‌شده برای شیراز در صفحهٔ دالاهو آمده است. مواد اولیه، دستور، شیوهٔ سرو و محل‌های ارائه در این منبع به‌اندازه‌ای مستند نشده که به‌صورت ویژگی قطعی ثبت شود.
یادداشت شواهد: صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.', '68ccfa3b62c1d6fbe995c8699578fd2db5b68b8837a0a11a02d2b192277f6678', 503, 'in_city', 'unknown'),
('shiraz-do-piazeh-aloo-v1', 'دوپیازه‌آلو', 'فارس', 'شیراز', 'food_dish', 'dalahoo-shiraz-guide', 'shiraz-do-piazeh-aloo-v1-doc', 'پرونده دانش گردشگری: دوپیازه‌آلو', 'https://dalahoo.com/destination.cfm?id=17785&loc=1', 'نام: دوپیازه‌آلو
نام انگلیسی: Do Piazeh Aloo
نوع رکورد: food_dish
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: نام دوپیازه‌آلو در فهرست غذاهای محلی معرفی‌شده برای شیراز در صفحهٔ دالاهو آمده است. این رکورد فقط حضور نام در فهرست منبع را ثبت می‌کند و دربارهٔ مواد اولیه یا دستور تهیه ادعای مستقلی ندارد.
یادداشت شواهد: صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.', 'f185ec63b69c624e2dff0ad7143e33381afabaee105f8e9e2a9e5897d7a0a5c8', 506, 'in_city', 'unknown'),
('shiraz-kalam-polo-v1', 'کلم‌پلو شیرازی', 'فارس', 'شیراز', 'food_dish', 'dalahoo-shiraz-guide', 'shiraz-kalam-polo-v1-doc', 'پرونده دانش گردشگری: کلم‌پلو شیرازی', 'https://dalahoo.com/destination.cfm?id=17785&loc=1', 'نام: کلم‌پلو شیرازی
نام انگلیسی: Shirazi Kalam Polo
نوع رکورد: food_dish
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: کلم‌پلو شیرازی در فهرست خوراک‌های محلی صفحهٔ دالاهو برای شیراز ذکر شده است. این رکورد برای شناسایی تجربهٔ غذایی است؛ دستور، مواد اولیه و کیفیت رستوران‌ها جداگانه نیازمند منبع‌اند.
یادداشت شواهد: صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.', 'b437e7b6841c72f89d2f7128bce5631ad9fbf094548ba258dfcc029c94822e3a', 503, 'in_city', 'unknown'),
('shiraz-rob-polo-v1', 'رب‌پلو', 'فارس', 'شیراز', 'food_dish', 'dalahoo-shiraz-guide', 'shiraz-rob-polo-v1-doc', 'پرونده دانش گردشگری: رب‌پلو', 'https://dalahoo.com/destination.cfm?id=17785&loc=1', 'نام: رب‌پلو
نام انگلیسی: Rob Polo
نوع رکورد: food_dish
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: رب‌پلو در فهرست خوراک‌های محلی صفحهٔ دالاهو برای شیراز ذکر شده است. جزئیات دستور و ترکیب مواد در رکورد فعلی تأیید نشده و عمداً حدس زده نشده است.
یادداشت شواهد: صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.', '604c8c98aeda6450b1db5fd65956c6f3a232cea75b1fc8090d53ae12c5974ee9', 450, 'in_city', 'unknown'),
('shiraz-masghati-v1', 'مسقطی', 'فارس', 'شیراز', 'local_sweet', 'dalahoo-shiraz-guide', 'shiraz-masghati-v1-doc', 'پرونده دانش گردشگری: مسقطی', 'https://dalahoo.com/destination.cfm?id=17785&loc=1', 'نام: مسقطی
نام انگلیسی: Masghati
نوع رکورد: local_sweet
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: مسقطی در بخش خوراکی‌ها و سوغات مرتبط با شیراز در صفحهٔ دالاهو نام برده شده است. این رکورد نوع خوراکی را ثبت می‌کند؛ تولیدکننده، فروشگاه و دستور دقیق آن هنوز مستند نشده‌اند.
یادداشت شواهد: صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.', 'cd086afdf455a4119da56e77d54150acbc52c8b9ae5be08527ac217481092d59', 479, 'in_city', 'unknown'),
('shiraz-kak-v1', 'کاک', 'فارس', 'شیراز', 'local_sweet', 'dalahoo-shiraz-guide', 'shiraz-kak-v1-doc', 'پرونده دانش گردشگری: کاک', 'https://dalahoo.com/destination.cfm?id=17785&loc=1', 'نام: کاک
نام انگلیسی: Kak
نوع رکورد: local_sweet
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: کاک در فهرست خوراکی‌ها و سوغات مرتبط با شیراز در صفحهٔ دالاهو نام برده شده است. این رکورد تنها نام محصول را به مقصد مرتبط می‌کند و دربارهٔ مواد اولیه یا فروشندگان ادعایی ندارد.
یادداشت شواهد: صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.', '368c77bf9404060801882f729a1bb87ffaced010f86de441410c030162dccc56', 476, 'in_city', 'unknown'),
('shiraz-bidmeshk-distillate-v1', 'عرق بیدمشک', 'فارس', 'شیراز', 'local_drink', 'dalahoo-shiraz-guide', 'shiraz-bidmeshk-distillate-v1-doc', 'پرونده دانش گردشگری: عرق بیدمشک', 'https://dalahoo.com/destination.cfm?id=17785&loc=1', 'نام: عرق بیدمشک
نام انگلیسی: Bidmeshk Distillate
نوع رکورد: local_drink
استان: فارس
شهر/محدوده: شیراز
دامنه مکانی: in_city
توضیح: عرق بیدمشک در بخش عرقیات و خوراکی‌های محلی/سوغات صفحهٔ دالاهو برای شیراز ذکر شده است. این رکورد به محصول محلی اشاره دارد و محل تولید، فروشنده یا ویژگی‌های درمانی را ادعا نمی‌کند.
یادداشت شواهد: صفحهٔ مقصد شیراز دالاهو نام این خوراکی/محصول را در فهرست خوراک‌های محلی یا سوغات مرتبط با شیراز آورده است. برای اقلامی که توضیح تفصیلی ندارند، فقط نام و پیوند مکانی ثبت شده است.', '92994be2ff35d3a1c0a96d728e5962ed340490f5e9ba93053cfe0a72e221f7b6', 501, 'in_city', 'unknown'),
('maragheh-observatory-v1', 'رصدخانه مراغه', 'آذربایجان شرقی', 'مراغه', 'historical_astronomical_site', 'astronomical-heritage-maragheh', 'maragheh-observatory-v1-doc', 'پرونده دانش گردشگری: رصدخانه مراغه', 'https://web.astronomicalheritage.net/index.php/show-entity?identity=29&idsubentity=1&tmpl=system', 'نام: رصدخانه مراغه
نام انگلیسی: Maragheh Observatory
نوع رکورد: historical_astronomical_site
استان: آذربایجان شرقی
شهر/محدوده: مراغه
دامنه مکانی: existing_destination_enrichment
توضیح: رصدخانهٔ مراغه در تپهٔ رصد داغی در شمال‌غرب شهر مراغه قرار دارد و در سدهٔ هفتم هجری به فرمان هلاکوخان و با سرپرستی خواجه نصیرالدین طوسی ساخته شد. این مجموعه از مراکز مهم رصد و پژوهش نجومی در جهان اسلام در سدهٔ میانه بود.
نقطه مرجع جغرافیایی: عرض 37.396111, طول 46.209167
معنای مختصات: representative_point؛ این مختصات ورودی بازدیدکنندگان نیست.
یادداشت شواهد: مرجع نهادی میراث نجومی تاریخ و مختصات منتشرشده را پشتیبانی می‌کند؛ دالاهو برای معرفی گردشگری و Mapcarta/OSM برای کنترل مستقل مکانی استفاده شده است.', '08fe0d7ada30bccf304fa45ba01f874e884a00d44997d57fc93028120d5def28', 691, 'existing_destination_enrichment', 'representative_point');

INSERT INTO knowledge.knowledge_documents
    (document_key, source_id, destination_id, title, language_code, document_type,
     canonical_url, raw_content, content_sha256, ingestion_status, record_origin,
     is_synthetic, retrieved_at)
SELECT x.document_key, s.source_id, d.destination_id, x.title, 'fa', 'destination_profile',
       x.canonical_url, x.raw_content, x.content_sha256, 'processed',
       'verified_external', FALSE, NOW()
FROM _shiraz_docs x
JOIN knowledge.destinations d
  ON d.destination_key=x.destination_key
  OR (d.canonical_name=x.canonical_name AND d.province_name=x.province_name
      AND COALESCE(d.city_name,'')=COALESCE(x.city_name,''))
JOIN _shiraz_sources src ON src.source_key=x.source_key
JOIN knowledge.knowledge_sources s ON s.source_name=src.source_name
WHERE d.status='needs_review'
  AND d.is_synthetic=FALSE
  AND d.record_origin='verified_external'
ON CONFLICT (document_key) DO UPDATE SET
    source_id=EXCLUDED.source_id,
    destination_id=EXCLUDED.destination_id,
    title=EXCLUDED.title,
    language_code=EXCLUDED.language_code,
    document_type=EXCLUDED.document_type,
    canonical_url=EXCLUDED.canonical_url,
    raw_content=EXCLUDED.raw_content,
    content_sha256=EXCLUDED.content_sha256,
    ingestion_status='processed',
    record_origin='verified_external',
    is_synthetic=FALSE,
    retrieved_at=NOW()
WHERE knowledge.knowledge_documents.is_synthetic=FALSE
  AND knowledge.knowledge_documents.record_origin IN ('user_supplied_unverified','verified_external');

INSERT INTO knowledge.knowledge_chunks
    (document_id, chunk_index, content, char_count, token_count,
     content_sha256, metadata, is_synthetic)
SELECT d.document_id, 0, x.raw_content, x.char_count, NULL, x.content_sha256,
       jsonb_build_object(
           'destination_key', x.destination_key,
           'scope', x.scope,
           'coordinate_role', x.coordinate_role,
           'data_class', 'verified_external',
           'chunking', 'single_compact_profile_v1'
       ),
       FALSE
FROM _shiraz_docs x
JOIN knowledge.knowledge_documents d ON d.document_key=x.document_key
WHERE d.is_synthetic=FALSE
  AND d.record_origin='verified_external'
ON CONFLICT (document_id, chunk_index) DO UPDATE SET
    content=EXCLUDED.content,
    char_count=EXCLUDED.char_count,
    token_count=EXCLUDED.token_count,
    content_sha256=EXCLUDED.content_sha256,
    metadata=EXCLUDED.metadata,
    is_synthetic=FALSE
WHERE knowledge.knowledge_chunks.is_synthetic=FALSE;


-- 9) Fail safely if the destination import did not resolve every curated row,
-- the city hierarchy was not established, or any imported row was misclassified.
DO $$
DECLARE
    expected_count INTEGER;
    resolved_count INTEGER;
    city_id BIGINT;
BEGIN
    SELECT COUNT(*) INTO expected_count FROM _shiraz_entities;
    SELECT COUNT(DISTINCT d.destination_key) INTO resolved_count
      FROM _shiraz_entities e
      JOIN knowledge.destinations d
        ON d.destination_key=e.destination_key
        OR (d.canonical_name=e.canonical_name AND d.province_name=e.province_name
            AND COALESCE(d.city_name,'')=COALESCE(e.city_name,''))
     WHERE d.status='needs_review'
       AND d.is_synthetic=FALSE
       AND d.record_origin='verified_external';
    IF resolved_count <> expected_count THEN
        RAISE EXCEPTION 'Expected % source-backed entities to resolve, got %; transaction rolled back.',
            expected_count, resolved_count;
    END IF;

    SELECT destination_id INTO city_id
      FROM knowledge.destinations
     WHERE destination_key='shiraz-city-v1'
        OR (canonical_name='شیراز' AND province_name='فارس' AND city_name='شیراز')
     ORDER BY destination_id
     LIMIT 1;
    IF city_id IS NULL THEN
        RAISE EXCEPTION 'Shiraz city parent row is missing.';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM _shiraz_entities e
          JOIN knowledge.destinations d
            ON d.destination_key=e.destination_key
            OR (d.canonical_name=e.canonical_name AND d.province_name=e.province_name
                AND COALESCE(d.city_name,'')=COALESCE(e.city_name,''))
         WHERE e.parent_key='shiraz-city-v1'
           AND d.parent_destination_id IS DISTINCT FROM city_id
    ) THEN
        RAISE EXCEPTION 'One or more Shiraz child entities are not linked to the Shiraz city parent.';
    END IF;

    IF EXISTS (
        SELECT 1 FROM knowledge.destinations d
        WHERE d.destination_key LIKE 'shiraz-%-v1'
          AND (d.is_synthetic OR d.record_origin <> 'verified_external'
               OR d.status <> 'needs_review' OR d.verification_status <> 'verified')
    ) THEN
        RAISE EXCEPTION 'A Shiraz import entity has invalid real/synthetic or publication markers.';
    END IF;

    IF (SELECT COUNT(*) FROM _shiraz_docs x
        JOIN knowledge.knowledge_documents d ON d.document_key=x.document_key
        WHERE d.is_synthetic=FALSE AND d.record_origin='verified_external'
          AND d.ingestion_status='processed') <> 23 THEN
        RAISE EXCEPTION 'Expected 23 non-synthetic processed knowledge documents.';
    END IF;

    IF (SELECT COUNT(*) FROM _shiraz_docs x
        JOIN knowledge.knowledge_documents d ON d.document_key=x.document_key
        JOIN knowledge.knowledge_chunks c ON c.document_id=d.document_id AND c.chunk_index=0
        WHERE c.is_synthetic=FALSE
          AND c.content_sha256=encode(sha256(convert_to(c.content,'UTF8')),'hex')
          AND c.char_count=CHAR_LENGTH(c.content)) <> 23 THEN
        RAISE EXCEPTION 'Expected 23 non-synthetic chunks with matching hashes and character counts.';
    END IF;
END $$;

INSERT INTO operations.dataset_import_batches
    (batch_key, data_class, source_id, record_counts, source_checksum, notes)
SELECT
    'shiraz-dalahoo-wikipedia-v1',
    'verified_external',
    s.source_id,
    '{"catalogue_entities":22,"existing_maragheh_rows_enriched":1,"knowledge_documents":23,"knowledge_chunks":23,"sources_in_package":18,"dalahoo_index_discovery_links_requested":13,"existing_unesco_nearby_links_requested":2}'::JSONB,
    '16c42d6b34c012379712404b9699d15b971393f78980098c0be8520bcfa23e62',
    'Source-backed Shiraz pilot candidate import. All catalogue entities are non-synthetic and remain needs_review. Dalahoo discovery links on legacy rows do not verify those rows. Wikipedia coordinates are representative points, not visitor entrances. Companion JSON: shiraz_dalahoo_wikipedia_real_data_v1.json.'
FROM knowledge.knowledge_sources s
WHERE s.source_name='Dalahoo domestic destination index'
ON CONFLICT (batch_key) DO UPDATE SET
    data_class=EXCLUDED.data_class,
    source_id=EXCLUDED.source_id,
    record_counts=EXCLUDED.record_counts,
    source_checksum=EXCLUDED.source_checksum,
    notes=EXCLUDED.notes,
    imported_at=NOW();

COMMIT;

-- Post-import verification queries (read-only):
-- SELECT record_origin, is_synthetic, status, verification_status, COUNT(*)
-- FROM knowledge.destinations GROUP BY 1,2,3,4 ORDER BY 1,2,3,4;
-- SELECT d.canonical_name, d.destination_type, d.city_name, d.latitude, d.longitude,
--        d.coordinate_role, d.status, d.record_origin, d.is_synthetic
-- FROM knowledge.destinations d
-- WHERE d.destination_key LIKE 'shiraz-%-v1' OR d.destination_key='maragheh-observatory-v1'
-- ORDER BY d.destination_type, d.canonical_name;
-- SELECT d.canonical_name, s.source_name, ds.source_role, ds.evidence_note
-- FROM knowledge.destination_sources ds
-- JOIN knowledge.destinations d USING(destination_id)
-- JOIN knowledge.knowledge_sources s USING(source_id)
-- WHERE d.destination_key LIKE 'shiraz-%-v1'
-- ORDER BY d.canonical_name, s.source_name;
-- SELECT * FROM knowledge.production_destinations WHERE destination_key LIKE 'shiraz-%-v1';
-- Expected production rows from this import: ZERO until explicit editorial approval.
