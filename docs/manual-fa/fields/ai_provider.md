# فرهنگ فیلدهای تنظیمات AI (ai_provider)

[فهرست اصلی](../README.md). مبنا cab603a7d40cfa35dd20de2ffb12a336d84f56ff؛ metadata پایلوت 0026 + DDL 0027، نه snapshot زنده. NULL قید SQL است نه الزام فرم. پیش‌فرض redacted پالایش شده؛ مقدار را حدس نزنید. توضیح خوانش نام/نوع اثبات معنای تجاری نیست. اطلاعات شخصی، رمز، توکن و ممیزی را مستقیم تغییر ندهید.

[metadata](../../database/rehearsed-schema-0026/catalog_metadata_snapshot.json) | [glossary](../../database/field_descriptions.json) | [DDL 0027](../../../engineering/pilot/sql/027_server_ai_provider_admin.sql) | [مرجع 0027](../../database/rehearsed-schema-0027/PROVIDER_ADMIN_FIELD_REFERENCE.md)

## ai_provider.active_routes

دامنه: تنظیمات AI؛ active_routes (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: DDL 0027.

مسیر دامنه: Owner /admin؛ provider_admin.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `capability` | `text` | خیر | ندارد | قابلیت؛ One independent routing slot per supported model capability; fixed migration bootstrap rows. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `revision_id` | `uuid` | بله | ندارد | شناسه ـ بازبینی؛ Active validated revision for this capability; administrator-selected; initially null. | فرم/API دامنه؛ راهنمای ورود | DDL/مرجع 0027 |
| `generation` | `bigint` | خیر | `0` | شمارنده افزایشی مسیر برای کنترل تعارض؛ Monotonic route switch generation for conflict/staleness detection; server-managed. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `updated_by` | `uuid` | بله | ندارد | حساب به‌روزرسان؛ Authenticated actor changing the route; server-managed. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `updated_at` | `timestamptz` | خیر | `now()` | زمان آخرین تغییر؛ Route change time; database-managed. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |

قیود دقیق DDL ستون‌ها:

```sql
capability TEXT PRIMARY KEY CHECK(capability IN ('chat','vision','embedding','reranking')),
revision_id UUID REFERENCES ai_provider.revisions(revision_id),
generation BIGINT NOT NULL DEFAULT 0 CHECK(generation>=0),
updated_by UUID REFERENCES identity.users(user_id),
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

## ai_provider.audit_events

دامنه: تنظیمات AI؛ audit_events (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: DDL 0027.

مسیر دامنه: Owner /admin؛ provider_admin.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `event_id` | `uuid` | خیر | `gen_random_uuid()` | event_id؛ Audit event identity. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |
| `actor_id` | `uuid` | بله | ندارد | شناسه ـ عامل؛ Authenticated actor; null only for system event. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |
| `action` | `text` | خیر | ندارد | عملیات؛ Sanitized action identifier such as profile update, validation, activation or rollback. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `target_type` | `text` | خیر | ندارد | نوع ـ هدف؛ Type of affected provider object. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `target_id` | `text` | بله | ندارد | شناسه ـ هدف؛ Opaque target identifier; not provider configuration or secret. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |
| `outcome` | `text` | خیر | ندارد | نتیجه؛ Result category; server-managed. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `metadata` | `jsonb` | خیر | `'{}'::jsonb` | فراداده؛ Minimal redacted audit metadata; must not hold prompts, API keys, TOTP or recovery material. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `occurred_at` | `timestamptz` | خیر | `now()` | زمان ـ وقوع؛ Audit event time. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |

قیود دقیق DDL ستون‌ها:

```sql
event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
actor_id UUID REFERENCES identity.users(user_id),
action TEXT NOT NULL CHECK(length(action) BETWEEN 1 AND 80),
target_type TEXT NOT NULL CHECK(length(target_type) BETWEEN 1 AND 40),
target_id TEXT,
outcome TEXT NOT NULL CHECK(outcome IN ('success','denied','failure')),
metadata JSONB NOT NULL DEFAULT '{}'::jsonb CHECK(jsonb_typeof(metadata)='object'),
occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

## ai_provider.fallback_policy

دامنه: تنظیمات AI؛ fallback_policy (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: DDL 0027.

مسیر دامنه: Owner /admin؛ provider_admin.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `capability` | `text` | خیر | ندارد | قابلیت؛ Capability whose fallback applies; one row per supported capability. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `enabled` | `boolean` | خیر | `FALSE` | فعال؛ Whether fallback is allowed; disabled by default and explicitly administrator-controlled. | فرم/API دامنه؛ راهنمای ورود | DDL/مرجع 0027 |
| `ordered_revision_ids` | `uuid[]` | خیر | `ARRAY[]::UUID[]` | ترتیب نسخه‌های جایگزین؛ Ordered validated revision candidates; when disabled this must be empty. | فرم/API دامنه؛ راهنمای ورود | DDL/مرجع 0027 |
| `updated_by` | `uuid` | بله | ندارد | حساب به‌روزرسان؛ Authenticated policy editor; server-managed. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `updated_at` | `timestamptz` | خیر | `now()` | زمان آخرین تغییر؛ Policy edit time; database-managed. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |

قیود دقیق DDL ستون‌ها:

```sql
capability TEXT PRIMARY KEY REFERENCES ai_provider.active_routes(capability),
enabled BOOLEAN NOT NULL DEFAULT FALSE,
ordered_revision_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
updated_by UUID REFERENCES identity.users(user_id),
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

قیود جدول:
- `CHECK(enabled OR cardinality(ordered_revision_ids)=0)`

## ai_provider.profiles

دامنه: تنظیمات AI؛ profiles (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: DDL 0027.

مسیر دامنه: Owner /admin؛ provider_admin.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `profile_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ پروفایل؛ Stable provider-profile identity; system-managed; API returns it for profile lifecycle operations. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |
| `name` | `text` | خیر | ندارد | نام؛ Human-readable administration label; Owner/provider administrator enters through the profile form. | فرم/API دامنه؛ راهنمای ورود | DDL/مرجع 0027 |
| `provider_kind` | `text` | خیر | ندارد | خانواده آداپتور ارائه‌دهنده؛ Adapter family selected by administrator; endpoint capability checks are enforced in API validation. | فرم/API دامنه؛ راهنمای ورود | DDL/مرجع 0027 |
| `enabled` | `boolean` | خیر | `TRUE` | فعال؛ Whether the profile may be selected; administrator-controlled, but it does not itself activate a route. | فرم/API دامنه؛ راهنمای ورود | DDL/مرجع 0027 |
| `archived_at` | `timestamptz` | بله | ندارد | زمان ـ بایگانی؛ When a profile was archived; automatic audit/lifecycle value; archived profiles must be disabled. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |
| `version` | `integer` | خیر | `1` | نسخه؛ Optimistic profile edit version used to reject stale updates; system incremented. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `created_by` | `uuid` | خیر | ندارد | حساب ایجادکننده؛ Authenticated creator; set by server, never client-supplied as authority. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `created_at` | `timestamptz` | خیر | `now()` | زمان ایجاد رکورد؛ Creation time; database-managed. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |
| `updated_at` | `timestamptz` | خیر | `now()` | زمان آخرین تغییر؛ Latest profile edit time; server-managed. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |

قیود دقیق DDL ستون‌ها:

```sql
profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
name TEXT NOT NULL UNIQUE CHECK(length(btrim(name)) BETWEEN 1 AND 100),
provider_kind TEXT NOT NULL CHECK(provider_kind IN ('lm_studio','openai_compatible')),
enabled BOOLEAN NOT NULL DEFAULT TRUE,
archived_at TIMESTAMPTZ,
version INTEGER NOT NULL DEFAULT 1 CHECK(version>0),
created_by UUID NOT NULL REFERENCES identity.users(user_id),
created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

قیود جدول:
- `CHECK(archived_at IS NULL OR enabled=FALSE)`

## ai_provider.revision_validations

دامنه: تنظیمات AI؛ revision_validations (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: DDL 0027.

مسیر دامنه: Owner /admin؛ provider_admin.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `validation_id` | `uuid` | خیر | `gen_random_uuid()` | validation_id؛ Validation record identity; system-managed. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |
| `revision_id` | `uuid` | خیر | ندارد | شناسه ـ بازبینی؛ Exact configuration tested; server-managed. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |
| `outcome` | `text` | خیر | ندارد | نتیجه؛ Result category from an administrator-triggered bounded validation; not proof of traveler inference by itself. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `details` | `jsonb` | خیر | `'{}'::jsonb` | جزئیات؛ Sanitized model/capability and diagnostic metadata; never contains API keys, prompts or raw provider envelopes. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `validated_by` | `uuid` | بله | ندارد | توسط/بر اساس ـ اعتبارسنجی؛ Authenticated administrator for interactive tests; null is reserved for system initiated validation. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `validated_at` | `timestamptz` | خیر | `now()` | زمان ـ اعتبارسنجی؛ Test time; database-managed. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |

قیود دقیق DDL ستون‌ها:

```sql
validation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
revision_id UUID NOT NULL REFERENCES ai_provider.revisions(revision_id),
outcome TEXT NOT NULL CHECK(outcome IN ('valid','invalid','unavailable')),
details JSONB NOT NULL DEFAULT '{}'::jsonb CHECK(jsonb_typeof(details)='object'),
validated_by UUID REFERENCES identity.users(user_id),
validated_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

## ai_provider.revisions

دامنه: تنظیمات AI؛ revisions (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: DDL 0027.

مسیر دامنه: Owner /admin؛ provider_admin.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `revision_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ بازبینی؛ Immutable configuration revision identity; system-managed. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |
| `profile_id` | `uuid` | خیر | ندارد | شناسه ـ پروفایل؛ Parent provider profile; server links revision to the selected profile. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |
| `revision_no` | `integer` | خیر | ندارد | revision_no؛ Monotonic revision number; server-managed. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `config` | `jsonb` | خیر | ندارد | تنظیمات؛ Validated non-secret endpoint, timeout, concurrency and capability/model configuration; administrator supplies supported values, API validates contract and safe endpoint policy. | فرم/API دامنه؛ راهنمای ورود | DDL/مرجع 0027 |
| `secret_ref` | `text` | بله | ندارد | ارجاع به راز Vault نه خود کلید؛ Opaque reference to the server-side AES-GCM vault; API accepts a secret transiently then stores only this reference. Never a key or secret value. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `created_by` | `uuid` | خیر | ندارد | حساب ایجادکننده؛ Authenticated revision author; server-managed. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `created_at` | `timestamptz` | خیر | `now()` | زمان ایجاد رکورد؛ Revision creation time; database-managed. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |

قیود دقیق DDL ستون‌ها:

```sql
revision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
profile_id UUID NOT NULL REFERENCES ai_provider.profiles(profile_id),
revision_no INTEGER NOT NULL CHECK(revision_no>0),
config JSONB NOT NULL CHECK(jsonb_typeof(config)='object'),
secret_ref TEXT CHECK(secret_ref IS NULL OR length(secret_ref) BETWEEN 8 AND 512),
created_by UUID NOT NULL REFERENCES identity.users(user_id),
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

قیود جدول:
- `UNIQUE(profile_id,revision_no)`

## ai_provider.usage_events

دامنه: تنظیمات AI؛ usage_events (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: DDL 0027.

مسیر دامنه: Owner /admin؛ provider_admin.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `usage_id` | `uuid` | خیر | `gen_random_uuid()` | usage_id؛ Usage record identity. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |
| `capability` | `text` | خیر | ندارد | قابلیت؛ Runtime capability invoked. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `revision_id` | `uuid` | بله | ندارد | شناسه ـ بازبینی؛ Configuration revision used; nullable when unavailable before route resolution. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |
| `outcome` | `text` | خیر | ندارد | نتیجه؛ Sanitized invocation result. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `latency_ms` | `integer` | بله | ندارد | زمان پاسخ بر حسب میلی‌ثانیه؛ Measured elapsed milliseconds; no request content. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `input_units` | `integer` | بله | ندارد | واحدها ـ ورودی؛ Provider-reported or safely estimated input units; null when unavailable. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `output_units` | `integer` | بله | ندارد | واحدها ـ خروجی؛ Provider-reported or safely estimated output units; null when unavailable. | فرم مستقیم احراز نشده | DDL/مرجع 0027 |
| `occurred_at` | `timestamptz` | خیر | `now()` | زمان ـ وقوع؛ Invocation time. Runtime can insert telemetry; administrator can read. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | DDL/مرجع 0027 |

قیود دقیق DDL ستون‌ها:

```sql
usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
capability TEXT NOT NULL CHECK(capability IN ('chat','vision','embedding','reranking')),
revision_id UUID REFERENCES ai_provider.revisions(revision_id),
outcome TEXT NOT NULL CHECK(outcome IN ('success','unavailable','rejected')),
latency_ms INTEGER CHECK(latency_ms IS NULL OR latency_ms>=0),
input_units INTEGER CHECK(input_units IS NULL OR input_units>=0),
output_units INTEGER CHECK(output_units IS NULL OR output_units>=0),
occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
```
