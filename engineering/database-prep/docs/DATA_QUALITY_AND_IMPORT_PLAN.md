# Data quality and population plan

## Current source inventory

The existing `database/tourism_points.sql` contains 15 destination rows and one supplied dataset source. Its own comments say the source field is `در دست جستجو`, coordinates are not supplied, and all records are `needs_review` with confidence 0. The preparation migration preserves this fact rather than silently promoting those records to verified content.

Current names to review individually:

1. رصدخانه مراغه
2. شهرستانک
3. دره زمان
4. دشت لار
5. تهران گردی
6. جنگل ابر
7. سافاری اوپرت تا اولنگ
8. کالپوش تا آبشار لوه
9. کویر حاج علی قلی
10. باداب سورت
11. رامسر و شمال
12. آبشار عروس دامن
13. آبشار گزو
14. دشت دریاسر
15. همدان

No row in this list is marked externally verified by this package. The current province/city/category/description values are not assumed correct just because they are in the source SQL. Each must be checked against reliable sources and, where applicable, coordinate sources before publication.

## Synthetic QA dataset

Twelve artificial destination fixtures provide controlled test coverage for nature, mountain, waterfall, desert, historical, coastal, lake, ecotourism, geology, family, wildlife and adventure use cases. Their names contain `QA`, their keys start with `qa-`, their coordinates are arbitrary test-plane coordinates near (0,0), and their status is `test_only`. These are not real locations. The 12 category records are the canonical product taxonomy and remain active. Only the 12 destination-to-category QA mappings are synthetic and excluded from production views.

Each synthetic destination has one synthetic knowledge document and two synthetic chunks. The test source explicitly says it is fabricated and is not a factual evidence source.

## First verified-external factual batch (UNESCO)

Ten Iranian World Heritage properties have been added with official UNESCO World Heritage Centre description and map references: Persepolis, Golestan Palace, Meidan Emam/Naqsh-e Jahan, Tabriz Historic Bazaar, Shushtar Historical Hydraulic System, Bam and its Cultural Landscape, Soltaniyeh, Bisotun, Pasargadae and Gonbad-e Qābus. The first batch contains 10 destination rows, 22 source rows/links, 10 Persian paraphrased knowledge documents and 20 chunks. Two additional references provide province context for Shushtar and Gonbad-e Qābus.

The Persian descriptions are original concise paraphrases. UNESCO descriptive pages state CC-BY-SA IGO 3.0; attribution and share-alike obligations must be reviewed before commercial republication. Coordinate values are copied from UNESCO World Heritage Centre geographic/map tables and converted from DMS to decimal degrees. They are marked `coordinate_role='property_reference'`: they are not visitor entrances, road access points, or property polygons. Never derive driving directions, exact distances to gates, or entrance routing from these points alone.

These 10 records have verified source provenance but have `status='needs_review'` pending product-owner/editorial review. The numeric `reliability_score` is left NULL and `data_confidence` remains 0 because the project has not yet established a calibrated scoring rubric; the package does not invent confidence numbers. The publication and RAG views therefore remain empty until each record is explicitly approved. No opening hours, admission fees, seasonality, accessibility, safety status, live availability or transport duration are populated because the first source batch does not establish those operational facts.

## Data population rules for the verified catalogue

For every future factual destination or attraction, capture:

- canonical Persian name and accepted aliases/transliterations (stored in `knowledge.destinations.aliases`)
- entity kind (destination, attraction, route, region, city experience, accommodation, etc.)
- country/province/city/parent entity with verified administrative assignment
- point coordinates, coordinate source/precision, and semantic coordinate role (`visitor_entrance`, `property_reference`, `representative_point`, or `unknown`)
- concise description supported by evidence
- category/tags from a controlled taxonomy
- seasonality, difficulty, transport/accessibility and family suitability only when evidenced
- source URL/name/type, authority, retrieval timestamp and evidence note
- validity/freshness where the fact can change
- reviewer/status and confidence rationale

Do not invent opening hours, price, route duration, distance, safety status, accessibility, operating season or weather. Unknown values remain NULL/unknown rather than plausible-looking filler.

## Import and QA controls

- Validate source files/content in an isolated import-preparation step first; then import transactionally and record the batch key, checksums, and row counts in `operations.dataset_import_batches`. No separate SQL staging table is currently part of the 30-table MVP schema.
- Validate required fields, unique canonical identity, foreign keys, coordinate ranges and geospatial validity.
- Reject duplicate records or send them to a reconciliation queue; do not silently merge uncertain identities.
- Store every document with source provenance and content hash.
- Verify the expected number of accepted, rejected and quarantined rows after every import.
- Synthetic fixtures are allowed only in Development/Test; a Production release gate must reject any `record_origin='synthetic_fixture'` or `is_synthetic=true` rows in user-visible destination/recommendation data.

## Production data gate

Before pilot exposure, define a minimum verified destination dataset with:

- source-level evidence for every published destination
- verified province/city/coordinates
- duplicate and category QA
- required safety/accessibility caveats where applicable
- automated query tests that confirm only verified active rows are eligible

The 15 unverified supplied records, 12 QA fixtures, and 10 UNESCO records still in `needs_review` do not satisfy this gate. The UNESCO batch proves the source/provenance and ingestion path, not launch readiness or adequate geographic coverage.
