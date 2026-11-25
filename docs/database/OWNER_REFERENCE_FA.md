# راهنمای مالک برای فرم‌ها و مرجع پایگاه‌دادهٔ رهگرد

> این فهرست از snapshot پالایش‌شدهٔ فقط‌خواندنیِ یک پایگاه‌داده ساخته شده است؛ آن را به‌عنوان موجودی کل VPS یا تأیید معماری تلقی نکنید.

- منبع تاریخی: `rahgard_pilot_vps_staging`، PostgreSQL `17.11 (Debian 17.11-1.pgdg13+2)`، snapshot `2026-11-24T11:28:13Z`.
- نسخهٔ برنامهٔ مشاهده‌شده: `9b5b07d0786578abdfac56848baf3c6d1260832e`؛ snapshot live تا مهاجرت ۰۰۲۳ است و migrations ۰۰۲۴–۰۰۲۶ را شامل نمی‌شود.
- پوشش این snapshot: 101 relation، از جمله viewها؛ تعداد descriptionهای glossary و occurrenceها را با تعداد پارامترهای منطقی محصول یکی نگیرید.
- نسخهٔ ایزولهٔ rehearse‌شده: migrations ۰۰۲۴–۰۰۲۶ روی clone بازیابی‌شده اجرا شد. جدول‌های افزوده‌شده در این نسخه فقط در بخش «تغییرات rehearseشده» معرفی می‌شوند؛ زنده تلقی نمی‌شوند.

## مسیرهای واقعی کاربر و پوشش فرم/API

| نقش | فرم/مسیر در UI | جدول‌ها و viewهای اصلی | مسیر API/کد و حدود مجوز |
|---|---|---|---|
| مالک/بازبین پلتفرم | `/admin` در `frontend/src/admin/AdminControlCenter.tsx`؛ MFA در `PlatformAdminMfaPanel.tsx` | `partner.platform_grants`, `partner.review_events`, `partner.organizations`, `identity.catalogue_review_grants`, `knowledge.destination_candidates`, viewهای انتشار | `backend/app/api/admin.py`, `backend/app/api/partners.py`, `backend/app/api/platform_admin_mfa.py`; فقط مجوز صریح، step-up برای اقدام ممتاز و audit؛ AI-provider admin در VPS فعال نیست. |
| نمایندهٔ شرکت | `/partners` در `frontend/src/partners/PartnerWorkspace.tsx` | `partner.organizations`, `memberships`, `services`, `service_destinations`, `schedules`, `offers`, `prices`, `availability_snapshots`, viewهای eligible/share | `backend/app/api/partners.py`; هر نوشتن در محدودهٔ سازمان عضو، RLS/authorization؛ فرم عمومی برای OTP، session، grant و audit وجود ندارد. |
| مسافر | workspace مسافر در `frontend/src/trip/TravelerJourney.tsx` | `travel.trips`, `trip_constraints`, `trip_interests`, `trip_requirement_revisions`, `conversation.conversations/messages`, `travel.itineraries/stops`, share/revision tables | `backend/app/api/traveler.py`, `assistant.py`, `recommendations.py`, `partners.py`; مالکیت مسافر و رضایت جداگانه برای اشتراک با شرکت. |
| اپراتور استقرار | shell/Compose، نه فرم عمومی | `system.schema_migrations`, `operations.*`, marker و role grants | اسکریپت‌های کنترل‌شدهٔ استقرار؛ هرگز از فرم عمومی یا API مسافر قابل‌نوشتن نیستند. |

## پوشش فیلدها و محدودیت معنا

