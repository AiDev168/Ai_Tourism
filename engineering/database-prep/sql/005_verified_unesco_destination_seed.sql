\set ON_ERROR_STOP on
BEGIN;

-- Curated first verified-external destination batch: 10 Iranian UNESCO World Heritage properties.
-- All descriptions below are original Persian paraphrases; no hours, admission prices, seasonality,
-- access routes or visitor entrances are inferred. Coordinates are UNESCO property/reference points.
-- These rows are source-verified but intentionally remain status='needs_review' until product-owner review.
-- UNESCO descriptive pages display CC-BY-SA IGO 3.0; attribution/license obligations must be reviewed before commercial republication.

INSERT INTO knowledge.knowledge_sources (source_name, source_type, verification_status, reliability_score, url, notes, is_synthetic)
VALUES
    ('UNESCO WHC 114: Persepolis — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/114/', 'Official UNESCO World Heritage Centre property description. Persian text in this dataset is an original concise paraphrase, not a verbatim reproduction. The page displays a CC-BY-SA IGO 3.0 license notice.', FALSE),
    ('UNESCO WHC 114: Persepolis — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/114/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point, or complete property polygon.', FALSE),
    ('UNESCO WHC 1422: Golestan Palace — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1422/', 'Official UNESCO World Heritage Centre property description. Persian text in this dataset is an original concise paraphrase, not a verbatim reproduction. The page displays a CC-BY-SA IGO 3.0 license notice.', FALSE),
    ('UNESCO WHC 1422: Golestan Palace — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1422/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point, or complete property polygon.', FALSE),
    ('UNESCO WHC 115: Meidan Emam, Esfahan — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/115/', 'Official UNESCO World Heritage Centre property description. Persian text in this dataset is an original concise paraphrase, not a verbatim reproduction. The page displays a CC-BY-SA IGO 3.0 license notice.', FALSE),
    ('UNESCO WHC 115: Meidan Emam, Esfahan — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/115/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point, or complete property polygon.', FALSE),
    ('UNESCO WHC 1346: Tabriz Historic Bazaar Complex — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1346/', 'Official UNESCO World Heritage Centre property description. Persian text in this dataset is an original concise paraphrase, not a verbatim reproduction. The page displays a CC-BY-SA IGO 3.0 license notice.', FALSE),
    ('UNESCO WHC 1346: Tabriz Historic Bazaar Complex — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1346/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point, or complete property polygon.', FALSE),
    ('UNESCO WHC 1315: Shushtar Historical Hydraulic System — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1315/', 'Official UNESCO World Heritage Centre property description. Persian text in this dataset is an original concise paraphrase, not a verbatim reproduction. The page displays a CC-BY-SA IGO 3.0 license notice.', FALSE),
    ('UNESCO WHC 1315: Shushtar Historical Hydraulic System — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1315/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point, or complete property polygon.', FALSE),
    ('UNESCO WHC 1208: Bam and its Cultural Landscape — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1208/', 'Official UNESCO World Heritage Centre property description. Persian text in this dataset is an original concise paraphrase, not a verbatim reproduction. The page displays a CC-BY-SA IGO 3.0 license notice.', FALSE),
    ('UNESCO WHC 1208: Bam and its Cultural Landscape — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1208/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point, or complete property polygon.', FALSE),
    ('UNESCO WHC 1188: Soltaniyeh — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1188/', 'Official UNESCO World Heritage Centre property description. Persian text in this dataset is an original concise paraphrase, not a verbatim reproduction. The page displays a CC-BY-SA IGO 3.0 license notice.', FALSE),
    ('UNESCO WHC 1188: Soltaniyeh — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1188/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point, or complete property polygon.', FALSE),
    ('UNESCO WHC 1222: Bisotun — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1222/', 'Official UNESCO World Heritage Centre property description. Persian text in this dataset is an original concise paraphrase, not a verbatim reproduction. The page displays a CC-BY-SA IGO 3.0 license notice.', FALSE),
    ('UNESCO WHC 1222: Bisotun — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1222/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point, or complete property polygon.', FALSE),
    ('UNESCO WHC 1106: Pasargadae — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1106/', 'Official UNESCO World Heritage Centre property description. Persian text in this dataset is an original concise paraphrase, not a verbatim reproduction. The page displays a CC-BY-SA IGO 3.0 license notice.', FALSE),
    ('UNESCO WHC 1106: Pasargadae — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1106/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point, or complete property polygon.', FALSE),
    ('UNESCO WHC 1398: Gonbad-e Qābus — description', 'world_heritage_description', 'verified', NULL, 'https://whc.unesco.org/en/list/1398/', 'Official UNESCO World Heritage Centre property description. Persian text in this dataset is an original concise paraphrase, not a verbatim reproduction. The page displays a CC-BY-SA IGO 3.0 license notice.', FALSE),
    ('UNESCO WHC 1398: Gonbad-e Qābus — mapped property point', 'world_heritage_geodata', 'verified', NULL, 'https://whc.unesco.org/en/list/1398/maps/', 'Official UNESCO World Heritage Centre geographical data/map. Stored coordinate is a property/reference point, not a visitor entrance, road access point, or complete property polygon.', FALSE),
    ('ICID World Heritage Irrigation Structures: Shushtar — location', 'heritage_geographic_reference', 'verified', NULL, 'https://icid-ciid.org/award/his_details/115', 'International Commission on Irrigation and Drainage reference identifies Khuzestan Province and Shushtar. Used only for province/city administrative context; UNESCO remains the primary heritage description and coordinate source.', FALSE),
    ('UNESCO ICOMOS evaluation: Gonbad-e Qābus — location', 'unesco_advisory_evaluation', 'verified', NULL, 'https://whc.unesco.org/document/116681', 'UNESCO advisory-body evaluation identifies Golestan Province for the property. Used as administrative-location evidence.', FALSE)
