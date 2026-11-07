# شمارش دقیق مورد انتظار دیتابیس — وضعیت‌های 0006 و 0007

این سند دو وضعیت معتبر و دقیق دیتابیس را تعریف می‌کند. وضعیت فعلی دیتابیس Development مشترک مالک، Migration 0006 با ۳۰ جدول و ۴۱۹ ردیف است؛ Migration 0007 هنوز روی آن اجرا نشده است. وضعیت 0007 با ۶۹۵ ردیف یک ارتقای اختیاری است و فقط پس از تأیید جداگانهٔ مالک مجاز است. تست `sql/tests/001_schema_seed_invariants.sql` و گزارش `sql/reports/final_row_counts.sql` وضعیت را از Migration ledger تشخیص می‌دهند و تعداد دقیق همان وضعیت را بررسی می‌کنند. هر اختلاف باید Fail شود؛ تعداد مورد انتظار هرگز برای سبز شدن تست به‌صورت خودکار تغییر نمی‌کند.

**وضعیت A — Migration 0006:** ۳۰ جدول / ۴۱۹ ردیف؛ Migration 0007 غایب.

**وضعیت B — Migration 0007:** ۳۰ جدول / ۶۹۵ ردیف؛ دقیقاً ۲۲ مقصد جدید و تکمیل یک ردیف مراغه، ۱۸ منبع، ۵۱ رابطهٔ مقصد/منبع، ۱۲۰ برچسب خالص، ۱۷ نگاشت دسته، ۲۳ سند و ۲۳ Chunk، یک Batch و یک سابقهٔ Migration افزوده شده است. صفرهای Embedding، کلیک خروجی، LLM و Audit عمدی هستند.

| Schema | Table | 0006 baseline | 0007 Shiraz |
|---|---|---:|---:|
| `identity` | `users` | 1 | 1 |
| `identity` | `user_consents` | 1 | 1 |
| `identity` | `user_preferences` | 3 | 3 |
| `conversation` | `conversations` | 1 | 1 |
| `conversation` | `messages` | 4 | 4 |
| `travel` | `trips` | 1 | 1 |
| `travel` | `trip_constraints` | 3 | 3 |
| `travel` | `trip_interests` | 3 | 3 |
| `travel` | `itineraries` | 1 | 1 |
| `travel` | `itinerary_stops` | 6 | 6 |
| `knowledge` | `knowledge_sources` | 40 | 58 |
| `knowledge` | `destinations` | 44 | 66 |
| `knowledge` | `destination_sources` | 65 | 116 |
| `knowledge` | `destination_tags` | 88 | 208 |
| `knowledge` | `destination_categories` | 12 | 12 |
| `knowledge` | `destination_category_map` | 30 | 47 |
| `knowledge` | `knowledge_documents` | 29 | 52 |
| `knowledge` | `knowledge_chunks` | 58 | 81 |
| `knowledge` | `embedding_spaces` | 0 | 0 |
| `knowledge` | `chunk_embeddings` | 0 | 0 |
| `recommendation` | `recommendation_requests` | 1 | 1 |
| `recommendation` | `recommendations` | 3 | 3 |
| `recommendation` | `recommendation_score_components` | 9 | 9 |
| `integration` | `external_links` | 3 | 3 |
| `integration` | `outbound_clicks` | 0 | 0 |
| `operations` | `feedback` | 1 | 1 |
| `operations` | `ai_model_calls` | 0 | 0 |
| `operations` | `audit_events` | 0 | 0 |
| `operations` | `dataset_import_batches` | 5 | 6 |
| `system` | `schema_migrations` | 7 | 8 |

| **TOTAL** | **30 project-owned tables** | **419** | **695** |

The `identity.users` value above is the immutable synthetic QA identity seed count, not a cap on real users. Repeatable validation counts only that synthetic seed row in the exact seed manifest and reports non-synthetic users separately. After Migration 0008, OTP challenges, verified-phone evidence, web sessions, and rate-limit rows are runtime data and may be non-empty. Validation checks their schema, permissions, provenance/time boundary, and migration state; it does not require them to remain empty. The `420` / `696` totals shown for 0006+0008 / 0007+0008 describe the clean post-migration baseline before runtime authentication activity.