- مرجع کامل occurrenceها: [ماتریس ستون‌ها](architecture-usage/column_occurrence_matrix.csv)، [lineage viewها](architecture-usage/view_column_lineage.csv)، [وابستگی API](architecture-usage/api_dependency_map.csv)، [تصمیم relationها](architecture-usage/object_decision_matrix.csv) و [گزارش معماری/مصرف](architecture-usage/ARCHITECTURE_AND_USAGE_REVIEW.md).
- baseline تاریخی: ۱۰۱ relation، ۱٬۱۰۶ occurrence، ۲۳۰ description موجود و ۸۷۶ شکاف glossary. طبقه‌بندی شکاف‌ها: ۶۰۵ occurrence پایهٔ برنامه، ۱۰۲ سیستم/عملیات، ۱۵۰ view مشتق و ۱۹ PostGIS. ۸۷۶ نیاز تازهٔ کسب‌وکار نیست.
- تصمیم relationها: ۶۱ KEEP، ۳۷ INVESTIGATE، ۳ EXTENSION-MANAGED. این وضعیت‌ها حفاظت/تحقیق را نشان می‌دهند، نه تأیید نهایی ضرورت معماری.
- هر فیلد بدون شاهد در `field_descriptions.json` صریحاً نامشخص می‌ماند. برای viewها به expression مبدأ ارجاع دهید؛ برای PostGIS به مستندات رسمی extension؛ نام یا نوع SQL به‌تنهایی معنای محصول را ثابت نمی‌کند.
- فرق فرم‌پذیر با خودکار/سیستمی: اطلاعات پایهٔ سازمان، خدمت، برنامه و قیمت فقط از فرم/API tenant مجاز نوشته می‌شوند؛ session، OTP، محدودیت نرخ، مهاجرت، grant و audit فقط سامانه/اپراتور کنترل‌شده را دارند.

## تغییرات rehearseشدهٔ ۰۰۲۴–۰۰۲۶ (فقط clone ایزوله)

- ۰۰۲۴: تغییر مجاز vocabulary و policy درج در `partner.review_events`; بدون grant بازبین و بدون تغییر دادهٔ موجود.
- ۰۰۲۵: افزودن `partner.platform_grant_events` و تابع تجمیع شمار مجوز؛ check constraint grant توسعه یافت.
- ۰۰۲۶: افزودن `identity.platform_admin_mfa`, `identity.platform_admin_step_up`, `identity.platform_admin_mfa_events`، policyهای RLS و توابع audit/capability. هیچ حساب بازبین یا MFA secret در clone ساخته نشد.
- شاهد دقیق: [بازیابی و rehearsal](../operations/evidence/issue27/R4-restore-migrations-2026-11-25.json) و [تغییرات ستون‌های ۰۰۲۴–۰۰۲۶](REHEARSED_0024_0026_FIELD_REFERENCE.md). این اسناد schema زنده را تغییر نمی‌دهند.

## فهرست همهٔ relationهای snapshot با پیوند به سند جزئی

### `conversation`

- [`assistant_turns`](live-schema/rahgard_pilot_vps_staging-6b3312d4/conversation-8b34dbc2/tables/assistant_turns-f6adb88f.md) — 12 occurrence؛ 2 بدون شرح baseline; r.
- [`conversations`](live-schema/rahgard_pilot_vps_staging-6b3312d4/conversation-8b34dbc2/tables/conversations-5c0dc939.md) — 13 occurrence؛ 7 بدون شرح baseline; r.
- [`messages`](live-schema/rahgard_pilot_vps_staging-6b3312d4/conversation-8b34dbc2/tables/messages-f5cccfb7.md) — 15 occurrence؛ 6 بدون شرح baseline; r.

### `geo`

- [`admin_area_aliases`](live-schema/rahgard_pilot_vps_staging-6b3312d4/geo-e81935fb/tables/admin_area_aliases-69b365be.md) — 10 occurrence؛ 10 بدون شرح baseline; r.
- [`admin_area_releases`](live-schema/rahgard_pilot_vps_staging-6b3312d4/geo-e81935fb/tables/admin_area_releases-b7a694e4.md) — 11 occurrence؛ 11 بدون شرح baseline; r.
- [`admin_areas`](live-schema/rahgard_pilot_vps_staging-6b3312d4/geo-e81935fb/tables/admin_areas-3e2eda73.md) — 13 occurrence؛ 13 بدون شرح baseline; r.

### `identity`

