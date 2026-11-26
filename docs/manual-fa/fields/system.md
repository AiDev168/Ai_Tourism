# فرهنگ فیلدهای سیستم (system)

[فهرست اصلی](../README.md). مبنا cab603a7d40cfa35dd20de2ffb12a336d84f56ff؛ metadata پایلوت 0026 + DDL 0027، نه snapshot زنده. NULL قید SQL است نه الزام فرم. پیش‌فرض redacted پالایش شده؛ مقدار را حدس نزنید. توضیح خوانش نام/نوع اثبات معنای تجاری نیست. اطلاعات شخصی، رمز، توکن و ممیزی را مستقیم تغییر ندهید.

[metadata](../../database/rehearsed-schema-0026/catalog_metadata_snapshot.json) | [glossary](../../database/field_descriptions.json) | [DDL 0027](../../../engineering/pilot/sql/027_server_ai_provider_admin.sql) | [مرجع 0027](../../database/rehearsed-schema-0027/PROVIDER_ADMIN_FIELD_REFERENCE.md)

## system.schema_migrations

دامنه: سیستم؛ schema_migrations (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ابزار مهاجرت.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `migration_id` | `text` | خیر | ندارد | شناسه ـ مهاجرت؛ کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `sha256` | `text` | خیر | ندارد | SHA-256 | سامانه/اپراتور مجاز | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `applied_at` | `timestamp with time zone` | خیر | `now()` | زمان ـ اعمال‌شده | سامانه/اپراتور مجاز | خوانش نام/نوع؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((length(sha256) = 64))`
- `PRIMARY KEY (migration_id)`