## ترکیب داده‌ها

- **وضعیت فعلی دیتابیس مشترک مالک:** Migration 0006، ۳۰ جدول و ۴۱۹ ردیف؛ Migration 0007 در ledger وجود ندارد و این سند یا Validator آن را اعمال نمی‌کند.
- **وضعیت اختیاری پس از 0007:** ۳۰ جدول و ۶۹۵ ردیف؛ فقط با opt-in صریح پس از تأیید جداگانهٔ مالک. برای دیتابیس موجود 0006، Initialize در حالت پیش‌فرض باید پیش از هر Migration متوقف شود.

- **۱۴ مقصد قدیمی باقی‌مانده از پروژه:** از `database/tourism_points.sql`؛ همگی `needs_review`، منبع اولیه pending و بدون مختصات تأییدشده. هویت هر ۱۵ ردیف اصلی حفظ شده؛ رصدخانهٔ مراغه یکی از همان ردیف‌هاست که با Migration 0007 منبع‌دار شد و وضعیتش همچنان `needs_review` است.

## افزودن اختیاری زیرساخت احراز هویت — Migration 0008

Migration `0008_authentication_foundation` فقط جداول OTP، شواهد شمارهٔ تأییدشده، نشست‌های وب و محدودکنندهٔ نرخ را به‌صورت افزایشی می‌سازد. هیچ شمارهٔ قدیمی را تأیید نمی‌کند و هیچ دادهٔ ورود/نشستی seed نمی‌کند.

| وضعیت معتبر | جداول پروژه | ردیف‌های کل | وضعیت پیشین |
|---|---:|---:|---|
| `0006-auth` — ledger شامل 0000–0006 و 0008 | ۳۴ | ۴۲۰ | ۰۰۰۶ / ۴۱۹ به‌علاوهٔ یک ledger row |
| `0007-auth` — ledger شامل 0000–0008 | ۳۴ | ۶۹۶ | ۰۰۰۷ / ۶۹۵ به‌علاوهٔ یک ledger row |

در هر دو حالت چهار جدول جدید `identity.otp_challenges`، `identity.verified_phones`، `identity.web_sessions` و `identity.auth_rate_limits` در شروع خالی هستند. اعتبارسنجی lifecycle فقط این چهار ترکیب دقیق ledger را می‌پذیرد: 0006، 0007، 0006+0008 و 0007+0008. هر حالت ناقص یا شمارش متفاوت fail-closed می‌شود. اعمال Migration 0008 روی دیتابیس موجود به opt-in جداگانهٔ `-ApplyAuthenticationMigrationToExistingDatabase` نیاز دارد؛ این opt-in مجوزی برای دیتابیس مشترک محسوب نمی‌شود.
- **۱۲ مقصد QA مصنوعی + ۱۲ سند + ۲۴ Chunk:** صرفاً برای تست؛ همه با `is_synthetic=true`، منشأ `synthetic_fixture` و وضعیت `test_only`.
- **۴۰ مقصد منبع‌دار و در انتظار بازبینی:** ۱۷ اثر میراث جهانی و ۲۳ موجودیت پایلوت شیراز/مراغه. همه `verified_external`, غیرمصنوعی و `needs_review` هستند و در Viewهای Production/RAG منتشر نمی‌شوند.
- **۵۸ منبع اطلاعات:** ۴۰ منبع Baseline و ۱۸ منبع ثبت‌شده در Shiraz Dataset.
- **۱۱۶ پیوند مقصد/منبع:** ۶۵ پیوند Baseline و ۵۱ رابطهٔ جدید پایلوت (شامل روابط discovery).
- **۲۰۸ برچسب مقصد:** ۸۸ برچسب Baseline و ۱۲۰ برچسب خالص جدید، پس از حذف دو برچسب بی‌پشتوانهٔ مراغه.
- **۴۷ نگاشت دسته‌بندی:** ۳۰ نگاشت Baseline و ۱۷ نگاشت جدید برای مقصدهای پایلوت و رصدخانهٔ مراغه.
- **۵۲ سند فارسی + ۸۱ Chunk:** ۲۹/۵۸ در Baseline و ۲۳/۲۳ جدید. داده‌های جدید یک Chunk برای هر سند دارند.
- **یک گراف E2E مصنوعی:** کاربر، رضایت، ترجیحات، مکالمه و پیام‌ها، سفر و محدودیت‌ها، پیشنهادها و امتیازها، برنامه سفر و بازخورد.
- **۶ Batch ورود داده:** پنج Baseline و یک Shiraz dataset batch.
- **۸ سابقه Migration:** یک Baseline مربوط به SQL قدیمی و هفت Migration کنترل‌شده.