- [`auth_rate_limits`](live-schema/rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/auth_rate_limits-ab60a2e5.md) — 4 occurrence؛ 4 بدون شرح baseline; r.
- [`catalogue_review_grants`](live-schema/rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/catalogue_review_grants-2d028f1d.md) — 6 occurrence؛ 6 بدون شرح baseline; r.
- [`otp_challenges`](live-schema/rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/otp_challenges-1969c61e.md) — 13 occurrence؛ 13 بدون شرح baseline; r.
- [`staging_auth_limits`](live-schema/rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/staging_auth_limits-1f09c6f7.md) — 4 occurrence؛ 4 بدون شرح baseline; r.
- [`staging_invites`](live-schema/rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/staging_invites-0d54e43c.md) — 6 occurrence؛ 6 بدون شرح baseline; r.
- [`staging_password_credentials`](live-schema/rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/staging_password_credentials-617738de.md) — 6 occurrence؛ 6 بدون شرح baseline; r.
- [`user_consents`](live-schema/rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/user_consents-7a7aebd6.md) — 10 occurrence؛ 10 بدون شرح baseline; r.
- [`user_preferences`](live-schema/rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/user_preferences-7e378789.md) — 11 occurrence؛ 11 بدون شرح baseline; r.
- [`users`](live-schema/rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/users-7dfb4cf6.md) — 10 occurrence؛ 10 بدون شرح baseline; r.
- [`verified_phones`](live-schema/rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/verified_phones-66f7e274.md) — 4 occurrence؛ 4 بدون شرح baseline; r.
- [`web_sessions`](live-schema/rahgard_pilot_vps_staging-6b3312d4/identity-689f6a62/tables/web_sessions-a075ea48.md) — 10 occurrence؛ 10 بدون شرح baseline; r.

### `integration`

- [`chat_daily_global_budget`](live-schema/rahgard_pilot_vps_staging-6b3312d4/integration-eb92cc52/tables/chat_daily_global_budget-27b4bbd7.md) — 2 occurrence; r.
- [`chat_daily_user_budget`](live-schema/rahgard_pilot_vps_staging-6b3312d4/integration-eb92cc52/tables/chat_daily_user_budget-6c98bd64.md) — 3 occurrence; r.
- [`external_links`](live-schema/rahgard_pilot_vps_staging-6b3312d4/integration-eb92cc52/tables/external_links-b9ab75bd.md) — 9 occurrence; r.
- [`outbound_clicks`](live-schema/rahgard_pilot_vps_staging-6b3312d4/integration-eb92cc52/tables/outbound_clicks-19c8afdc.md) — 9 occurrence; r.

### `knowledge`

- [`active_embedding_spaces`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/active_embedding_spaces-1b30f488.md) — 11 occurrence; v.
- [`catalogue_publication_events`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/catalogue_publication_events-c4a82f50.md) — 7 occurrence؛ 7 بدون شرح baseline; r.
- [`chunk_embeddings`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/chunk_embeddings-f9d8072c.md) — 6 occurrence؛ 6 بدون شرح baseline; r.
- [`culinary_item_sources`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/culinary_item_sources-c8ea7adb.md) — 14 occurrence؛ 14 بدون شرح baseline; r.
- [`culinary_knowledge_items`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/culinary_knowledge_items-39e2713d.md) — 21 occurrence؛ 21 بدون شرح baseline; r.
- [`destination_access_points`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_access_points-0c087cc8.md) — 14 occurrence؛ 14 بدون شرح baseline; r.
- [`destination_aliases`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_aliases-75309a16.md) — 10 occurrence؛ 10 بدون شرح baseline; r.
- [`destination_candidate_evidence`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_candidate_evidence-92151fb7.md) — 11 occurrence؛ 11 بدون شرح baseline; r.
- [`destination_candidate_reviews`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_candidate_reviews-4cf36b04.md) — 10 occurrence؛ 10 بدون شرح baseline; r.
- [`destination_candidates`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_candidates-6a9824e7.md) — 21 occurrence؛ 21 بدون شرح baseline; r.
- [`destination_categories`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_categories-6ec43aad.md) — 6 occurrence؛ 6 بدون شرح baseline; r.
- [`destination_category_map`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_category_map-2776bfb3.md) — 5 occurrence؛ 5 بدون شرح baseline; r.
- [`destination_claim_evidence`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_claim_evidence-c4355517.md) — 23 occurrence؛ 23 بدون شرح baseline; r.
- [`destination_enrichment_proposal_sources`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_enrichment_proposal_sources-7ce2e624.md) — 14 occurrence؛ 14 بدون شرح baseline; r.
- [`destination_enrichment_proposals`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_enrichment_proposals-253b2149.md) — 16 occurrence؛ 16 بدون شرح baseline; r.
- [`destination_localizations`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_localizations-0eb8da97.md) — 11 occurrence؛ 11 بدون شرح baseline; r.
- [`destination_operational_assertions`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_operational_assertions-5805af5e.md) — 17 occurrence؛ 17 بدون شرح baseline; r.
- [`destination_sources`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_sources-52eec045.md) — 7 occurrence؛ 7 بدون شرح baseline; r.
- [`destination_tags`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_tags-fe7b7ef7.md) — 2 occurrence؛ 2 بدون شرح baseline; r.
- [`destination_visit_duration_evidence`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destination_visit_duration_evidence-5579d9f3.md) — 13 occurrence؛ 13 بدون شرح baseline; r.
- [`destinations`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/destinations-1af0500e.md) — 28 occurrence؛ 28 بدون شرح baseline; r.
- [`embedding_spaces`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/embedding_spaces-f7a9b58b.md) — 12 occurrence؛ 12 بدون شرح baseline; r.
- [`knowledge_chunks`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/knowledge_chunks-c1de8a43.md) — 10 occurrence؛ 10 بدون شرح baseline; r.
- [`knowledge_documents`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/knowledge_documents-c8a3d0bd.md) — 18 occurrence؛ 18 بدون شرح baseline; r.
- [`knowledge_sources`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/knowledge_sources-059f8744.md) — 10 occurrence؛ 10 بدون شرح baseline; r.
- [`production_chunk_embeddings`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_chunk_embeddings-c270ebe9.md) — 14 occurrence; v.
- [`production_culinary_knowledge`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_culinary_knowledge-bb2646f2.md) — 9 occurrence; v.
- [`production_destination_categories`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_destination_categories-afee998c.md) — 5 occurrence; v.
- [`production_destination_category_map`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_destination_category_map-389c0e66.md) — 4 occurrence; v.
- [`production_destination_claim_evidence`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_destination_claim_evidence-c36d86cb.md) — 26 occurrence; v.
- [`production_destination_sources`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_destination_sources-9f650eaa.md) — 11 occurrence; v.
- [`production_destination_tags`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_destination_tags-965cf515.md) — 2 occurrence; v.
- [`production_destinations`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_destinations-40eadf41.md) — 27 occurrence; v.
- [`production_retrieval_chunks`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_retrieval_chunks-5c690ae9.md) — 19 occurrence; v.
- [`production_retrieval_documents`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/views/production_retrieval_documents-7946c5ed.md) — 22 occurrence; v.
- [`source_candidate_reviews`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/source_candidate_reviews-447c5344.md) — 9 occurrence؛ 9 بدون شرح baseline; r.
- [`source_candidates`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/source_candidates-96f26cbd.md) — 17 occurrence؛ 17 بدون شرح baseline; r.
- [`source_registry_registration_events`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/source_registry_registration_events-091879f4.md) — 10 occurrence؛ 10 بدون شرح baseline; r.
- [`source_verification_reviews`](live-schema/rahgard_pilot_vps_staging-6b3312d4/knowledge-e0f89587/tables/source_verification_reviews-cc624d8f.md) — 11 occurrence؛ 11 بدون شرح baseline; r.

