# شمارش دقیق مورد انتظار دیتابیس — Shiraz integration v0.4

این سند Manifest قطعی Seedهای Pre-Codex پس از Migration شماره 0006 است. تست `sql/tests/001_schema_seed_invariants.sql` تعداد جدول‌ها و تعدادهای ثابت اصلی را کنترل می‌کند و `sql/reports/final_row_counts.sql` تعداد واقعی و مورد انتظار هر جدول را گزارش می‌کند. هر اختلافی باید Fail شود؛ تعداد مورد انتظار هرگز برای سبز شدن تست به‌صورت خودکار تغییر نمی‌کند.

**۳۰ جدول متعلق به پروژه، ۶۹۵ ردیف مورد انتظار پس از اعمال Migration 0007.** این مقدار، ۲۲ مقصد جدید و تکمیل یک ردیف موجود مراغه، ۱۸ منبع، ۵۱ رابطهٔ مقصد/منبع، ۱۲۰ برچسب خالص، ۱۷ نگاشت دسته، ۲۳ سند و ۲۳ Chunk، و یک Batch و یک سابقهٔ Migration جدید را نسبت به Baseline 0006 منعکس می‌کند. ردیف‌های صفر عمدی هستند؛ Embedding واقعی، کلیک خروجی، فراخوانی LLM و رویداد Audit تا زمان وقوع واقعی نباید ساخته شوند.

| Schema | Table | Expected rows |
|---|---|---:|
| `identity` | `users` | 1 |
| `identity` | `user_consents` | 1 |
| `identity` | `user_preferences` | 3 |
| `conversation` | `conversations` | 1 |
| `conversation` | `messages` | 4 |
| `travel` | `trips` | 1 |
| `travel` | `trip_constraints` | 3 |
| `travel` | `trip_interests` | 3 |
| `travel` | `itineraries` | 1 |
| `travel` | `itinerary_stops` | 6 |
| `knowledge` | `knowledge_sources` | 58 |
| `knowledge` | `destinations` | 66 |
| `knowledge` | `destination_sources` | 116 |
| `knowledge` | `destination_tags` | 208 |
| `knowledge` | `destination_categories` | 12 |
| `knowledge` | `destination_category_map` | 47 |
| `knowledge` | `knowledge_documents` | 52 |
| `knowledge` | `knowledge_chunks` | 81 |
| `knowledge` | `embedding_spaces` | 0 |
| `knowledge` | `chunk_embeddings` | 0 |
| `recommendation` | `recommendation_requests` | 1 |
| `recommendation` | `recommendations` | 3 |
| `recommendation` | `recommendation_score_components` | 9 |
| `integration` | `external_links` | 3 |
| `integration` | `outbound_clicks` | 0 |
| `operations` | `feedback` | 1 |
| `operations` | `ai_model_calls` | 0 |
| `operations` | `audit_events` | 0 |
| `operations` | `dataset_import_batches` | 6 |
| `system` | `schema_migrations` | 8 |

| **TOTAL** | **30 project-owned tables** | **695** |

## ترکیب داده‌ها

- **۱۴ مقصد قدیمی باقی‌مانده از پروژه:** از `database/tourism_points.sql`؛ همگی `needs_review`، منبع اولیه pending و بدون مختصات تأییدشده. هویت هر ۱۵ ردیف اصلی حفظ شده؛ رصدخانهٔ مراغه یکی از همان ردیف‌هاست که با Migration 0007 منبع‌دار شد و وضعیتش همچنان `needs_review` است.
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
