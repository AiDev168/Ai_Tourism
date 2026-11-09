\set ON_ERROR_STOP on
BEGIN;

-- Second curated batch: seven additional single-point UNESCO World Heritage properties in Iran.
-- Persian summaries are original paraphrases. No opening hours, prices, route times, access or safety facts are inferred.
-- All map coordinates are official UNESCO property/reference points, not visitor entrances.
-- Every destination remains needs_review; verification of source and coordinates does not constitute editorial publication.
-- UNESCO descriptive content carries CC-BY-SA IGO 3.0 notice; commercial reuse/attribution obligations need review.

INSERT INTO knowledge.knowledge_sources
    (source_name, source_type, verification_status, reliability_score, url, notes, is_synthetic)
VALUES
    ('UNESCO WHC 1077: Takht-e Soleyman — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1077/', 'Official UNESCO World Heritage Centre property description. Persian text is an original concise paraphrase, not verbatim. The page displays CC-BY-SA IGO 3.0; attribution/share-alike obligations require review before commercial republication.', FALSE),
    ('UNESCO WHC 1077: Takht-e Soleyman — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1077/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point or complete property polygon.', FALSE),
    ('UNESCO WHC 113: Tchogha Zanbil — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/113/', 'Official UNESCO World Heritage Centre property description. Persian text is an original concise paraphrase, not verbatim. The page displays CC-BY-SA IGO 3.0; attribution/share-alike obligations require review before commercial republication.', FALSE),
    ('UNESCO WHC 113: Tchogha Zanbil — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/113/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point or complete property polygon.', FALSE),
    ('UNESCO WHC 1345: Sheikh Safi al-din Khānegāh and Shrine Ensemble in Ardabil — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1345/', 'Official UNESCO World Heritage Centre property description. Persian text is an original concise paraphrase, not verbatim. The page displays CC-BY-SA IGO 3.0; attribution/share-alike obligations require review before commercial republication.', FALSE),
    ('UNESCO WHC 1345: Sheikh Safi al-din Khānegāh and Shrine Ensemble in Ardabil — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1345/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point or complete property polygon.', FALSE),
    ('UNESCO WHC 1397: Masjed-e Jāmé of Isfahan — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1397/', 'Official UNESCO World Heritage Centre property description. Persian text is an original concise paraphrase, not verbatim. The page displays CC-BY-SA IGO 3.0; attribution/share-alike obligations require review before commercial republication.', FALSE),
    ('UNESCO WHC 1397: Masjed-e Jāmé of Isfahan — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1397/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point or complete property polygon.', FALSE),
    ('UNESCO WHC 1456: Shahr-i Sokhta — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1456/', 'Official UNESCO World Heritage Centre property description. Persian text is an original concise paraphrase, not verbatim. The page displays CC-BY-SA IGO 3.0; attribution/share-alike obligations require review before commercial republication.', FALSE),
    ('UNESCO WHC 1456: Shahr-i Sokhta — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1456/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point or complete property polygon.', FALSE),
    ('UNESCO WHC 1423: Cultural Landscape of Maymand — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1423/', 'Official UNESCO World Heritage Centre property description. Persian text is an original concise paraphrase, not verbatim. The page displays CC-BY-SA IGO 3.0; attribution/share-alike obligations require review before commercial republication.', FALSE),
    ('UNESCO WHC 1423: Cultural Landscape of Maymand — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1423/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point or complete property polygon.', FALSE),
    ('UNESCO WHC 1716: Hegmataneh — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1716/', 'Official UNESCO World Heritage Centre property description. Persian text is an original concise paraphrase, not verbatim. The page displays CC-BY-SA IGO 3.0; attribution/share-alike obligations require review before commercial republication.', FALSE),
    ('UNESCO WHC 1716: Hegmataneh — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1716/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point or complete property polygon.', FALSE),
    ('UNESCO WHC Nomination 1456: Shahr-i Sokhta — administrative location', 'unesco_nomination_geography', 'verified', NULL, 'https://whc.unesco.org/uploads/nominations/1456.pdf', 'Official State Party nomination file hosted by UNESCO identifies Shahr-i Sokhta as 56 km from Zabol in Sistan-o Baluchestan Province; used for administrative context only.', FALSE),
    ('UNESCO ICOMOS Evaluation 1423rev: Maymand — administrative location', 'unesco_advisory_evaluation', 'verified', NULL, 'https://whc.unesco.org/archive/2015/whc15-39com-inf8B1-Add-en.pdf', 'Official ICOMOS evaluation hosted by UNESCO identifies Kerman Province and Shahr-e Babak Township; used for administrative context only.', FALSE)