### `operations`

- [`ai_model_calls`](live-schema/rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/ai_model_calls-48e13f37.md) — 12 occurrence; r.
- [`audit_events`](live-schema/rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/audit_events-14cca081.md) — 9 occurrence; r.
- [`dataset_import_batches`](live-schema/rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/dataset_import_batches-df7cf9dc.md) — 8 occurrence; r.
- [`dataset_import_files`](live-schema/rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/dataset_import_files-904901ca.md) — 15 occurrence; r.
- [`feedback`](live-schema/rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/feedback-59bda3f8.md) — 10 occurrence; r.
- [`private_pilot_geo_approvals`](live-schema/rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/private_pilot_geo_approvals-b1ba5af2.md) — 9 occurrence; r.
- [`private_pilot_geo_authorizations`](live-schema/rahgard_pilot_vps_staging-6b3312d4/operations-74de07c4/tables/private_pilot_geo_authorizations-4ca96d93.md) — 17 occurrence; r.

### `partner`

- [`availability_snapshots`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/availability_snapshots-ba838abd.md) — 14 occurrence; r.
- [`branches`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/branches-dce19053.md) — 12 occurrence; r.
- [`invitations`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/invitations-33cd5e40.md) — 10 occurrence; r.
- [`memberships`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/memberships-5050625e.md) — 9 occurrence; r.
- [`offers`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/offers-92ab364e.md) — 13 occurrence; r.
- [`organizations`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/organizations-f8a665a9.md) — 15 occurrence; r.
- [`platform_grants`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/platform_grants-a4a5df9a.md) — 6 occurrence; r.
- [`prices`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/prices-fe81f939.md) — 14 occurrence; r.
- [`review_events`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/review_events-3b16bd9c.md) — 9 occurrence; r.
- [`schedules`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/schedules-6e9a1ab2.md) — 12 occurrence; r.
- [`service_destinations`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/service_destinations-210419ff.md) — 7 occurrence; r.
- [`service_localizations`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/service_localizations-51c8d7f8.md) — 9 occurrence; r.
- [`services`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/services-ef1c4b45.md) — 12 occurrence; r.
- [`share_eligible_organizations`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/views/share_eligible_organizations-ce33f94c.md) — 3 occurrence; v.
- [`traveler_request_inbox`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/traveler_request_inbox-e77d4232.md) — 6 occurrence; r.
- [`traveler_request_revisions`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/traveler_request_revisions-e7bb178d.md) — 11 occurrence; r.
- [`traveler_request_shares`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/traveler_request_shares-27951838.md) — 9 occurrence; r.
- [`trip_company_responses`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/trip_company_responses-f5079928.md) — 18 occurrence; r.
- [`verification_cases`](live-schema/rahgard_pilot_vps_staging-6b3312d4/partner-7f3fa48c/tables/verification_cases-ccd9ee8c.md) — 11 occurrence; r.

