# مشاهدهٔ فقط‌خواندنی پایگاه زنده — ۲۰۲۶-۱۱-۲۴

## هویت و روش

- زمان snapshot کاتالوگ: `2026-11-24T06:58:13Z`.
- پایگاه بررسی‌شده: `rahgard_pilot_vps_staging`، PostgreSQL `17.11`؛ نقش کاتالوگ `ai_tourism_app`.
- منبع: `pg_catalog` در `BEGIN READ ONLY`، با محدودیت timeout. هیچ ردیف گفت‌وگو، حساب، درخواست شرکت، سفر، نشست یا مدرک خصوصی خوانده نشد.
- snapshot شامل ۱۰۱ جدول/View در ۱۱ schema است. این بررسی فقط همان دیتابیس نام‌برده را پوشش می‌دهد؛ سایر دیتابیس‌های VPS در این نوبت شمارش/اتصال‌سنجی نشدند. فهرست هیچ دیتابیس دیگر را از `databases_inaccessible=[]` استنتاج نکنید.
- برای فهم release، نام image و label `org.opencontainers.image.revision` هر دو container API/Web روی `9b5b07d0786578abdfac56848baf3c6d1260832e` بودند. فایل `RELEASE_COMMIT` در مسیر current مقدار متفاوت `5e2664fb51e18f52549aa37a8b5793e12ace09b2` داشت؛ آن marker با image revision فعلی سازگار نیست و باید در عملیات انتشار بعدی رفع/توضیح داده شود. این مستندات ادعای همگامی checkout، GitHub و VPS نمی‌کنند.
- volume زندهٔ PostgreSQL فقط‌خواندنی به‌عنوان `rahgard_staging_pgdata` روی `/var/lib/postgresql/data` مشاهده شد. کانتینر دیتابیس در شبکهٔ خصوصی `rahgard-staging_staging_private` است.

## Migration ledger

خواندن ledger با نقش محدود برنامه به schema `system` مجاز نبود؛ تلاش با آن نقش با `permission denied for schema system` تمام شد. سپس فقط query صریح زیر در transaction فقط‌خواندنی با rollback و نقش مالک دیتابیس اجرا شد: `SELECT migration_id, sha256 FROM system.schema_migrations ORDER BY migration_id`. نتیجه ۲۲ ردیف است؛ آخرین migration `0023_partner_trip_responses`. هیچ migration اجرا نشد.

| Migration | SHA-256 |
|---|---|
| 0000_legacy_tourism_points_baseline | `0f09e1a1b003e76b67134cc5e1f74b37fa5a0a89f62e4b4ecd534c14c823314f` |
| 0001_core_schema | `00b4d8616f4e1622191e982c4a388feb20c41a6e46778ce0770c40339a48063e` |
| 0002_synthetic_knowledge_seed | `ec6ea33a5f3c9e8b902050015bd24672e25e112f7852bc7d936d48cc6d944ec7` |
| 0003_synthetic_e2e_seed | `9ef84f906ba33988ac3cfaa176856c1dbc1f9003060c60dd90c60359e2066383` |
| 0004_app_role_grants | `b3b9903dcfed60417aeb8fcd690c34fbc933477491f908a3b02fc80c2fc8b6a7` |
| 0005_verified_unesco_destination_seed | `9ad5523af9733da845df8c8c090862e29d877b72ac3951053cb0c3580e9a3218` |
| 0006_verified_unesco_destination_seed_batch2 | `c0a935c7c7b17f085107643a9ea0911cac4378adb945cdf3348146efc56ada63` |
| 0007_shiraz_dalahoo_wikipedia_dataset_v1 | `b95891fe6de229ea51a2cc446fc0e5f0cb03dbe3e7c34914a4becf67ee78a7c2` |
| 0008_authentication_foundation | `bba9a0bb08e7c86429ebb67bda443aeca268f47d41d10d8ee09bd188127a23e3` |
| 0009_traveler_core | `8e77827f318e2acd3ccc5be020e5229f989cb4bbfadc73de75ed109a7750a91b` |
| 0010_task31_content_privacy_full_itinerary | `f9c83fefbbc8f48b362ebf42f8ea4e2558192657d4f6f1dd804a69aa39529db5` |
| 0011_internal_chat_turns | `0d325f3968932fa06a6aef38c92b980b41e72dffd62711933f205ca4b8dce927` |
| 0012_task5_published_claim_evidence | `cfce395ed1f2bf3dc01f7b42e47d64434a32bb2638e4e30ff27da5b4f22dfa9a` |
| 0013_private_pilot_geo_audit | `c5db92c206faad0af63b0789d5445894b8872d511306c11c387d1c9cdd978591` |
| 0016_staging_invitation_auth | `702b113f2a26856836d1eb64320cb13c97626e61f588244faa3923ae23b03016` |
| 0017_provisional_itineraries | `4576f4e1390de68345866e0d99815d1644833f577266539d47075da26776de6d` |
| 0018_national_catalogue_ingestion | `f5fc0cb3e3fcf61b36a5d21f9c98c3d75e04581cb19d4e22ad1754d53480dd36` |
| 0019_partner_workspace | `8f7c745e128faf0d9d91bf808159367a7a2636ac31b4544147619a9af751dd56` |
| 0020_archive_candidate_publication | `b6822a3401cef3f7ac8c85ce0577eb71d0373bc34bf4ec2d8c65b0a812f13326` |
| 0021_postgis_security_definer_publication | `bc0b6abb335549ddff91a811aeeca30bc5ba75d3e3f5f3fe81f7ded4b3bee650` |
| 0022_traveler_company_requests | `e6b7db49abc0ff76c2620b2cc8d5dded0f4255f8533efd20bd5b402a0ba57eda` |
| 0023_partner_trip_responses | `deef8c5016f26aa646b9ff22346fad4ade3c6780ff447f701aa9e8a8e28571ac` |

## Public aggregates

در transaction فقط‌خواندنی با نقش `ai_tourism_app`، فقط شمارش viewهای عمومی (نه payload ردیف‌ها) انجام شد:

- `knowledge.production_destinations`: **۰** مقصد عمومی.
- `partner.share_eligible_organizations`: **۰** سازمان واجد شرایط اشتراک.

این شمارش‌ها دربارهٔ دادهٔ خصوصی یا تعداد همهٔ حساب‌ها/سازمان‌ها نیستند.

## پوشش معنا و محدودیت‌های مستندات

- `manifest.json` برای ۱۰۱ شیء فایل مستقل دارد. نوع واقعی ستون، nullable/default امن، قیود، index، RLS policy و trigger از snapshot ثبت شده است.
- پس از اعمال واژه‌نامهٔ فعلی، **۸۷۶ فیلد از نظر شرح کسب‌وکاری هنوز نیازمند بررسی** هستند. این فیلدها unknown باقی می‌مانند؛ نام ستون به‌تنهایی معنی قطعی تلقی نشده است.
- نقش `ai_tourism_app` برای استخراج metadata، نقش اختصاصی read-only نیست؛ transaction به‌صورت read-only بوده است. دسترسی به schema مهاجرت برای این نقش بسته است.
- Migration `0024_partner_review_audit_actions.sql` فقط در PostgreSQL 17 موقت آزمایش شد؛ روی VPS اجرا نشده است. بنابراین خطای RLS ثبت audit `verification_case` در acceptance تولیدی هنوز رفع نشده است.
- هیچ تغییر زنده در schema، داده، container، volume، Nginx یا انتشار کاتالوگ انجام نشد.