ON CONFLICT (source_name) DO UPDATE SET
    source_type=EXCLUDED.source_type,
    verification_status='verified',
    reliability_score=NULL,
    url=EXCLUDED.url,
    notes=EXCLUDED.notes,
    is_synthetic=FALSE,
    updated_at=NOW();

INSERT INTO knowledge.destinations (
    destination_key, canonical_name, destination_type, province_name, city_name,
    description, aliases, latitude, longitude, coordinate_role, status, data_confidence,
    record_origin, verification_status, is_synthetic, country_code
)
VALUES
    ('unesco-takht-e-soleyman-v2', 'تخت سلیمان', 'archaeological_site', 'آذربایجان غربی', NULL, 'تخت سلیمان محوطه‌ای باستانی در استان آذربایجان غربی است که در یک دره و چشم‌انداز کوهستانی آتشفشانی قرار دارد. این مجموعه بقایای نیایشگاه اصلی زرتشتی و سازه‌های وابسته به معماری سلطنتی ساسانی را در بر می‌گیرد. بخشی از بناها در دوره ایلخانی، در سده سیزدهم میلادی، بازسازی شده‌اند. در مرکز محوطه دریاچه‌ای آرتزین، آتشکده و نیایشگاه آناهیتا قرار دارند.', ARRAY['Takht-e Soleyman', 'Throne of Solomon', 'تخت سلیمان']::TEXT[], 36.6038889, 47.235, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-tchogha-zanbil-v2', 'چغازنبیل', 'elamite_archaeological_site', 'خوزستان', NULL, 'چغازنبیل در استان خوزستان، بقایای شهر مقدس پادشاهی ایلام است که حدود ۱۲۵۰ پیش از میلاد بنیان گذاشته شد. محوطه باستانی با سه حصار متحدالمرکز شناخته می‌شود و زیگورات آن عنصر اصلی مجموعه است. این اثر از مهم‌ترین شواهد معماری و سنت‌های آیینی ایلام میانه به شمار می‌رود.', ARRAY['Tchogha Zanbil', 'Chogha Zanbil', 'Dur-Untash', 'چغازنبیل', 'زیگورات چغازنبیل']::TEXT[], 32.00857, 48.5221181, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-sheikh-safi-ardabil-v2', 'مجموعه شیخ صفی‌الدین اردبیلی', 'sufi_shrine_ensemble', 'اردبیل', 'اردبیل', 'مجموعه خانقاه و آرامگاه شیخ صفی‌الدین در اردبیل، فضایی آیینی در سنت تصوف است که بخش‌هایی از آن از آغاز سده شانزدهم تا پایان سده هجدهم ساخته شده‌اند. این مجموعه با بهره‌گیری از الگوهای معماری سنتی ایران، کارکردهایی چون کتابخانه، مسجد، مدرسه، آرامگاه، آب‌انبار، بیمارستان، آشپزخانه و فضاهای خدماتی را در کنار هم جای داده است.', ARRAY['Sheikh Safi al-din Shrine', 'Sheikh Safi al-din Khānegāh', 'مجموعه شیخ صفی', 'مجموعه شیخ صفی‌الدین اردبیلی']::TEXT[], 38.2486111, 48.2913889, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-masjed-jame-isfahan-v2', 'مسجد جامع اصفهان', 'historic_mosque', 'اصفهان', 'اصفهان', 'مسجد جامع اصفهان در مرکز تاریخی شهر قرار دارد و نمونه‌ای برجسته از تحول معماری مسجد در ایران طی حدود دوازده قرن، از سال ۸۴۱ میلادی به بعد، است. این مجموعه لایه‌های معماری دوره‌های مختلف را در خود حفظ کرده و الگوی چهارایوانی حیاط آن در تاریخ معماری اسلامی اهمیت دارد.', ARRAY['Masjed-e Jame of Isfahan', 'Friday Mosque of Isfahan', 'مسجد جامع اصفهان', 'مسجد جمعه اصفهان']::TEXT[], 32.6697222, 51.6852778, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-shahr-i-sokhta-v2', 'شهر سوخته', 'bronze_age_archaeological_city', 'سیستان و بلوچستان', NULL, 'شهر سوخته در استان سیستان و بلوچستان و در مسیر پیونددهنده راه‌های بازرگانی عصر مفرغ در فلات ایران قرار داشته است. این شهر حدود ۳۲۰۰ پیش از میلاد شکل گرفت و بقایای خشتی آن از پیدایش جوامع پیچیده در شرق ایران و سازمان فضایی سکونتگاه‌های آن دوره شواهد مهمی ارائه می‌کند.', ARRAY['Shahr-i Sokhta', 'Shahr-e Sukhteh', 'Burnt City', 'شهر سوخته']::TEXT[], 30.5938889, 61.3277778, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-maymand-v2', 'منظر فرهنگی میمند', 'cultural_landscape', 'کرمان', 'شهربابک', 'منظر فرهنگی میمند در استان کرمان و شهرستان شهربابک، در دره‌ای نیمه‌خشک در بخش جنوبی رشته‌کوه‌های مرکزی ایران قرار دارد. یونسکو این منظر را نمونه‌ای از شیوه معیشت کشاورزی و دامداری نیمه‌کوچ‌رو می‌داند که با جابه‌جایی فصلی میان سکونتگاه‌ها و استفاده از خانه‌های دست‌کند در سنگ نرم در زمستان پیوند دارد.', ARRAY['Cultural Landscape of Maymand', 'Maymand', 'میمند', 'منظر فرهنگی میمند']::TEXT[], 30.1680556, 55.3755556, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-hegmataneh-v2', 'هگمتانه', 'ancient_archaeological_city', 'همدان', 'همدان', 'هگمتانه در شهر همدان از محوطه‌های باستانی مهم فلات ایران است که در منابع تاریخی با نام‌هایی مانند اکباتان نیز شناخته می‌شود. یونسکو این محوطه را از جایگاه‌های مهم حکومتی در دوره مادها و دوره‌های هخامنشی، اشکانی، ساسانی و اسلامی معرفی می‌کند و بقایای شهرسازی و معماری آن شواهدی از تعامل فرهنگ‌های منطقه به دست می‌دهد.', ARRAY['Hegmataneh', 'Ecbatana', 'Egbatana', 'هگمتانه', 'اکباتان']::TEXT[], 34.8035556, 48.5183333, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR')
ON CONFLICT (destination_key) DO UPDATE SET
    canonical_name=EXCLUDED.canonical_name,
    destination_type=EXCLUDED.destination_type,
    province_name=EXCLUDED.province_name,
    city_name=EXCLUDED.city_name,
    description=EXCLUDED.description,
    aliases=EXCLUDED.aliases,
    latitude=EXCLUDED.latitude,
    longitude=EXCLUDED.longitude,
    coordinate_role='property_reference',
    status='needs_review',
    data_confidence=0,
    record_origin='verified_external',
    verification_status='verified',
    is_synthetic=FALSE,
    country_code='IR',
    updated_at=NOW();

INSERT INTO knowledge.destination_sources
    (destination_id, source_id, source_role, evidence_note, retrieved_at)
SELECT d.destination_id, s.source_id, x.source_role, x.evidence_note, NOW()
FROM (VALUES
    ('unesco-takht-e-soleyman-v2', 'UNESCO WHC 1077: Takht-e Soleyman — description', 'primary', 'Official UNESCO property description; Persian text is an original paraphrase.'),
    ('unesco-tchogha-zanbil-v2', 'UNESCO WHC 113: Tchogha Zanbil — description', 'primary', 'Official UNESCO property description; Persian text is an original paraphrase.'),
    ('unesco-sheikh-safi-ardabil-v2', 'UNESCO WHC 1345: Sheikh Safi al-din Khānegāh and Shrine Ensemble in Ardabil — description', 'primary', 'Official UNESCO property description; Persian text is an original paraphrase.'),
    ('unesco-masjed-jame-isfahan-v2', 'UNESCO WHC 1397: Masjed-e Jāmé of Isfahan — description', 'primary', 'Official UNESCO property description; Persian text is an original paraphrase.'),
    ('unesco-shahr-i-sokhta-v2', 'UNESCO WHC 1456: Shahr-i Sokhta — description', 'primary', 'Official UNESCO property description; Persian text is an original paraphrase.'),
    ('unesco-maymand-v2', 'UNESCO WHC 1423: Cultural Landscape of Maymand — description', 'primary', 'Official UNESCO property description; Persian text is an original paraphrase.'),
    ('unesco-hegmataneh-v2', 'UNESCO WHC 1716: Hegmataneh — description', 'primary', 'Official UNESCO property description; Persian text is an original paraphrase.'),
    ('unesco-takht-e-soleyman-v2', 'UNESCO WHC 1077: Takht-e Soleyman — mapped property point', 'verification', 'Official UNESCO geographical data; coordinate is a property/reference point, not a visitor entrance.'),
    ('unesco-tchogha-zanbil-v2', 'UNESCO WHC 113: Tchogha Zanbil — mapped property point', 'verification', 'Official UNESCO geographical data; coordinate is a property/reference point, not a visitor entrance.'),
    ('unesco-sheikh-safi-ardabil-v2', 'UNESCO WHC 1345: Sheikh Safi al-din Khānegāh and Shrine Ensemble in Ardabil — mapped property point', 'verification', 'Official UNESCO geographical data; coordinate is a property/reference point, not a visitor entrance.'),
    ('unesco-masjed-jame-isfahan-v2', 'UNESCO WHC 1397: Masjed-e Jāmé of Isfahan — mapped property point', 'verification', 'Official UNESCO geographical data; coordinate is a property/reference point, not a visitor entrance.'),
    ('unesco-shahr-i-sokhta-v2', 'UNESCO WHC 1456: Shahr-i Sokhta — mapped property point', 'verification', 'Official UNESCO geographical data; coordinate is a property/reference point, not a visitor entrance.'),
    ('unesco-maymand-v2', 'UNESCO WHC 1423: Cultural Landscape of Maymand — mapped property point', 'verification', 'Official UNESCO geographical data; coordinate is a property/reference point, not a visitor entrance.'),
    ('unesco-hegmataneh-v2', 'UNESCO WHC 1716: Hegmataneh — mapped property point', 'verification', 'Official UNESCO geographical data; coordinate is a property/reference point, not a visitor entrance.'),
    ('unesco-shahr-i-sokhta-v2', 'UNESCO WHC Nomination 1456: Shahr-i Sokhta — administrative location', 'verification', 'Official nomination file confirms the province and nearby Zabol administrative context.'),
    ('unesco-maymand-v2', 'UNESCO ICOMOS Evaluation 1423rev: Maymand — administrative location', 'verification', 'Official ICOMOS evaluation confirms Kerman Province and Shahr-e Babak Township.')
) AS x(destination_key, source_name, source_role, evidence_note)
JOIN knowledge.destinations d ON d.destination_key=x.destination_key
JOIN knowledge.knowledge_sources s ON s.source_name=x.source_name
ON CONFLICT (destination_id, source_id) DO UPDATE SET
    source_role=EXCLUDED.source_role,
    evidence_note=EXCLUDED.evidence_note,
    retrieved_at=NOW();

INSERT INTO knowledge.destination_category_map
    (destination_id, category_id, mapping_source, is_synthetic)
SELECT d.destination_id, c.category_id, 'verified_external_curated', FALSE
FROM (VALUES
    ('unesco-takht-e-soleyman-v2', 'historical'),
    ('unesco-tchogha-zanbil-v2', 'historical'),
    ('unesco-sheikh-safi-ardabil-v2', 'historical'),
    ('unesco-masjed-jame-isfahan-v2', 'historical'),
    ('unesco-shahr-i-sokhta-v2', 'historical'),
    ('unesco-maymand-v2', 'historical'),
    ('unesco-hegmataneh-v2', 'historical')
) AS x(destination_key, category_key)
JOIN knowledge.destinations d ON d.destination_key=x.destination_key
JOIN knowledge.destination_categories c ON c.category_key=x.category_key
ON CONFLICT (destination_id, category_id) DO UPDATE SET
    mapping_source=EXCLUDED.mapping_source,
    is_synthetic=FALSE;

INSERT INTO knowledge.destination_tags (destination_id, tag)
SELECT d.destination_id, x.tag
FROM (VALUES
    ('unesco-takht-e-soleyman-v2', 'unesco_world_heritage'),
    ('unesco-takht-e-soleyman-v2', 'province:آذربایجان غربی'),
    ('unesco-takht-e-soleyman-v2', 'unesco_dossier:1077'),
    ('unesco-tchogha-zanbil-v2', 'unesco_world_heritage'),
    ('unesco-tchogha-zanbil-v2', 'province:خوزستان'),
    ('unesco-tchogha-zanbil-v2', 'unesco_dossier:113'),
    ('unesco-sheikh-safi-ardabil-v2', 'unesco_world_heritage'),
    ('unesco-sheikh-safi-ardabil-v2', 'province:اردبیل'),
    ('unesco-sheikh-safi-ardabil-v2', 'unesco_dossier:1345'),
    ('unesco-masjed-jame-isfahan-v2', 'unesco_world_heritage'),
    ('unesco-masjed-jame-isfahan-v2', 'province:اصفهان'),
    ('unesco-masjed-jame-isfahan-v2', 'unesco_dossier:1397'),
    ('unesco-shahr-i-sokhta-v2', 'unesco_world_heritage'),
    ('unesco-shahr-i-sokhta-v2', 'province:سیستان و بلوچستان'),
    ('unesco-shahr-i-sokhta-v2', 'unesco_dossier:1456'),
    ('unesco-maymand-v2', 'unesco_world_heritage'),
    ('unesco-maymand-v2', 'province:کرمان'),
    ('unesco-maymand-v2', 'unesco_dossier:1423'),
    ('unesco-hegmataneh-v2', 'unesco_world_heritage'),
    ('unesco-hegmataneh-v2', 'province:همدان'),
    ('unesco-hegmataneh-v2', 'unesco_dossier:1716')
) AS x(destination_key, tag)
JOIN knowledge.destinations d ON d.destination_key=x.destination_key
ON CONFLICT (destination_id, tag) DO NOTHING;

INSERT INTO knowledge.knowledge_documents (
    document_key, source_id, destination_id, title, language_code, document_type,
    canonical_url, raw_content, content_sha256, ingestion_status, record_origin,
    is_synthetic, retrieved_at
)
SELECT x.document_key, s.source_id, d.destination_id, x.title, 'fa', 'destination_profile',
       x.canonical_url, x.raw_content, x.content_sha256, 'processed', 'verified_external',
       FALSE, NOW()
FROM (VALUES
    ('unesco-takht-e-soleyman-v2-doc', 'پرونده دانش میراث جهانی: تخت سلیمان', 'https://whc.unesco.org/en/list/1077/', 'تخت سلیمان محوطه‌ای باستانی در استان آذربایجان غربی است که در یک دره و چشم‌انداز کوهستانی آتشفشانی قرار دارد. این مجموعه بقایای نیایشگاه اصلی زرتشتی و سازه‌های وابسته به معماری سلطنتی ساسانی را در بر می‌گیرد. بخشی از بناها در دوره ایلخانی، در سده سیزدهم میلادی، بازسازی شده‌اند. در مرکز محوطه دریاچه‌ای آرتزین، آتشکده و نیایشگاه آناهیتا قرار دارند.', '1fa3caad0de21233a7df98270826382ef45cec9712047d22e617318c3dc20800'),
    ('unesco-tchogha-zanbil-v2-doc', 'پرونده دانش میراث جهانی: چغازنبیل', 'https://whc.unesco.org/en/list/113/', 'چغازنبیل در استان خوزستان، بقایای شهر مقدس پادشاهی ایلام است که حدود ۱۲۵۰ پیش از میلاد بنیان گذاشته شد. محوطه باستانی با سه حصار متحدالمرکز شناخته می‌شود و زیگورات آن عنصر اصلی مجموعه است. این اثر از مهم‌ترین شواهد معماری و سنت‌های آیینی ایلام میانه به شمار می‌رود.', '7aa1a645d01ded5ba5934128c264f448486a66a3a53389ab78602a496f822d0e'),
    ('unesco-sheikh-safi-ardabil-v2-doc', 'پرونده دانش میراث جهانی: مجموعه شیخ صفی‌الدین اردبیلی', 'https://whc.unesco.org/en/list/1345/', 'مجموعه خانقاه و آرامگاه شیخ صفی‌الدین در اردبیل، فضایی آیینی در سنت تصوف است که بخش‌هایی از آن از آغاز سده شانزدهم تا پایان سده هجدهم ساخته شده‌اند. این مجموعه با بهره‌گیری از الگوهای معماری سنتی ایران، کارکردهایی چون کتابخانه، مسجد، مدرسه، آرامگاه، آب‌انبار، بیمارستان، آشپزخانه و فضاهای خدماتی را در کنار هم جای داده است.', 'c592f0e1c9197aee89936d493f03476b17348734c46cd491dc8d835acc0ee9d3'),
    ('unesco-masjed-jame-isfahan-v2-doc', 'پرونده دانش میراث جهانی: مسجد جامع اصفهان', 'https://whc.unesco.org/en/list/1397/', 'مسجد جامع اصفهان در مرکز تاریخی شهر قرار دارد و نمونه‌ای برجسته از تحول معماری مسجد در ایران طی حدود دوازده قرن، از سال ۸۴۱ میلادی به بعد، است. این مجموعه لایه‌های معماری دوره‌های مختلف را در خود حفظ کرده و الگوی چهارایوانی حیاط آن در تاریخ معماری اسلامی اهمیت دارد.', '799c59552ccd107da1154d78a4fec29095a6e39e7955f1108c046ea056522301'),
    ('unesco-shahr-i-sokhta-v2-doc', 'پرونده دانش میراث جهانی: شهر سوخته', 'https://whc.unesco.org/en/list/1456/', 'شهر سوخته در استان سیستان و بلوچستان و در مسیر پیونددهنده راه‌های بازرگانی عصر مفرغ در فلات ایران قرار داشته است. این شهر حدود ۳۲۰۰ پیش از میلاد شکل گرفت و بقایای خشتی آن از پیدایش جوامع پیچیده در شرق ایران و سازمان فضایی سکونتگاه‌های آن دوره شواهد مهمی ارائه می‌کند.', 'f01406862642019aea46549ecf5b1d40554b4627c307adde5e7231ecfa03b9e0'),
    ('unesco-maymand-v2-doc', 'پرونده دانش میراث جهانی: منظر فرهنگی میمند', 'https://whc.unesco.org/en/list/1423/', 'منظر فرهنگی میمند در استان کرمان و شهرستان شهربابک، در دره‌ای نیمه‌خشک در بخش جنوبی رشته‌کوه‌های مرکزی ایران قرار دارد. یونسکو این منظر را نمونه‌ای از شیوه معیشت کشاورزی و دامداری نیمه‌کوچ‌رو می‌داند که با جابه‌جایی فصلی میان سکونتگاه‌ها و استفاده از خانه‌های دست‌کند در سنگ نرم در زمستان پیوند دارد.', '12274ab7e332db4ce49838d3b2de7d316df42d71d4f6377a677aff134af33e39'),
    ('unesco-hegmataneh-v2-doc', 'پرونده دانش میراث جهانی: هگمتانه', 'https://whc.unesco.org/en/list/1716/', 'هگمتانه در شهر همدان از محوطه‌های باستانی مهم فلات ایران است که در منابع تاریخی با نام‌هایی مانند اکباتان نیز شناخته می‌شود. یونسکو این محوطه را از جایگاه‌های مهم حکومتی در دوره مادها و دوره‌های هخامنشی، اشکانی، ساسانی و اسلامی معرفی می‌کند و بقایای شهرسازی و معماری آن شواهدی از تعامل فرهنگ‌های منطقه به دست می‌دهد.', '32c0b0a52ce424070e94406e19a46c34de1f1a468d5d6bfd3c4b948c18e4ba85')
) AS x(document_key, title, canonical_url, raw_content, content_sha256)
JOIN knowledge.knowledge_sources s
  ON s.source_name = CASE x.document_key
    WHEN 'unesco-takht-e-soleyman-v2-doc' THEN 'UNESCO WHC 1077: Takht-e Soleyman — description'
    WHEN 'unesco-tchogha-zanbil-v2-doc' THEN 'UNESCO WHC 113: Tchogha Zanbil — description'
    WHEN 'unesco-sheikh-safi-ardabil-v2-doc' THEN 'UNESCO WHC 1345: Sheikh Safi al-din Khānegāh and Shrine Ensemble in Ardabil — description'
    WHEN 'unesco-masjed-jame-isfahan-v2-doc' THEN 'UNESCO WHC 1397: Masjed-e Jāmé of Isfahan — description'
    WHEN 'unesco-shahr-i-sokhta-v2-doc' THEN 'UNESCO WHC 1456: Shahr-i Sokhta — description'
    WHEN 'unesco-maymand-v2-doc' THEN 'UNESCO WHC 1423: Cultural Landscape of Maymand — description'
    WHEN 'unesco-hegmataneh-v2-doc' THEN 'UNESCO WHC 1716: Hegmataneh — description'
  END
JOIN knowledge.destinations d
  ON d.destination_key = REPLACE(x.document_key, '-doc', '')
ON CONFLICT (document_key) DO UPDATE SET
    source_id=EXCLUDED.source_id,
    destination_id=EXCLUDED.destination_id,
    title=EXCLUDED.title,
    canonical_url=EXCLUDED.canonical_url,
    raw_content=EXCLUDED.raw_content,
    content_sha256=EXCLUDED.content_sha256,
    ingestion_status='processed',
    record_origin='verified_external',
    is_synthetic=FALSE,
    retrieved_at=NOW(),
    updated_at=NOW();

INSERT INTO knowledge.knowledge_chunks
    (document_id, chunk_index, content, char_count, content_sha256, metadata, is_synthetic)
SELECT d.document_id, x.chunk_index, x.content, CHAR_LENGTH(x.content), x.content_sha256,
       jsonb_build_object(
           'dataset_key', 'unesco-iran-second-batch-v2',
           'destination_key', x.destination_key,
           'chunk_role', x.chunk_role,
           'source_license_notice', 'CC-BY-SA IGO 3.0; original Persian paraphrase'
       ),
       FALSE
FROM (VALUES
    ('unesco-takht-e-soleyman-v2', 0, 'تخت سلیمان در استان آذربایجان غربی و در یک دره کوهستانی با منشأ آتشفشانی قرار دارد. یونسکو این مجموعه را شامل نیایشگاه زرتشتی، عناصر معماری سلطنتی ساسانی و بناهایی می‌داند که بخشی از آن‌ها در دوره ایلخانی بازسازی شده‌اند.', 'f5b00cdddb7c30f275968f550b85c4aaa97e2b5351c0cdb9abef9d1d78a88e65', 'overview'),
    ('unesco-takht-e-soleyman-v2', 1, 'در مرکز محوطه تخت سلیمان دریاچه‌ای آرتزین، آتشکده زرتشتی و نیایشگاه آناهیتا قرار دارند. نقطه ثبت‌شده در نقشه یونسکو نقطه مرجع ملک میراثی است؛ این داده به‌تنهایی ورودی بازدید، مسیر، ساعت کار یا وضعیت کنونی دسترسی را مشخص نمی‌کند.', '612d1d40fa768f1720bef141059da059c84d9e48000b554e98765789195214e4', 'context_and_limitations'),
    ('unesco-tchogha-zanbil-v2', 0, 'چغازنبیل یا دوراونتاش، شهر مقدس پادشاهی ایلام، حدود ۱۲۵۰ پیش از میلاد بنیان گذاشته شد. یونسکو محوطه را دربرگیرنده سه حصار متحدالمرکز و مجموعه‌ای از فضاهای مذهبی و وابسته به شهر توصیف می‌کند.', '2e12cd1ddbc9808088539d9649f7839fe99db9b1349124ece554245119b41d93', 'overview'),
    ('unesco-tchogha-zanbil-v2', 1, 'زیگورات چغازنبیل عنصر مرکزی محوطه و نمونه‌ای برجسته از معماری ایلامی است. مختصات این رکورد از جدول جغرافیایی یونسکو و به‌عنوان نقطه مرجع ملک میراثی ثبت شده است؛ نه به‌عنوان در ورودی یا نقطه قطعی مسیریابی بازدیدکننده.', 'fe6ce57b97160720dbb1801acf271952a6469ea34f4eb02ee35d961166387ac0', 'context_and_limitations'),
    ('unesco-sheikh-safi-ardabil-v2', 0, 'مجموعه شیخ صفی‌الدین اردبیلی در شهر اردبیل قرار دارد و از آغاز سده شانزدهم تا پایان سده هجدهم میلادی توسعه یافته است. یونسکو آن را فضایی برای خلوت و آیین‌های صوفیانه با عناصر گوناگون مذهبی، آموزشی و خدماتی توصیف می‌کند.', 'a549ec63c2ee46bdf0e4bf1e084a75f118c551a0f47aa67e484fc2fdecf7eb84', 'overview'),
    ('unesco-sheikh-safi-ardabil-v2', 1, 'در توصیف یونسکو، مجموعه شامل کتابخانه، مسجد، مدرسه، آرامگاه‌ها، آب‌انبار، بیمارستان، آشپزخانه و فضاهای دیگر است. نقطه درج‌شده در نقشه، مرجع ملک ثبت‌شده است؛ برای ورودی، ساعات بازدید و جزئیات دسترسی باید داده مستقل و به‌روز تهیه شود.', '811ad4d9ddb6a2e8d743cc8604b1f2d3381bf8f8b95c02efd3e57ede39cc7600', 'context_and_limitations'),
    ('unesco-masjed-jame-isfahan-v2', 0, 'مسجد جامع اصفهان در مرکز تاریخی این شهر قرار دارد. یونسکو روند تحول معماری مسجد در ایران را در این بنا طی حدود دوازده قرن و از سال ۸۴۱ میلادی قابل مشاهده می‌داند.', '01ae172aa5c48d6138d25597d8275ba363af08cae647154bc8b352842062b9ad', 'overview'),
    ('unesco-masjed-jame-isfahan-v2', 1, 'حیاط چهارایوانی مسجد جامع اصفهان و گنبدهای دوپوسته آن از ویژگی‌های مهم معماری مجموعه‌اند. مختصات ثبت‌شده در نقشه یونسکو نقطه مرجع ملک میراثی است؛ ساعات بازدید، بلیت و ورودی‌های جاری در این رکورد ثبت نشده‌اند.', '339294da4ac9015c523703592c3367a02009fdc7f2124c3df723cbdcc52c1b7b', 'context_and_limitations'),
    ('unesco-shahr-i-sokhta-v2', 0, 'شهر سوخته در شرق فلات ایران و در پیوند با مسیرهای بازرگانی عصر مفرغ قرار داشت. بر اساس پرونده یونسکو، شکل‌گیری آن حدود ۳۲۰۰ پیش از میلاد آغاز شد و سکونت در آن تا حدود ۱۸۰۰ پیش از میلاد در چند دوره اصلی ادامه یافت.', '0fc4f324e0c0b13aefbdbb8a53ad4e14ef1f94a6fc031c0b989715217dc37f03', 'overview'),
    ('unesco-shahr-i-sokhta-v2', 1, 'بقایای شهر سوخته بخش‌هایی با کارکردهای متفاوت، از جمله محدوده‌های مسکونی، تدفینی، تولیدی و فضاهای مرتبط با بناهای شاخص را نشان می‌دهد. مختصات یونسکو نقطه مرجع ملک ثبت‌شده است و محل ورودی یا وضعیت کنونی بازدید را تعیین نمی‌کند.', 'a9a7f2871dde0c034feb3095fb42e58fb8c3d60c74bb1ab2cc2050458f74e782', 'context_and_limitations'),
    ('unesco-maymand-v2', 0, 'میمند در دره‌ای نیمه‌خشک در جنوب رشته‌کوه‌های مرکزی ایران و در استان کرمان قرار دارد. منظر فرهنگی آن شیوه معیشت نیمه‌کوچ‌رو مبتنی بر دامداری و کشاورزی را بازتاب می‌دهد که در آن خانوارها از چند محدوده سکونتی در فصل‌های مختلف استفاده می‌کردند.', '4e8807d2617f9a1b63b097c7d4e3a2e2ff4546a4a64a1ecb8a1f5ef71567bfc4', 'overview'),
    ('unesco-maymand-v2', 1, 'یکی از ویژگی‌های شاخص میمند، خانه‌های دست‌کند در سنگ نرم است که در دوره زمستان مورد استفاده قرار می‌گرفتند. این مختصات نقطه مرجع ملک میراثی در نقشه یونسکو است؛ داده فعلی درباره وضعیت سکونت، ظرفیت بازدید، مسیر یا شرایط روز منطقه ادعایی ندارد.', 'ce3c1d8e8e86f22a2332489900c08aef4c19257bda2b355077103c5662e12251', 'context_and_limitations'),
    ('unesco-hegmataneh-v2', 0, 'هگمتانه در شهر همدان قرار دارد و از محوطه‌های مهم باستانی ایران است. یونسکو آن را از مراکز حکومتی مهم در دوره مادها و دوره‌های بعدی، از جمله هخامنشی، اشکانی، ساسانی و اسلامی معرفی می‌کند.', '947d5b4ca8be3220e6f8989fd57d2afa4cda38881c1e66aae0172da3309abbc4', 'overview'),
    ('unesco-hegmataneh-v2', 1, 'بقایای معماری و شهرسازی هگمتانه شواهدی از دوره‌های مختلف و تعامل فرهنگ‌های خاورمیانه باستان را در بر دارد. مختصات این رکورد نقطه مرجع ثبت‌شده در نقشه یونسکو است و نباید بدون منبع جداگانه به‌عنوان ورودی بازدیدکنندگان یا مسیر دسترسی استفاده شود.', '34f3a7e43f77ac707ae84f5e5e95547e8826ecd0c444059b37e98e5536934240', 'context_and_limitations')
) AS x(destination_key, chunk_index, content, content_sha256, chunk_role)
JOIN knowledge.knowledge_documents d
  ON d.document_key = x.destination_key || '-doc'
ON CONFLICT (document_id, chunk_index) DO UPDATE SET
    content=EXCLUDED.content,
    char_count=EXCLUDED.char_count,
    content_sha256=EXCLUDED.content_sha256,
    metadata=EXCLUDED.metadata,
    is_synthetic=FALSE;

INSERT INTO operations.dataset_import_batches (batch_key, data_class, source_id, record_counts, notes)
VALUES (
    'verified-unesco-iran-sites-v2',
    'verified_external',
    NULL,
    '{"destinations":7,"sources":16,"destination_source_links":16,"category_mappings":7,"documents":7,"chunks":14}'::JSONB,
    'Second curated external batch: seven additional Iranian UNESCO World Heritage properties. Fourteen UNESCO-hosted description/map sources plus two official UNESCO-hosted administrative-location references. All rows are source-verified but remain needs_review and are not published. Coordinates are official property/reference points, not visitor entrances. Persian summaries are original paraphrases; CC-BY-SA IGO 3.0 attribution/share-alike obligations require review before commercial republication.'
)
ON CONFLICT (batch_key) DO UPDATE SET
    data_class=EXCLUDED.data_class,
    source_id=NULL,
    record_counts=EXCLUDED.record_counts,
    notes=EXCLUDED.notes;

INSERT INTO system.schema_migrations (migration_id, sha256)
VALUES ('0006_verified_unesco_destination_seed_batch2', :'migration_hash')
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;