## Batch دوم داده منبع‌دار

Migration `0006_verified_unesco_destination_seed_batch2` هفت اثر دیگر را اضافه می‌کند:

1. تخت سلیمان — UNESCO WHC 1077
2. چغازنبیل — UNESCO WHC 113
3. مجموعه شیخ صفی‌الدین اردبیلی — UNESCO WHC 1345
4. مسجد جامع اصفهان — UNESCO WHC 1397
5. شهر سوخته — UNESCO WHC 1456
6. منظر فرهنگی میمند — UNESCO WHC 1423
7. هگمتانه — UNESCO WHC 1716

برای هر اثر، یک منبع توصیف رسمی، یک منبع نقشه رسمی، یک سند فارسیِ بازنویسی‌شده، دو Chunk و یک نگاشت دسته‌بندی ثبت می‌شود. دو مرجع تکمیلی رسمی نیز برای موقعیت اداری شهر سوخته و میمند اضافه شده‌اند. مختصات از نقشه رسمی به‌عنوان `property_reference` ثبت شده‌اند، نه ورودی بازدیدکننده یا مسیر دسترسی.

## چرا Embeddingها صفرند؟

جداول `embedding_spaces` و `chunk_embeddings` عمداً خالی هستند تا مدل، Provider یا بُعد برداری خاصی به پروژه تحمیل نشود. تست RAG با بردارهای مصنوعی ۳بعدی و ۴بعدی در تراکنش Rollbackشونده، قرارداد ذخیره‌سازی، جداسازی فضاهای برداری، ترتیب nearest-neighbor و رد ابعاد نامعتبر را بررسی می‌کند.

این تست، کیفیت معنایی، Recall فارسی یا صحت پاسخ LLM را اثبات نمی‌کند. آن مرحله بعد از اتصال الگوریتم RAG مورد تأیید مالک پروژه و مجموعه ارزیابی مستقل آن انجام خواهد شد.

## کنترل انتشار و مجوز

- هر ۱۷ رکورد UNESCO دارای منبع و نقطه مرجع رسمی هستند، اما همگی `needs_review` باقی می‌مانند؛ بنابراین تا تأیید تحریریه وارد پیشنهادهای Production یا RAG عملیاتی نمی‌شوند.
- مختصات UNESCO نقطه مرجع ملک ثبت‌شده است؛ از آن برای ادعای ورودی، ساعات بازدید، پارکینگ یا مسیر استفاده نمی‌شود.
- صفحات توصیفی UNESCO اعلامیه مجوز CC-BY-SA IGO 3.0 دارند. متن فارسی این بسته بازنویسی مستقل است، نه نقل‌قول؛ با این حال تعهدات انتساب و Share-Alike باید پیش از بازنشر تجاری توسط مالک محصول/مشاور حقوقی بررسی شود.
- ۱۳ اثر دیگر از فهرست ۳۰ اثر ثبت‌شده ایران در این دو Batch پوشش داده نشده‌اند. برخی از آن‌ها چندجزئی یا گسترده‌اند و باید پیش از ورود، مدل والد/جزء، هندسه و مرجع مکانی‌شان دقیق طراحی شود؛ یک نقطه دلخواه برای آن‌ها کافی نیست.
- داده مصنوعی، داده تأییدنشده یا داده صرفاً منبع‌دار ولی بازبینی‌نشده نباید به Production منتقل شود.
