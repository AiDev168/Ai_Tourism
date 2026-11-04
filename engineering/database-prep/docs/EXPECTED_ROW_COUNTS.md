# شمارش دقیق مورد انتظار دیتابیس — Pre-Codex v0.3

این سند Manifest قطعی Seedهای Pre-Codex پس از Migration شماره 0006 است. تست `sql/tests/001_schema_seed_invariants.sql` تعداد جدول‌ها و تعدادهای ثابت اصلی را کنترل می‌کند و `sql/reports/final_row_counts.sql` تعداد واقعی و مورد انتظار هر جدول را گزارش می‌کند. هر اختلافی باید Fail شود؛ تعداد مورد انتظار هرگز برای سبز شدن تست به‌صورت خودکار تغییر نمی‌کند.

**۳۰ جدول متعلق به پروژه، ۴۱۹ ردیف مورد انتظار پس از اعمال Migration 0006.** ردیف‌های صفر عمدی هستند؛ Embedding واقعی، کلیک خروجی، فراخوانی LLM و رویداد Audit تا زمان وقوع واقعی نباید ساخته شوند.

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
| `knowledge` | `knowledge_sources` | 40 |
| `knowledge` | `destinations` | 44 |
| `knowledge` | `destination_sources` | 65 |
| `knowledge` | `destination_tags` | 88 |
| `knowledge` | `destination_categories` | 12 |
| `knowledge` | `destination_category_map` | 30 |
| `knowledge` | `knowledge_documents` | 29 |
| `knowledge` | `knowledge_chunks` | 58 |
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
| `operations` | `dataset_import_batches` | 5 |
| `system` | `schema_migrations` | 7 |

| **TOTAL** | **30 project-owned tables** | **419** |

## ترکیب داده‌ها

- **۱۵ مقصد قدیمی پروژه:** منتقل‌شده از `database/tourism_points.sql`؛ همگی `needs_review`، منبع اولیه pending و بدون مختصات تأییدشده.
- **۱۲ مقصد QA مصنوعی + ۱۲ سند + ۲۴ Chunk:** صرفاً برای تست؛ همه با `is_synthetic=true`، منشأ `synthetic_fixture` و وضعیت `test_only`.
- **۱۷ مقصد میراث جهانی منبع‌دار + ۱۷ سند فارسی + ۳۴ Chunk:** ۱۰ رکورد Batch اول و ۷ رکورد Batch دوم. منابع رسمی بررسی شده‌اند و `verification_status=verified` دارند، اما تمام مقصدها عمداً `status=needs_review` باقی می‌مانند و در Viewهای Production/RAG منتشر نمی‌شوند.
- **۴۰ منبع اطلاعات:** ۱ منبع Legacy، ۱ منبع Synthetic، ۳۴ صفحه/نقشه رسمی UNESCO (دو منبع برای هر یک از ۱۷ اثر) و ۴ مرجع رسمی تکمیلی برای کنترل موقعیت اداری.
- **۶۵ پیوند مقصد/منبع:** ۲۷ پیوند Legacy و QA، به‌اضافه ۳۸ پیوند مربوط به ۱۷ اثر واقعی.
- **۸۸ برچسب مقصد:** ۶۷ برچسب قبلی به‌اضافه ۲۱ برچسب منبع‌دار Batch دوم.
- **۳۰ نگاشت دسته‌بندی:** ۱۲ نگاشت Synthetic QA و ۱۸ نگاشت دسته‌بندی برای ۱۷ رکورد واقعی.
- **یک گراف E2E مصنوعی:** کاربر، رضایت، ترجیحات، مکالمه و پیام‌ها، سفر و محدودیت‌ها، پیشنهادها و امتیازها، برنامه سفر و بازخورد.
- **۵ Batch ورود داده:** ورودی قدیمی، Fixture دانشی، گراف E2E، UNESCO Batch اول و UNESCO Batch دوم.
- **۷ سابقه Migration:** یک Baseline مربوط به SQL قدیمی و شش Migration کنترل‌شده.

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
