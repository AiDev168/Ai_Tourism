# Eram Garden coordinate review

**Status:** review proposal only; no dataset or database coordinate was changed.

The current curated dataset coordinate is `29.63583, 52.52528`. The UNESCO nomination file lists Bagh-e Eram at `29° 38′ 10.03″ N, 52° 31′ 31″ E`, equivalent to approximately `29.6361194, 52.5252778`.

The latitude difference is `0.0002894°` (about 32.1 m); the longitude difference is `0.0000022°` (about 0.2 m at this latitude). The straight-line discrepancy is approximately **32 metres**. This is consistent with two slightly different reference points, but the documents alone do not establish which coordinate is the entrance or exact surveyed property centroid.

**Editorial proposal:** review `property_reference` as the semantic coordinate role for the UNESCO nomination point, because the UNESCO coordinate identifies the nominated property. Confirm against the nomination map/property boundary and an authoritative geospatial source before changing the curated dataset. Do not alter Migration 0007 or apply a coordinate correction to any shared database.

Sources: [UNESCO nomination file 1372](https://whc.unesco.org/uploads/nominations/1372.pdf) (Bagh-e Eram geographical coordinates); local dataset value in `engineering/database-prep/sql/007_shiraz_dalahoo_wikipedia_dataset_v1.sql`.