ON CONFLICT (source_name) DO UPDATE SET source_type=EXCLUDED.source_type, verification_status='verified', reliability_score=EXCLUDED.reliability_score, url=EXCLUDED.url, notes=EXCLUDED.notes, is_synthetic=FALSE, updated_at=NOW();

INSERT INTO knowledge.destinations (
    destination_key, canonical_name, destination_type, province_name, city_name,
    description, aliases, latitude, longitude, coordinate_role, status, data_confidence,
    record_origin, verification_status, is_synthetic, country_code
) VALUES
    ('unesco-persepolis-v1', 'تخت جمشید', 'archaeological_site', 'فارس', NULL, 'محوطه باستانی تخت جمشید در استان فارس، پایتخت تشریفاتی و مجموعه کاخی هخامنشی است که ساخت آن در روزگار داریوش یکم و حدود ۵۱۸ پیش از میلاد آغاز شد. اثر شامل صفه و بقایای مجموعه‌ای از فضاهای تشریفاتی و کاخ‌هاست.', ARRAY['Persepolis', 'تخت جمشید', 'پارسه']::TEXT[], 29.9344400, 52.8902800, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-golestan-palace-v1', 'کاخ گلستان', 'historic_palace', 'تهران', 'تهران', 'کاخ گلستان در بافت تاریخی تهران، مجموعه‌ای از بناهای دوره قاجار است. این مجموعه در دوره قاجار به مرکز حکومت تبدیل شد و ترکیب هنرها و فنون ایرانی با تأثیرهای معماری غربی و آرایه‌های سده نوزدهم از ویژگی‌های ثبت‌شده آن است.', ARRAY['Golestan Palace', 'کاخ گلستان']::TEXT[], 35.6803667, 51.4205111, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-meidan-emam-v1', 'میدان نقش جهان', 'historic_square', 'اصفهان', 'اصفهان', 'میدان نقش جهان در اصفهان، مجموعه‌ای شهری از دوره صفوی است که به فرمان شاه عباس یکم در آغاز سده هفدهم ساخته شد. بناهای شاخص پیرامون میدان از طریق رواق‌ها و گذرهای دوطبقه به یکدیگر پیوند دارند.', ARRAY['Meidan Emam', 'Naqsh-e Jahan Square', 'میدان امام', 'میدان نقش جهان']::TEXT[], 32.6574500, 51.6777778, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-tabriz-bazaar-v1', 'بازار تاریخی تبریز', 'historic_bazaar', 'آذربایجان شرقی', 'تبریز', 'بازار تاریخی تبریز مجموعه‌ای پیوسته از فضاها و ساختمان‌های سرپوشیده آجری با کارکردهای گوناگون تجاری، اجتماعی و فرهنگی است. این بازار در مسیرهای مبادلاتی جاده ابریشم قرار داشته و در سده سیزدهم میلادی رونق و شهرت داشته است.', ARRAY['Tabriz Bazaar', 'Tabriz Historic Bazaar', 'بازار تبریز', 'بازار تاریخی تبریز']::TEXT[], 38.0813889, 46.2930556, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-shushtar-hydraulic-v1', 'سازه‌های آبی تاریخی شوشتر', 'hydraulic_heritage', 'خوزستان', 'شوشتر', 'سازه‌های آبی تاریخی شوشتر مجموعه‌ای از کانال‌های انحرافی، تونل‌ها، پل‌ها، بندها، حوضچه‌ها و آسیاب‌های آبی در ارتباط با رود کارون و کانال گرگر است. پیشینه بخشی از سامانه به دوره باستان نسبت داده شده و این مجموعه نمونه‌ای برجسته از مهندسی آب است.', ARRAY['Shushtar Historical Hydraulic System', 'Shushtar water mills', 'سازه‌های آبی شوشتر', 'آبشارها و آسیاب‌های شوشتر']::TEXT[], 32.0186111, 48.8358333, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-bam-cultural-landscape-v1', 'بم و منظر فرهنگی آن', 'cultural_landscape', 'کرمان', 'بم', 'بم و منظر فرهنگی آن در استان کرمان و در محیطی بیابانی قرار دارد. شکل‌گیری بم به دوره هخامنشی نسبت داده می‌شود و توسعه واحه آن بر شبکه قنات‌های زیرزمینی متکی بوده است. ارگ بم نمونه‌ای شاخص از شهر محصور تاریخی با ساخت‌وساز خشتی است.', ARRAY['Arg-e Bam', 'Bam Citadel', 'Bam and its Cultural Landscape', 'ارگ بم', 'بم و منظر فرهنگی آن']::TEXT[], 29.1168300, 58.3666667, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-soltaniyeh-v1', 'گنبد سلطانیه', 'historic_mausoleum', 'زنجان', 'سلطانیه', 'گنبد سلطانیه در استان زنجان و در شهر سلطانیه، آرامگاه اولجایتو است که در سال‌های ۱۳۰۲ تا ۱۳۱۲ میلادی ساخته شد. بنای هشت‌ضلعی آن با گنبدی بلند و پوشش کاشی فیروزه‌ای شناخته می‌شود و در تاریخ معماری اسلامی ایران جایگاه مهمی دارد.', ARRAY['Soltaniyeh Dome', 'Dome of Soltaniyeh', 'گنبد اولجایتو', 'گنبد سلطانیه']::TEXT[], 36.4339722, 48.7960278, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-bisotun-v1', 'بیستون', 'archaeological_site', 'کرمانشاه', NULL, 'محوطه باستانی بیستون در استان کرمانشاه در مسیر تاریخی پیونددهنده فلات ایران و میان‌رودان قرار دارد. شاخص‌ترین اثر آن نقش‌برجسته و کتیبه داریوش یکم است که پس از به‌قدرت رسیدن او در سال ۵۲۱ پیش از میلاد فرمان داده شد.', ARRAY['Behistun', 'Bisotun Inscription', 'کتیبه بیستون', 'بیستون']::TEXT[], 34.3883333, 47.4366667, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-pasargadae-v1', 'پاسارگاد', 'archaeological_landscape', 'فارس', NULL, 'پاسارگاد در استان فارس نخستین پایتخت دودمانی امپراتوری هخامنشی بود که به کوروش دوم نسبت داده می‌شود. محوطه گسترده آن بقایای کاخ‌ها، باغ‌ها، مجموعه سلطنتی و آرامگاه کوروش را در بر می‌گیرد.', ARRAY['Pasargadae', 'Pasargad', 'پاسارگاد']::TEXT[], 30.1938300, 53.1672900, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR'),
    ('unesco-gonbad-e-qabus-v1', 'گنبد قابوس', 'monument_tower', 'گلستان', 'گنبد کاووس', 'گنبد قابوس در شهر گنبد کاووس استان گلستان، برج آرامگاهی آجری به ارتفاع حدود ۵۳ متر است که در سال ۱۰۰۶ میلادی برای قابوس بن وشمگیر ساخته شد. ساختار هندسی و بدنه آجری آن از نمونه‌های برجسته معماری اوایل دوره اسلامی است.', ARRAY['Gonbad-e Qabus', 'Qabus Tower', 'Gonbad-e Kavus Tower', 'گنبد قابوس', 'برج قابوس']::TEXT[], 37.2580278, 55.1690000, 'property_reference', 'needs_review', 0, 'verified_external', 'verified', FALSE, 'IR')
ON CONFLICT (destination_key) DO UPDATE SET canonical_name=EXCLUDED.canonical_name, destination_type=EXCLUDED.destination_type, province_name=EXCLUDED.province_name, city_name=EXCLUDED.city_name, description=EXCLUDED.description, aliases=EXCLUDED.aliases, latitude=EXCLUDED.latitude, longitude=EXCLUDED.longitude, coordinate_role=EXCLUDED.coordinate_role, status='needs_review', data_confidence=EXCLUDED.data_confidence, record_origin='verified_external', verification_status='verified', is_synthetic=FALSE, country_code=EXCLUDED.country_code, updated_at=NOW();

INSERT INTO knowledge.destination_sources (destination_id, source_id, source_role, evidence_note, retrieved_at)
SELECT d.destination_id, s.source_id, x.source_role, x.evidence_note, NOW()
FROM (VALUES
    ('unesco-persepolis-v1', 'unesco-persepolis-v1-content', 'primary', 'Official UNESCO property description; Persian summary is an original paraphrase.'),
    ('unesco-persepolis-v1', 'unesco-persepolis-v1-map', 'verification', 'Official UNESCO property/reference coordinate; not a visitor entrance.'),
    ('unesco-golestan-palace-v1', 'unesco-golestan-palace-v1-content', 'primary', 'Official UNESCO property description; Persian summary is an original paraphrase.'),
    ('unesco-golestan-palace-v1', 'unesco-golestan-palace-v1-map', 'verification', 'Official UNESCO property/reference coordinate; not a visitor entrance.'),
    ('unesco-meidan-emam-v1', 'unesco-meidan-emam-v1-content', 'primary', 'Official UNESCO property description; Persian summary is an original paraphrase.'),
    ('unesco-meidan-emam-v1', 'unesco-meidan-emam-v1-map', 'verification', 'Official UNESCO property/reference coordinate; not a visitor entrance.'),
    ('unesco-tabriz-bazaar-v1', 'unesco-tabriz-bazaar-v1-content', 'primary', 'Official UNESCO property description; Persian summary is an original paraphrase.'),
    ('unesco-tabriz-bazaar-v1', 'unesco-tabriz-bazaar-v1-map', 'verification', 'Official UNESCO property/reference coordinate; not a visitor entrance.'),
    ('unesco-shushtar-hydraulic-v1', 'unesco-shushtar-hydraulic-v1-content', 'primary', 'Official UNESCO property description; Persian summary is an original paraphrase.'),
    ('unesco-shushtar-hydraulic-v1', 'unesco-shushtar-hydraulic-v1-map', 'verification', 'Official UNESCO property/reference coordinate; not a visitor entrance.'),
    ('unesco-bam-cultural-landscape-v1', 'unesco-bam-cultural-landscape-v1-content', 'primary', 'Official UNESCO property description; Persian summary is an original paraphrase.'),
    ('unesco-bam-cultural-landscape-v1', 'unesco-bam-cultural-landscape-v1-map', 'verification', 'Official UNESCO property/reference coordinate; not a visitor entrance.'),
    ('unesco-soltaniyeh-v1', 'unesco-soltaniyeh-v1-content', 'primary', 'Official UNESCO property description; Persian summary is an original paraphrase.'),
    ('unesco-soltaniyeh-v1', 'unesco-soltaniyeh-v1-map', 'verification', 'Official UNESCO property/reference coordinate; not a visitor entrance.'),
    ('unesco-bisotun-v1', 'unesco-bisotun-v1-content', 'primary', 'Official UNESCO property description; Persian summary is an original paraphrase.'),
    ('unesco-bisotun-v1', 'unesco-bisotun-v1-map', 'verification', 'Official UNESCO property/reference coordinate; not a visitor entrance.'),
    ('unesco-pasargadae-v1', 'unesco-pasargadae-v1-content', 'primary', 'Official UNESCO property description; Persian summary is an original paraphrase.'),
    ('unesco-pasargadae-v1', 'unesco-pasargadae-v1-map', 'verification', 'Official UNESCO property/reference coordinate; not a visitor entrance.'),
    ('unesco-gonbad-e-qabus-v1', 'unesco-gonbad-e-qabus-v1-content', 'primary', 'Official UNESCO property description; Persian summary is an original paraphrase.'),
    ('unesco-gonbad-e-qabus-v1', 'unesco-gonbad-e-qabus-v1-map', 'verification', 'Official UNESCO property/reference coordinate; not a visitor entrance.'),
    ('unesco-shushtar-hydraulic-v1', 'unesco-shushtar-admin', 'secondary', 'Administrative province/city reference: Khuzestan / Shushtar.'),
    ('unesco-gonbad-e-qabus-v1', 'unesco-gonbad-admin', 'secondary', 'Administrative province reference: Golestan.')
) AS x(destination_key, source_key, source_role, evidence_note)
JOIN knowledge.destinations d ON d.destination_key=x.destination_key
JOIN knowledge.knowledge_sources s ON s.source_name = CASE x.source_key
    WHEN 'unesco-persepolis-v1-content' THEN 'UNESCO WHC 114: Persepolis — description'
    WHEN 'unesco-persepolis-v1-map' THEN 'UNESCO WHC 114: Persepolis — mapped property point'
    WHEN 'unesco-golestan-palace-v1-content' THEN 'UNESCO WHC 1422: Golestan Palace — description'
    WHEN 'unesco-golestan-palace-v1-map' THEN 'UNESCO WHC 1422: Golestan Palace — mapped property point'
    WHEN 'unesco-meidan-emam-v1-content' THEN 'UNESCO WHC 115: Meidan Emam, Esfahan — description'
    WHEN 'unesco-meidan-emam-v1-map' THEN 'UNESCO WHC 115: Meidan Emam, Esfahan — mapped property point'
    WHEN 'unesco-tabriz-bazaar-v1-content' THEN 'UNESCO WHC 1346: Tabriz Historic Bazaar Complex — description'
    WHEN 'unesco-tabriz-bazaar-v1-map' THEN 'UNESCO WHC 1346: Tabriz Historic Bazaar Complex — mapped property point'
    WHEN 'unesco-shushtar-hydraulic-v1-content' THEN 'UNESCO WHC 1315: Shushtar Historical Hydraulic System — description'
    WHEN 'unesco-shushtar-hydraulic-v1-map' THEN 'UNESCO WHC 1315: Shushtar Historical Hydraulic System — mapped property point'
    WHEN 'unesco-bam-cultural-landscape-v1-content' THEN 'UNESCO WHC 1208: Bam and its Cultural Landscape — description'
    WHEN 'unesco-bam-cultural-landscape-v1-map' THEN 'UNESCO WHC 1208: Bam and its Cultural Landscape — mapped property point'
    WHEN 'unesco-soltaniyeh-v1-content' THEN 'UNESCO WHC 1188: Soltaniyeh — description'
    WHEN 'unesco-soltaniyeh-v1-map' THEN 'UNESCO WHC 1188: Soltaniyeh — mapped property point'
    WHEN 'unesco-bisotun-v1-content' THEN 'UNESCO WHC 1222: Bisotun — description'
    WHEN 'unesco-bisotun-v1-map' THEN 'UNESCO WHC 1222: Bisotun — mapped property point'
    WHEN 'unesco-pasargadae-v1-content' THEN 'UNESCO WHC 1106: Pasargadae — description'
    WHEN 'unesco-pasargadae-v1-map' THEN 'UNESCO WHC 1106: Pasargadae — mapped property point'
    WHEN 'unesco-gonbad-e-qabus-v1-content' THEN 'UNESCO WHC 1398: Gonbad-e Qābus — description'
    WHEN 'unesco-gonbad-e-qabus-v1-map' THEN 'UNESCO WHC 1398: Gonbad-e Qābus — mapped property point'
    WHEN 'unesco-shushtar-admin' THEN 'ICID World Heritage Irrigation Structures: Shushtar — location'
    WHEN 'unesco-gonbad-admin' THEN 'UNESCO ICOMOS evaluation: Gonbad-e Qābus — location'
END
ON CONFLICT (destination_id, source_id) DO UPDATE SET source_role=EXCLUDED.source_role, evidence_note=EXCLUDED.evidence_note, retrieved_at=EXCLUDED.retrieved_at;

INSERT INTO knowledge.destination_category_map (destination_id, category_id, mapping_source, is_synthetic)
SELECT d.destination_id, c.category_id, 'curated_unesco_seed_v1', FALSE
FROM (VALUES
    ('unesco-persepolis-v1', 'historical'),
    ('unesco-golestan-palace-v1', 'historical'),
    ('unesco-meidan-emam-v1', 'historical'),
    ('unesco-tabriz-bazaar-v1', 'historical'),
    ('unesco-shushtar-hydraulic-v1', 'historical'),
    ('unesco-bam-cultural-landscape-v1', 'historical'),
    ('unesco-bam-cultural-landscape-v1', 'desert'),
    ('unesco-soltaniyeh-v1', 'historical'),
    ('unesco-bisotun-v1', 'historical'),
    ('unesco-pasargadae-v1', 'historical'),
    ('unesco-gonbad-e-qabus-v1', 'historical')
) AS x(destination_key, category_key)
JOIN knowledge.destinations d ON d.destination_key=x.destination_key
JOIN knowledge.destination_categories c ON c.category_key=x.category_key
ON CONFLICT (destination_id, category_id) DO UPDATE SET mapping_source=EXCLUDED.mapping_source, is_synthetic=FALSE;

INSERT INTO knowledge.destination_tags (destination_id, tag)
SELECT destination_id, 'unesco_world_heritage' FROM knowledge.destinations
WHERE destination_key LIKE 'unesco-%-v1' ON CONFLICT DO NOTHING;

INSERT INTO knowledge.knowledge_documents (
    document_key, source_id, destination_id, title, language_code, document_type,
    canonical_url, raw_content, content_sha256, ingestion_status, record_origin,
    is_synthetic, retrieved_at
) SELECT x.document_key, s.source_id, d.destination_id, x.title, 'fa', 'destination_profile',
         x.canonical_url, x.raw_content, x.content_sha256, 'processed', 'verified_external', FALSE,
         NOW()
FROM (VALUES
    ('unesco-persepolis-v1-doc', 'پرونده دانش میراث جهانی: تخت جمشید', 'https://whc.unesco.org/en/list/114/', 'تخت جمشید یا پرسپولیس در استان فارس قرار دارد. ساخت صفه و مجموعه کاخی آن در حدود ۵۱۸ پیش از میلاد به فرمان داریوش یکم آغاز شد و از مهم‌ترین محوطه‌های باستانی دوره هخامنشی به شمار می‌رود. مختصات ثبت‌شده در صفحه نقشه میراث جهانی یونسکو، نقطه مرجع ملک میراثی است و لزوماً ورودی بازدیدکنندگان نیست. برای مسیریابی خودرو یا تعیین ورودی باید منبع دسترسی جداگانه بررسی شود.', '65e96c69e5e15917fa48825d88c2f740c073895b2eff48af2e37d996fb455454'),
    ('unesco-golestan-palace-v1-doc', 'پرونده دانش میراث جهانی: کاخ گلستان', 'https://whc.unesco.org/en/list/1422/', 'کاخ گلستان از مجموعه‌های تاریخی تهران و از آثار شاخص دوره قاجار است. این مجموعه پس از پایتخت شدن تهران به مرکز حکومتی قاجار تبدیل شد. صفحه یونسکو به باغ، حوض‌ها و تزئینات و هنرهای قاجاری سده نوزدهم اشاره می‌کند. مختصات یونسکو نقطه مرجع اثر ثبت‌شده است، نه لزوماً در ورودی یا گیت بازدید.', '9071f39932aaa7985d7ea8e68aceb6d3b05c70c7f604443609317e7bc98c6158'),
    ('unesco-meidan-emam-v1-doc', 'پرونده دانش میراث جهانی: میدان نقش جهان', 'https://whc.unesco.org/en/list/115/', 'میدان نقش جهان یا میدان امام اصفهان در آغاز قرن هفدهم و در دوره شاه عباس یکم ساخته شد. این مجموعه شامل بناهای شاخصی مانند مسجد شاه، مسجد شیخ لطف‌الله و سردر قیصریه است. میدان و بناهای پیرامون آن نمونه‌ای از زندگی اجتماعی و فرهنگی دوره صفوی هستند. مختصات ثبت‌شده در نقشه یونسکو نقطه مرجع اثر است؛ جزئیات ورودی‌ها و مسیرهای پیاده باید جداگانه راستی‌آزمایی شوند.', '12125b1e69d78dbbc32733d416b1cae7b451278a014f07c4f61dd77dd529b07a'),
    ('unesco-tabriz-bazaar-v1-doc', 'پرونده دانش میراث جهانی: بازار تاریخی تبریز', 'https://whc.unesco.org/en/list/1346/', 'بازار تاریخی تبریز در استان آذربایجان شرقی قرار دارد. یونسکو آن را مجموعه‌ای از ساختارهای آجری سرپوشیده و فضاهای به‌هم‌پیوسته با کارکردهای تجاری و اجتماعی توصیف می‌کند. تبریز و بازار آن در قرن سیزدهم میلادی از مراکز مهم تجاری بودند و شهر در دوره صفوی پایتخت شد. نقطه ثبت‌شده روی نقشه یونسکو با عنوان Center آمده و صرفاً نقطه مرجع مجموعه است.', 'c83e1d4ef0525987741b5b864f0caab0e478297bf958712044e0d7d98795cf9b'),
    ('unesco-shushtar-hydraulic-v1-doc', 'پرونده دانش میراث جهانی: سازه‌های آبی تاریخی شوشتر', 'https://whc.unesco.org/en/list/1315/', 'سازه‌های آبی تاریخی شوشتر در خوزستان، مجموعه‌ای از سازه‌های مهندسی آب شامل کانال‌های انحرافی، تونل‌ها، آسیاب‌ها، پل‌ها و بندهاست. کانال گرگر بخشی از سامانه‌ای است که آب را به شهر شوشتر می‌رسانده است. یونسکو پیشینه سامانه را به دوره داریوش بزرگ نسبت می‌دهد و به پیوند آن با رود کارون و دشت میان‌آب اشاره می‌کند. نقطه درج‌شده در نقشه، مرجع ملک میراثی است و جانشین مختصات تک‌تک اجزا یا ورودی بازدید نیست.', '306b0a6b9f31cdb436d0a142183c757178a34c20cc8613cecb1bef41277de280'),
    ('unesco-bam-cultural-landscape-v1-doc', 'پرونده دانش میراث جهانی: بم و منظر فرهنگی آن', 'https://whc.unesco.org/en/list/1208/', 'بم و منظر فرهنگی آن در استان کرمان و در حاشیه جنوبی فلات ایران قرار دارد. حیات واحه تاریخی بم به قنات‌های زیرزمینی وابسته بوده و بخشی از شواهد کهن قنات در این منطقه حفظ شده است. ارگ بم نمونه شاخص شهر محصور قرون میانه با تکنیک ساخت لایه‌ای از خشت و خاک است. این اثر در محیط بیابانی قرار دارد؛ با این حال داده فعلی هیچ توصیه فصلی، وضعیت ایمنی یا شرایط دسترسی روز را تأیید نمی‌کند.', 'be63c6cb8613eca6bf046f150c00c0c409233ca70783f372d480a3675ce3ad60'),
    ('unesco-soltaniyeh-v1-doc', 'پرونده دانش میراث جهانی: گنبد سلطانیه', 'https://whc.unesco.org/en/list/1188/', 'گنبد سلطانیه آرامگاه اولجایتو در شهر سلطانیه استان زنجان است. ساخت بنا در فاصله سال‌های ۱۳۰۲ تا ۱۳۱۲ میلادی انجام شد و ساختمان هشت‌ضلعی با گنبدی بلند دارد. یونسکو این بنا را نمونه‌ای مهم در تحول معماری اسلامی ایران معرفی می‌کند. نقطه درج‌شده در جدول جغرافیایی یونسکو برای جزء «گنبد سلطانیه» است؛ مجموعه گسترده‌تر دارای اجزای دیگری نیز هست.', 'b7ec51f6aecf0edb983dbe48dc76f22d557191e99c88c08cd3acbf6178b13287'),
    ('unesco-bisotun-v1-doc', 'پرونده دانش میراث جهانی: بیستون', 'https://whc.unesco.org/en/list/1222/', 'بیستون در استان کرمانشاه قرار دارد و در آن آثار دوره‌های گوناگون از پیشاتاریخ تا دوره‌های تاریخی دیده می‌شود. اثر شاخص محوطه، نقش‌برجسته و کتیبه داریوش یکم است. کتیبه بیستون به سه زبان نوشته شده و روایت‌هایی از رخدادهای آغاز فرمانروایی داریوش را ثبت می‌کند. مختصات یونسکو به ملک میراثی اشاره دارد و محل دقیق ورودی یا مسیر دسترسی باید جداگانه بررسی شود.', '123a163ae591618d96c607003ffbf7cdedb04eb9b797cb02dd2b6373cf99100a'),
    ('unesco-pasargadae-v1-doc', 'پرونده دانش میراث جهانی: پاسارگاد', 'https://whc.unesco.org/en/list/1106/', 'پاسارگاد در استان فارس به‌عنوان نخستین پایتخت دودمانی هخامنشی معرفی شده است. این مجموعه به بنیان‌گذاری کوروش دوم در سده ششم پیش از میلاد نسبت داده می‌شود. از اجزای مهم محوطه پاسارگاد می‌توان به آرامگاه کوروش، تل تخت، دروازه، تالار بارعام، بقایای کاخ و باغ اشاره کرد. نقطه یونسکو نقطه مرجع ملک ثبت‌شده است و محدوده اثر بسیار گسترده‌تر از یک نقطه است.', 'b88aa1cb7a2755f0dec8b5951c96e09af0780a574ca28b7d04bdda84f477852a'),
    ('unesco-gonbad-e-qabus-v1-doc', 'پرونده دانش میراث جهانی: گنبد قابوس', 'https://whc.unesco.org/en/list/1398/', 'گنبد قابوس در شهر گنبد کاووس استان گلستان قرار دارد. این برج آرامگاهی در سال ۱۰۰۶ میلادی برای قابوس بن وشمگیر ساخته شد و ارتفاع آن حدود ۵۳ متر است. یونسکو این اثر را نمونه‌ای برجسته از معماری آجری اوایل دوره اسلامی و نوآوری سازه‌ای می‌داند. مختصات جغرافیایی در جدول نقشه یونسکو ثبت شده، اما ساعات بازدید، قیمت و وضعیت کنونی دسترسی در این داده وجود ندارد.', '4d3123a985e18d464dba0910ef9e624f285dfb3a6e5e8b2503e34e37a75d10e1')
) AS x(document_key, title, canonical_url, raw_content, content_sha256)
JOIN knowledge.knowledge_sources s ON s.source_name = CASE x.document_key
    WHEN 'unesco-persepolis-v1-doc' THEN 'UNESCO WHC 114: Persepolis — description'
    WHEN 'unesco-golestan-palace-v1-doc' THEN 'UNESCO WHC 1422: Golestan Palace — description'
    WHEN 'unesco-meidan-emam-v1-doc' THEN 'UNESCO WHC 115: Meidan Emam, Esfahan — description'
    WHEN 'unesco-tabriz-bazaar-v1-doc' THEN 'UNESCO WHC 1346: Tabriz Historic Bazaar Complex — description'
    WHEN 'unesco-shushtar-hydraulic-v1-doc' THEN 'UNESCO WHC 1315: Shushtar Historical Hydraulic System — description'
    WHEN 'unesco-bam-cultural-landscape-v1-doc' THEN 'UNESCO WHC 1208: Bam and its Cultural Landscape — description'
    WHEN 'unesco-soltaniyeh-v1-doc' THEN 'UNESCO WHC 1188: Soltaniyeh — description'
    WHEN 'unesco-bisotun-v1-doc' THEN 'UNESCO WHC 1222: Bisotun — description'
    WHEN 'unesco-pasargadae-v1-doc' THEN 'UNESCO WHC 1106: Pasargadae — description'
    WHEN 'unesco-gonbad-e-qabus-v1-doc' THEN 'UNESCO WHC 1398: Gonbad-e Qābus — description'
END
JOIN knowledge.destinations d ON d.destination_key = REPLACE(x.document_key, '-doc', '')
ON CONFLICT (document_key) DO UPDATE SET source_id=EXCLUDED.source_id, destination_id=EXCLUDED.destination_id, title=EXCLUDED.title, canonical_url=EXCLUDED.canonical_url, raw_content=EXCLUDED.raw_content, content_sha256=EXCLUDED.content_sha256, ingestion_status='processed', record_origin='verified_external', is_synthetic=FALSE, retrieved_at=EXCLUDED.retrieved_at, updated_at=NOW();

INSERT INTO knowledge.knowledge_chunks (document_id, chunk_index, content, char_count, content_sha256, metadata, is_synthetic)
SELECT d.document_id, x.chunk_index, x.content, CHAR_LENGTH(x.content), x.content_sha256,
       jsonb_build_object('dataset_key', 'unesco-iran-first-batch-v1', 'destination_key', x.destination_key, 'chunk_role', x.chunk_role, 'source_license_notice', 'CC-BY-SA IGO 3.0; original Persian paraphrase'), FALSE
FROM (VALUES
    ('unesco-persepolis-v1', 0, 'تخت جمشید یا پرسپولیس در استان فارس قرار دارد. ساخت صفه و مجموعه کاخی آن در حدود ۵۱۸ پیش از میلاد به فرمان داریوش یکم آغاز شد و از مهم‌ترین محوطه‌های باستانی دوره هخامنشی به شمار می‌رود.', '1b48030acb3d67dc1b97d8c4a33aeadf7963de628a9e929c62d05dc76f15991f', 'overview'),
    ('unesco-persepolis-v1', 1, 'مختصات ثبت‌شده در صفحه نقشه میراث جهانی یونسکو، نقطه مرجع ملک میراثی است و لزوماً ورودی بازدیدکنندگان نیست. برای مسیریابی خودرو یا تعیین ورودی باید منبع دسترسی جداگانه بررسی شود.', '6d07684ae1f734ddaea47105ff6f5d083ec4a13881b9ed6a566392bbec52405c', 'context_and_limitations'),
    ('unesco-golestan-palace-v1', 0, 'کاخ گلستان از مجموعه‌های تاریخی تهران و از آثار شاخص دوره قاجار است. این مجموعه پس از پایتخت شدن تهران به مرکز حکومتی قاجار تبدیل شد.', '2adba14072843c293c8baa50d210e21ad6b597b9260e452d52cea920697ba10b', 'overview'),
    ('unesco-golestan-palace-v1', 1, 'صفحه یونسکو به باغ، حوض‌ها و تزئینات و هنرهای قاجاری سده نوزدهم اشاره می‌کند. مختصات یونسکو نقطه مرجع اثر ثبت‌شده است، نه لزوماً در ورودی یا گیت بازدید.', 'b66caab2cc87fe11c0a3f4deaa585e3f0e257781c194b2a3dc9315c7cb0ea78b', 'context_and_limitations'),
    ('unesco-meidan-emam-v1', 0, 'میدان نقش جهان یا میدان امام اصفهان در آغاز قرن هفدهم و در دوره شاه عباس یکم ساخته شد. این مجموعه شامل بناهای شاخصی مانند مسجد شاه، مسجد شیخ لطف‌الله و سردر قیصریه است.', '7c29482de7a9251207cd70097b7701cb6a21f6fd3807dfcbeee515a548b2a688', 'overview'),
    ('unesco-meidan-emam-v1', 1, 'میدان و بناهای پیرامون آن نمونه‌ای از زندگی اجتماعی و فرهنگی دوره صفوی هستند. مختصات ثبت‌شده در نقشه یونسکو نقطه مرجع اثر است؛ جزئیات ورودی‌ها و مسیرهای پیاده باید جداگانه راستی‌آزمایی شوند.', 'b0c49e86fbccde0311945d6edd94189b9e076121613b674113dd3086770c7450', 'context_and_limitations'),
    ('unesco-tabriz-bazaar-v1', 0, 'بازار تاریخی تبریز در استان آذربایجان شرقی قرار دارد. یونسکو آن را مجموعه‌ای از ساختارهای آجری سرپوشیده و فضاهای به‌هم‌پیوسته با کارکردهای تجاری و اجتماعی توصیف می‌کند.', 'a3aded284a9c00f799df8b0d8c4fe4480be933380f8c1b8c3f1518297d6d7d66', 'overview'),
    ('unesco-tabriz-bazaar-v1', 1, 'تبریز و بازار آن در قرن سیزدهم میلادی از مراکز مهم تجاری بودند و شهر در دوره صفوی پایتخت شد. نقطه ثبت‌شده روی نقشه یونسکو با عنوان Center آمده و صرفاً نقطه مرجع مجموعه است.', '9967435d94f025901ab2f358f259657021c9334b1b3a5e29eee380d245cdc38f', 'context_and_limitations'),
    ('unesco-shushtar-hydraulic-v1', 0, 'سازه‌های آبی تاریخی شوشتر در خوزستان، مجموعه‌ای از سازه‌های مهندسی آب شامل کانال‌های انحرافی، تونل‌ها، آسیاب‌ها، پل‌ها و بندهاست. کانال گرگر بخشی از سامانه‌ای است که آب را به شهر شوشتر می‌رسانده است.', '2d5d6338ea1694e0ba0985baf8fda94ee9cd77f437e0af9a1a41bfb5db844144', 'overview'),
    ('unesco-shushtar-hydraulic-v1', 1, 'یونسکو پیشینه سامانه را به دوره داریوش بزرگ نسبت می‌دهد و به پیوند آن با رود کارون و دشت میان‌آب اشاره می‌کند. نقطه درج‌شده در نقشه، مرجع ملک میراثی است و جانشین مختصات تک‌تک اجزا یا ورودی بازدید نیست.', 'a89ae1dbaf4cb62afd65021413ada04bd68ffe7826ddb9a2465164b4ffcbcedc', 'context_and_limitations'),
    ('unesco-bam-cultural-landscape-v1', 0, 'بم و منظر فرهنگی آن در استان کرمان و در حاشیه جنوبی فلات ایران قرار دارد. حیات واحه تاریخی بم به قنات‌های زیرزمینی وابسته بوده و بخشی از شواهد کهن قنات در این منطقه حفظ شده است.', '6306837d7625cc476f20bb83ae1189e9b7c96899f685cc0dd76634efa5153fec', 'overview'),
    ('unesco-bam-cultural-landscape-v1', 1, 'ارگ بم نمونه شاخص شهر محصور قرون میانه با تکنیک ساخت لایه‌ای از خشت و خاک است. این اثر در محیط بیابانی قرار دارد؛ با این حال داده فعلی هیچ توصیه فصلی، وضعیت ایمنی یا شرایط دسترسی روز را تأیید نمی‌کند.', 'b901287ccbd9d8ba2755624a113e06b7d123644a029f1b1707954e51745189f5', 'context_and_limitations'),
    ('unesco-soltaniyeh-v1', 0, 'گنبد سلطانیه آرامگاه اولجایتو در شهر سلطانیه استان زنجان است. ساخت بنا در فاصله سال‌های ۱۳۰۲ تا ۱۳۱۲ میلادی انجام شد و ساختمان هشت‌ضلعی با گنبدی بلند دارد.', 'd37c82e86d362dfcf9681efaa3642bc8e398bcfc42dcbb930db35c095d07d6a1', 'overview'),
    ('unesco-soltaniyeh-v1', 1, 'یونسکو این بنا را نمونه‌ای مهم در تحول معماری اسلامی ایران معرفی می‌کند. نقطه درج‌شده در جدول جغرافیایی یونسکو برای جزء «گنبد سلطانیه» است؛ مجموعه گسترده‌تر دارای اجزای دیگری نیز هست.', '9b0470401b0b4872c79d27f1057319dc273e70dda7ecb3f32a8955c17f61f259', 'context_and_limitations'),
    ('unesco-bisotun-v1', 0, 'بیستون در استان کرمانشاه قرار دارد و در آن آثار دوره‌های گوناگون از پیشاتاریخ تا دوره‌های تاریخی دیده می‌شود. اثر شاخص محوطه، نقش‌برجسته و کتیبه داریوش یکم است.', 'e4c3e16a9764bb70b794cdcfa64ec457dcaa52de63105b919a3286f11b27395c', 'overview'),
    ('unesco-bisotun-v1', 1, 'کتیبه بیستون به سه زبان نوشته شده و روایت‌هایی از رخدادهای آغاز فرمانروایی داریوش را ثبت می‌کند. مختصات یونسکو به ملک میراثی اشاره دارد و محل دقیق ورودی یا مسیر دسترسی باید جداگانه بررسی شود.', '7e55fe053fb3960f25ba78877711643bc785af6a21c49220565792cf336d4f02', 'context_and_limitations'),
    ('unesco-pasargadae-v1', 0, 'پاسارگاد در استان فارس به‌عنوان نخستین پایتخت دودمانی هخامنشی معرفی شده است. این مجموعه به بنیان‌گذاری کوروش دوم در سده ششم پیش از میلاد نسبت داده می‌شود.', 'd4aeec732938245fc1231eeef428bdf2362f489db43b589b1198cdc836ecff02', 'overview'),
    ('unesco-pasargadae-v1', 1, 'از اجزای مهم محوطه پاسارگاد می‌توان به آرامگاه کوروش، تل تخت، دروازه، تالار بارعام، بقایای کاخ و باغ اشاره کرد. نقطه یونسکو نقطه مرجع ملک ثبت‌شده است و محدوده اثر بسیار گسترده‌تر از یک نقطه است.', '58c497928e6dac6d0f03cb8a8d4b89857e102a8fb1489b6ff1863619d462da3b', 'context_and_limitations'),
    ('unesco-gonbad-e-qabus-v1', 0, 'گنبد قابوس در شهر گنبد کاووس استان گلستان قرار دارد. این برج آرامگاهی در سال ۱۰۰۶ میلادی برای قابوس بن وشمگیر ساخته شد و ارتفاع آن حدود ۵۳ متر است.', '3ec87f32fc3d2177aea32d26a4f1897f5c82ca3c2a8928322f3ca86d2f3c1721', 'overview'),
    ('unesco-gonbad-e-qabus-v1', 1, 'یونسکو این اثر را نمونه‌ای برجسته از معماری آجری اوایل دوره اسلامی و نوآوری سازه‌ای می‌داند. مختصات جغرافیایی در جدول نقشه یونسکو ثبت شده، اما ساعات بازدید، قیمت و وضعیت کنونی دسترسی در این داده وجود ندارد.', '0c61fef7b724c8df23908e6746e5786ae99c746edde1930115c94f9b2757d9d1', 'context_and_limitations')
) AS x(destination_key, chunk_index, content, content_sha256, chunk_role)
JOIN knowledge.knowledge_documents d ON d.document_key = x.destination_key || '-doc'
ON CONFLICT (document_id, chunk_index) DO UPDATE SET content=EXCLUDED.content, char_count=EXCLUDED.char_count, content_sha256=EXCLUDED.content_sha256, metadata=EXCLUDED.metadata, is_synthetic=FALSE;

INSERT INTO operations.dataset_import_batches (batch_key, data_class, source_id, record_counts, notes)
VALUES ('verified-unesco-iran-sites-v1', 'verified_external', NULL,
        '{"destinations":10,"sources":22,"destination_source_links":22,"categories":12,"category_mappings":11,"documents":10,"chunks":20}'::JSONB,
        'First curated external batch from official UNESCO World Heritage Centre property descriptions and map records, plus two administrative cross-check sources. Rows are source-verified but remain needs_review and are not published. Coordinates are property/reference points, not visitor entrances. Descriptive source license notice: CC-BY-SA IGO 3.0; descriptions are original paraphrases.')
ON CONFLICT (batch_key) DO UPDATE SET data_class=EXCLUDED.data_class, source_id=NULL, record_counts=EXCLUDED.record_counts, notes=EXCLUDED.notes;

INSERT INTO system.schema_migrations (migration_id, sha256)
VALUES ('0005_verified_unesco_destination_seed', :'migration_hash')
ON CONFLICT (migration_id) DO NOTHING;
COMMIT;