### `public`

- [`geography_columns`](live-schema/rahgard_pilot_vps_staging-6b3312d4/public-efa1f375/views/geography_columns-d4370c1b.md) — 7 occurrence; v.
- [`geometry_columns`](live-schema/rahgard_pilot_vps_staging-6b3312d4/public-efa1f375/views/geometry_columns-db35ba0f.md) — 7 occurrence; v.
- [`rahgard_private_pilot_marker`](live-schema/rahgard_pilot_vps_staging-6b3312d4/public-efa1f375/tables/rahgard_private_pilot_marker-64e06a2e.md) — 1 occurrence; r.
- [`spatial_ref_sys`](live-schema/rahgard_pilot_vps_staging-6b3312d4/public-efa1f375/tables/spatial_ref_sys-6b0f8c39.md) — 5 occurrence; r.

### `recommendation`

- [`recommendation_requests`](live-schema/rahgard_pilot_vps_staging-6b3312d4/recommendation-dbfe9375/tables/recommendation_requests-b58aca54.md) — 10 occurrence؛ 10 بدون شرح baseline; r.
- [`recommendation_score_components`](live-schema/rahgard_pilot_vps_staging-6b3312d4/recommendation-dbfe9375/tables/recommendation_score_components-e3b855a1.md) — 10 occurrence؛ 10 بدون شرح baseline; r.
- [`recommendations`](live-schema/rahgard_pilot_vps_staging-6b3312d4/recommendation-dbfe9375/tables/recommendations-f9b89ad4.md) — 12 occurrence؛ 12 بدون شرح baseline; r.

### `system`

- [`schema_migrations`](live-schema/rahgard_pilot_vps_staging-6b3312d4/system-bbc5e661/tables/schema_migrations-26bec784.md) — 3 occurrence; r.

### `travel`

- [`itineraries`](live-schema/rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/itineraries-03a4100d.md) — 12 occurrence؛ 12 بدون شرح baseline; r.
- [`itinerary_stops`](live-schema/rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/itinerary_stops-5025eb44.md) — 13 occurrence؛ 13 بدون شرح baseline; r.
- [`provisional_itineraries`](live-schema/rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/provisional_itineraries-db7c0fe6.md) — 11 occurrence؛ 11 بدون شرح baseline; r.
- [`trip_constraints`](live-schema/rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/trip_constraints-a41e8f02.md) — 11 occurrence؛ 11 بدون شرح baseline; r.
- [`trip_interests`](live-schema/rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/trip_interests-7b9a4366.md) — 7 occurrence؛ 7 بدون شرح baseline; r.
- [`trip_requirement_revisions`](live-schema/rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/trip_requirement_revisions-8de20de1.md) — 7 occurrence؛ 7 بدون شرح baseline; r.
- [`trips`](live-schema/rahgard_pilot_vps_staging-6b3312d4/travel-0209442e/tables/trips-57866688.md) — 26 occurrence؛ 26 بدون شرح baseline; r.

## تغییر وضعیت پس از rehearse تا production

در snapshot آخرِ فقط‌خواندنی، VPS هنوز ledger تا ۰۰۲۳ داشت؛ clone rehearsal تا ۰۰۲۶ رفت. DDL، secrets، grants، داده یا سرویس live در این ماموریت تغییر نکرده‌اند. برای تغییر live به مجوز جداگانهٔ دقیق نیاز است.
