# شمارش دقیق مورد انتظار دیتابیس — Pre-Codex v0.2

این سند Manifest مورد انتظار Seed اولیه است. تست `sql/tests/001_schema_seed_invariants.sql` تعداد جدول‌ها و تعدادهای اصلی را کنترل می‌کند و `sql/reports/final_row_counts.sql` مقدار واقعی هر جدول را در کنار مقدار مورد انتظار چاپ می‌کند. هر اختلافی باید Fail محسوب شود؛ نه اینکه تعداد مورد انتظار برای سبز شدن تست به‌صورت خودکار تغییر کند.

**۳۰ جدول متعلق به پروژه، ۳۲۹ ردیف مورد انتظار.** ردیف‌های صفر عمدی هستند؛ Embedding واقعی و رویدادهای واقعی قبل از اتصال Pipeline یا رخ دادن رویداد نباید ساخته شوند.

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
| `knowledge` | `knowledge_sources` | 24 |
| `knowledge` | `destinations` | 37 |
| `knowledge` | `destination_sources` | 49 |
| `knowledge` | `destination_tags` | 67 |
| `knowledge` | `destination_categories` | 12 |
| `knowledge` | `destination_category_map` | 23 |
| `knowledge` | `knowledge_documents` | 22 |
| `knowledge` | `knowledge_chunks` | 44 |
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
| `operations` | `dataset_import_batches` | 4 |
| `system` | `schema_migrations` | 6 |

| **TOTAL** | **30 project-owned tables** | **329** |

## ترکیب داده‌ها

- ۱۵ مقصد منتقل‌شده از SQL فعلی پروژه: همگی `needs_review` و بدون مختصات تأییدشده.
- ۱۲ مقصد مصنوعی QA + ۱۲ سند + ۲۴ Chunk: فقط برای تست؛ همگی `test_only` و `is_synthetic=true`.
- ۱۰ مقصد میراث جهانی دارای منابع رسمی + ۱۰ سند فارسی + ۲۰ Chunk: `verification_status=verified` اما `status=needs_review`؛ هیچ‌کدام فعلاً در Viewهای Production/RAG منتشر نمی‌شوند.
- ۲۴ منبع اطلاعات: ۱ Legacy، ۱ مصنوعی، ۲۰ صفحه/نقشه رسمی UNESCO و ۲ منبع تکمیلی اداری.
- یک گراف E2E مصنوعی برای کاربر، رضایت، ترجیحات، مکالمه، سفر، پیشنهاد، امتیاز، برنامه سفر و بازخورد.
- ۶ Migration ledger entry: یک Baseline مربوط به SQL قدیمی و پنج Migration کنترل‌شده.

## چرا Embeddingها صفرند؟

جداول `embedding_spaces` و `chunk_embeddings` عمداً خالی هستند تا هیچ مدل یا بُعد برداری پیش‌فرض در Schema تحمیل نشود. تست RAG با Vectorهای مصنوعی ۳بعدی و ۴بعدی داخل تراکنش Rollbackشونده، قرارداد ذخیره‌سازی، جداسازی فضای برداری، ترتیب nearest-neighbor و رد ابعاد نادرست را کنترل می‌کند. این تست کیفیت معنایی RAG یا Recall واقعی فارسی را تأیید نمی‌کند؛ آن بخش پس از اتصال الگوریتم مورد تأیید مالک پروژه تست خواهد شد.
