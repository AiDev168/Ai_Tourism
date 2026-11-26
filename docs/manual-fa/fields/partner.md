# فرهنگ فیلدهای شرکت‌ها (partner)

[فهرست اصلی](../README.md). مبنا cab603a7d40cfa35dd20de2ffb12a336d84f56ff؛ metadata پایلوت 0026 + DDL 0027، نه snapshot زنده. NULL قید SQL است نه الزام فرم. پیش‌فرض redacted پالایش شده؛ مقدار را حدس نزنید. توضیح خوانش نام/نوع اثبات معنای تجاری نیست. اطلاعات شخصی، رمز، توکن و ممیزی را مستقیم تغییر ندهید.

[metadata](../../database/rehearsed-schema-0026/catalog_metadata_snapshot.json) | [glossary](../../database/field_descriptions.json) | [DDL 0027](../../../engineering/pilot/sql/027_server_ai_provider_admin.sql) | [مرجع 0027](../../database/rehearsed-schema-0027/PROVIDER_ADMIN_FIELD_REFERENCE.md)

## partner.availability_snapshots

Time-bounded availability observation, not a future guarantee.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: PartnerWorkspace optional availability observation form/history..
قاعده نوشتن ثبت‌شده: POST observation only; do not overwrite history.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `snapshot_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ تصویر ثابت؛ Unique identifier for one time-bounded availability observation. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | Owning partner organization; tenant boundary used by foreign keys and RLS. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `offer_id` | `uuid` | خیر | ندارد | Offer whose availability was observed. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `schedule_id` | `uuid` | بله | ندارد | Related schedule occurrence source; nullable when the observation is not schedule-specific. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `occurrence_starts_at` | `timestamp with time zone` | بله | ندارد | Start instant of the observed service occurrence, stored as timestamptz. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `occurrence_ends_at` | `timestamp with time zone` | بله | ندارد | End instant of that occurrence when known; must not precede its start. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `availability_state` | `text` | خیر | ندارد | Observed state: available, unavailable, limited, unknown, or conflicting. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `available_count` | `integer` | بله | ندارد | Non-negative observed count when applicable; NULL is required for unknown state. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `source_kind` | `text` | خیر | ندارد | دسته ـ منبع؛ Provenance class: partner_asserted, approved_feed, or platform_observation. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `observed_at` | `timestamp with time zone` | بله | ندارد | زمان ـ مشاهده؛ Instant when availability was observed; required for available state. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `valid_from` | `timestamp with time zone` | بله | ندارد | از ـ اعتبار؛ Start of the interval for which this observation is represented as valid. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `valid_until` | `timestamp with time zone` | بله | ندارد | تا ـ اعتبار؛ End of the validity interval; do not treat stale data as current. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_by` | `uuid` | بله | ندارد | حساب ایجادکننده؛ User account that submitted the observation, if recorded. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ Database creation timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK ((availability_state = ANY (ARRAY['available'::text, 'unavailable'::text, 'limited'::text, 'unknown'::text, 'conflicting'::text])))`
- `CHECK (((available_count IS NULL) OR (available_count >= 0)))`
- `CHECK ((((availability_state = 'unknown'::text) AND (available_count IS NULL)) OR (availability_state <> 'unknown'::text)))`
- `CHECK (((availability_state <> 'available'::text) OR (observed_at IS NOT NULL)))`
- `CHECK (((occurrence_ends_at IS NULL) OR (occurrence_starts_at IS NULL) OR (occurrence_ends_at >= occurrence_starts_at)))`
- `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- `CHECK ((source_kind = ANY (ARRAY['partner_asserted'::text, 'approved_feed'::text, 'platform_observation'::text])))`
- `FOREIGN KEY (created_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (organization_id, offer_id, schedule_id) REFERENCES partner.offers(organization_id, offer_id, schedule_id) ON DELETE RESTRICT`
- `PRIMARY KEY (snapshot_id)`

## partner.branches

Optional service-location record with explicit coordinate role.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: No form in this workspace; location entry is intentionally absent..
قاعده نوشتن ثبت‌شده: No user-facing write API currently found.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `branch_id` | `uuid` | خیر | `gen_random_uuid()` | Unique identifier for an organization branch/service location. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | Owning organization and tenant boundary. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `display_name` | `text` | خیر | ندارد | Human-readable name of the branch. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `address_text` | `text` | بله | ندارد | Partner-provided address text; not independently geocoded. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `admin_area_id` | `bigint` | بله | ندارد | شناسه ـ محدوده ـ اداری/مدیریتی؛ Reference to a canonical administrative-area record when resolved. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `location` | `geometry(Point,4326)` | بله | ندارد | موقعیت؛ PostGIS Point in SRID 4326; the role column determines whether it is an approximate reference, service location, or entrance. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `location_role` | `text` | خیر | `[redacted string default]` | نقش ـ موقعیت؛ Coordinate role: service_location, entrance, approximate_reference, or unknown; entrance requires a coordinate source. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `coordinate_source` | `text` | بله | ندارد | منبع ـ مختصات؛ Provenance for coordinates; required for an entrance role. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `contact_public` | `text` | بله | ندارد | Partner-provided contact detail intended for public display only after applicable review. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `status` | `text` | خیر | `[redacted string default]` | وضعیت؛ Lifecycle state: draft, submitted, approved, suspended, or withdrawn. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ Database creation timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر؛ Timestamp of the latest profile update. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK (((location IS NULL) OR (location_role <> 'unknown'::text)))`
- `CHECK (((location_role <> 'entrance'::text) OR ((location IS NOT NULL) AND (coordinate_source IS NOT NULL))))`
- `CHECK (((length(btrim(display_name)) >= 1) AND (length(btrim(display_name)) <= 240)))`
- `CHECK ((location_role = ANY (ARRAY['service_location'::text, 'entrance'::text, 'approximate_reference'::text, 'unknown'::text])))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'suspended'::text, 'withdrawn'::text])))`
- `FOREIGN KEY (admin_area_id) REFERENCES geo.admin_areas(admin_area_id) ON DELETE RESTRICT`
- `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- `PRIMARY KEY (branch_id)`
- `UNIQUE (organization_id, branch_id)`

## partner.invitations

Hashed, expiring organization membership invitations.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: No UI in this milestone..
قاعده نوشتن ثبت‌شده: No user-facing invitation route currently registered.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `invitation_id` | `uuid` | خیر | `gen_random_uuid()` | Unique identifier for a membership invitation. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | Organization the invite targets. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `email_digest` | `bytea` | خیر | ندارد | اثر انگشت ـ ایمیل؛ One-way digest of the target email; raw email is not stored in this field. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `token_hash` | `bytea` | خیر | ندارد | هش ـ توکن؛ Unique one-way invitation token hash; never return the token hash to users. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `proposed_role` | `text` | خیر | ندارد | نقش ـ پیشنهادی؛ Role offered: manager, editor, availability_operator, or viewer. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `invited_by` | `uuid` | خیر | ندارد | User account that issued the invitation. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `expires_at` | `timestamp with time zone` | خیر | ندارد | زمان ـ انقضا؛ Timestamp after which the invitation cannot be accepted. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `accepted_at` | `timestamp with time zone` | بله | ندارد | زمان ـ پذیرفته‌شده؛ Timestamp of acceptance, if accepted. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `revoked_at` | `timestamp with time zone` | بله | ندارد | زمان ـ لغوشده؛ Timestamp of revocation, if revoked. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ Database creation timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK ((expires_at > created_at))`
- `CHECK (((accepted_at IS NULL) OR (revoked_at IS NULL)))`
- `CHECK ((octet_length(email_digest) = 32))`
- `CHECK ((proposed_role = ANY (ARRAY['manager'::text, 'editor'::text, 'availability_operator'::text, 'viewer'::text])))`
- `CHECK ((octet_length(token_hash) = 32))`
- `FOREIGN KEY (invited_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- `PRIMARY KEY (invitation_id)`
- `UNIQUE (token_hash)`

## partner.memberships

عضویت کاربران در یک سازمان و نقش/فعال‌بودن آن‌ها.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: No ordinary user form; owner/member management is not exposed in this workspace..
قاعده نوشتن ثبت‌شده: Created with company registration or invitation flow; no generic membership editor.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `membership_id` | `uuid` | خیر | `gen_random_uuid()` | Unique identifier for the organization membership. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | ارجاع به سازمان عضوپذیر. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ ارجاع به حساب شخص عضو سازمان. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `role` | `text` | خیر | ندارد | نقش؛ نقش عضو در سازمان؛ محدوده دسترسی از سیاست‌های مجوز استخراج شود. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `status` | `text` | خیر | `[redacted string default]` | وضعیت؛ وضعیت عضویت. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `invited_by` | `uuid` | بله | ندارد | Inviting user when membership originated from an invitation; nullable for owner registration. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `accepted_at` | `timestamp with time zone` | بله | ندارد | زمان ـ پذیرفته‌شده؛ زمان پذیرش عضویت یا دعوت. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `revoked_at` | `timestamp with time zone` | بله | ندارد | زمان ـ لغوشده؛ Timestamp that an active membership was revoked; must match revoked status. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ Database creation timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK (((status = 'revoked'::text) = (revoked_at IS NOT NULL)))`
- `CHECK ((role = ANY (ARRAY['owner'::text, 'manager'::text, 'editor'::text, 'availability_operator'::text, 'viewer'::text])))`
- `CHECK ((status = ANY (ARRAY['invited'::text, 'active'::text, 'revoked'::text, 'suspended'::text])))`
- `FOREIGN KEY (invited_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `PRIMARY KEY (membership_id)`
- `UNIQUE (organization_id, membership_id)`
- `UNIQUE (organization_id, user_id)`

## partner.offers

پیشنهاد تجاری/بسته خدمت که ممکن است زمان‌بندی و ظرفیت داشته باشد.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: PartnerWorkspace optional offer form and edit list..
قاعده نوشتن ثبت‌شده: Create/edit unpublished offer; capacity is non-negative and published state is reviewer-controlled.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `offer_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه یکتای پیشنهاد. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | سازمان مالک پیشنهاد. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `service_id` | `uuid` | خیر | ندارد | شناسه ـ خدمت؛ خدمت پایه پیشنهاد. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `schedule_id` | `uuid` | بله | ندارد | زمان‌بندی مرتبط، در صورت وجود. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `offer_type` | `text` | خیر | ندارد | نوع پیشنهاد با قرارداد ثابت. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `status` | `text` | خیر | `[redacted string default]` | وضعیت؛ وضعیت پیشنهاد. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `valid_from` | `timestamp with time zone` | بله | ندارد | از ـ اعتبار؛ آغاز دوره اعتبار پیشنهاد. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `valid_until` | `timestamp with time zone` | بله | ندارد | تا ـ اعتبار؛ پایان دوره اعتبار پیشنهاد. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `capacity_limit` | `integer` | بله | ندارد | حداکثر ظرفیت قابل ارائه؛ واحد از قرارداد API. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `created_by` | `uuid` | خیر | ندارد | حساب ایجادکننده؛ User account that created the offer. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ Database creation timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر؛ Timestamp of the latest editable offer change. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `published_at` | `timestamp with time zone` | بله | ندارد | زمان ـ منتشرشده؛ Publication timestamp; a published offer must have this value and publication is reviewer-controlled. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK (((capacity_limit IS NULL) OR (capacity_limit >= 0)))`
- `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- `CHECK (((status <> 'published'::text) OR (published_at IS NOT NULL)))`
- `CHECK (((length(btrim(offer_type)) >= 1) AND (length(btrim(offer_type)) <= 80)))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'published'::text, 'suspended'::text, 'withdrawn'::text, 'rejected'::text])))`
- `FOREIGN KEY (created_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT`
- `FOREIGN KEY (organization_id, service_id, schedule_id) REFERENCES partner.schedules(organization_id, service_id, schedule_id) ON DELETE RESTRICT`
- `PRIMARY KEY (offer_id)`
- `UNIQUE (organization_id, offer_id)`
- `UNIQUE (organization_id, offer_id, schedule_id)`

## partner.organizations

هویت حقوقی/عملیاتی سازمان گردشگری و وضعیت درخواست، احراز صلاحیت و مشارکت آن.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: PartnerWorkspace: company registration/profile and reviewer queue..
قاعده نوشتن ثبت‌شده: Owners/managers edit profile fields only; lifecycle transitions require the independent reviewer API.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `organization_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه یکتای سازمان برای ارتباط با اعضا، خدمات و صندوق درخواست‌ها. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `legal_name` | `text` | خیر | ندارد | نام حقوقی سازمان طبق مدارک رسمی (داده هویتی؛ دسترسی محدود). | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `display_name` | `text` | خیر | ندارد | عنوان نمایشی شرکت در محیط شریک و فهرست گیرندگان. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `organization_type` | `text` | خیر | ندارد | دسته سازمان مانند آژانس یا ارائه‌دهنده خدمت؛ مقادیر مجاز از enum/اعتبارسنجی API. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `registration_country` | `character(2)` | خیر | ندارد | کشور ـ ثبت؛ کشور ثبت حقوقی سازمان؛ کد/فرمت باید با اعتبارسنجی API تطبیق شود. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `registration_number` | `text` | بله | ندارد | شماره ـ ثبت؛ Optional legal registration identifier supplied by the organization; sensitive business identity data. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `primary_admin_area_id` | `bigint` | بله | ندارد | Optional resolved reference to the organization?s primary administrative area. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `verification_status` | `text` | خیر | `[redacted string default]` | وضعیت ـ راستی‌آزمایی؛ وضعیت احراز/تأیید سازمان توسط فرایند صاحب‌اختیار. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `participation_status` | `text` | خیر | `[redacted string default]` | وضعیت فعال‌بودن مشارکت سازمان در سامانه. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `application_status` | `text` | خیر | `[redacted string default]` | وضعیت درخواست عضویت/پذیرش سازمان. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_by` | `uuid` | خیر | ندارد | حساب ایجادکننده؛ شناسه کاربری که سازمان را ایجاد کرده است. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ زمان ایجاد رکورد در دیتابیس. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر؛ زمان آخرین به‌روزرسانی رکورد. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `closed_at` | `timestamp with time zone` | بله | ندارد | Timestamp that the organization was closed; a closed organization is not share-eligible. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `is_test` | `boolean` | خیر | `false` | نشان رکورد آزمایشی؛ Operator-controlled test-data marker; test organizations are excluded from share eligibility. | فرم مستقیم احراز نشده | فرهنگ موجود |

قیود جدول:
- `CHECK ((application_status = ANY (ARRAY['draft'::text, 'submitted'::text, 'needs_information'::text, 'approved'::text, 'rejected'::text, 'withdrawn'::text])))`
- `CHECK (((length(btrim(display_name)) >= 1) AND (length(btrim(display_name)) <= 240)))`
- `CHECK (((length(btrim(legal_name)) >= 1) AND (length(btrim(legal_name)) <= 240)))`
- `CHECK ((organization_type = ANY (ARRAY['company'::text, 'individual_business'::text, 'nonprofit'::text, 'public_body'::text, 'other'::text])))`
- `CHECK ((participation_status = ANY (ARRAY['inactive'::text, 'active'::text, 'suspended'::text, 'closed'::text])))`
- `CHECK ((registration_country ~ '^[A-Z]{2}$'::text))`
- `CHECK ((verification_status = ANY (ARRAY['pending'::text, 'verified'::text, 'rejected'::text, 'suspended'::text])))`
- `FOREIGN KEY (created_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (primary_admin_area_id) REFERENCES geo.admin_areas(admin_area_id) ON DELETE RESTRICT`
- `PRIMARY KEY (organization_id)`

## partner.platform_grant_events

دامنه: شرکت‌ها؛ platform_grant_events (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /partners و /admin؛ partners.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `event_id` | `uuid` | خیر | `gen_random_uuid()` | کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `grant_domain` | `text` | خیر | ندارد | دامنه مجوز اعطا یا لغوشده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `target_user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر ـ هدف؛ ارجاع به identity.users(user_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `capability` | `text` | خیر | ندارد | قابلیت مدیریتی یا مجوز مشخص | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `action` | `text` | خیر | ندارد | نوع عملیات ثبت‌شده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `actor_user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر ـ عامل؛ ارجاع به identity.users(user_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `reason` | `text` | خیر | ندارد | دلیل ثبت‌شده برای عملیات یا تصمیم | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `occurred_at` | `timestamp with time zone` | خیر | `now()` | زمان وقوع رویداد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((action = ANY (ARRAY['granted'::text, 'revoked'::text])))`
- `CHECK ((capability = ANY (ARRAY['organization_review'::text, 'service_review'::text, 'offer_review'::text, 'admin_overview_read'::text, 'candidate_review'::text, 'source_review'::text, 'catalogue_publish'::text])))`
- `CHECK ((target_user_id <> actor_user_id))`
- `CHECK ((((grant_domain = 'partner'::text) AND (capability = ANY (ARRAY['organization_review'::text, 'service_review'::text, 'offer_review'::text, 'admin_overview_read'::text]))) OR ((grant_domain = 'catalogue'::text) AND (capability = ANY (ARRAY['candidate_review'::text, 'source_review'::text, 'catalogue_publish'::text])))))`
- `CHECK ((grant_domain = ANY (ARRAY['partner'::text, 'catalogue'::text])))`
- `CHECK (((length(btrim(reason)) >= 10) AND (length(btrim(reason)) <= 1000)))`
- `FOREIGN KEY (actor_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (target_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `PRIMARY KEY (event_id)`

## partner.platform_grants

Operator-controlled platform capability grants.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: No UI. Do not expose generic admin CRUD..
قاعده نوشتن ثبت‌شده: No application-role INSERT/UPDATE after migration 0024; no self-service grant route.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ User receiving the platform capability. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `capability` | `text` | خیر | ندارد | قابلیت؛ Granted platform permission: organization_review, service_review, or offer_review. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `granted_by` | `uuid` | خیر | ندارد | توسط/بر اساس ـ اعطا‌شده؛ Operator user that issued the grant. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `reason` | `text` | خیر | ندارد | دلیل؛ Required audit rationale, 10?1000 characters. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `granted_at` | `timestamp with time zone` | خیر | `now()` | زمان ـ اعطا‌شده؛ Grant timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `revoked_at` | `timestamp with time zone` | بله | ندارد | زمان ـ لغوشده؛ Revocation timestamp; a non-NULL value disables the grant. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK ((capability = ANY (ARRAY['organization_review'::text, 'service_review'::text, 'offer_review'::text, 'admin_overview_read'::text])))`
- `CHECK (((revoked_at IS NULL) OR (revoked_at >= granted_at)))`
- `CHECK (((length(btrim(reason)) >= 10) AND (length(btrim(reason)) <= 1000)))`
- `FOREIGN KEY (granted_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `PRIMARY KEY (user_id, capability, granted_at)`

## partner.prices

اقلام قیمت پیشنهادی همراه واحد و کیفیت/اعتبار ثبت مبلغ.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: PartnerWorkspace optional price observation form/history..
قاعده نوشتن ثبت‌شده: POST observation only; previous observations are preserved.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `price_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه یکتای ردیف قیمت. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | سازمان مالک رکورد قیمت. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `offer_id` | `uuid` | خیر | ندارد | پیشنهاد مربوط به قیمت. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `price_state` | `text` | خیر | ندارد | وضعیت معتبر بودن، اعلام‌نشده بودن یا برآوردی‌بودن مبلغ. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `amount` | `numeric(14,2)` | بله | ندارد | مبلغ؛ مقدار عددی مبلغ مطابق precision و scale ستون. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `currency` | `character(3)` | بله | ندارد | ارز؛ واحد پول/کد ارز؛ با denomination و unit اشتباه نشود. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `denomination` | `text` | بله | ندارد | مقیاس نمایشی مبلغ مانند میلیون؛ واحدهای واقعی باید از قرارداد استخراج شوند. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `unit` | `text` | بله | ندارد | واحد؛ مبنای قیمت مثل نفر/شب/خدمت (بسته به enum/قرارداد). | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `tax_included` | `boolean` | بله | ندارد | Whether the asserted amount includes tax; nullable when not known or not applicable. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `valid_from` | `timestamp with time zone` | بله | ندارد | از ـ اعتبار؛ Start of the stated price validity interval, when provided. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `valid_until` | `timestamp with time zone` | بله | ندارد | تا ـ اعتبار؛ پایان اعتبار قیمت. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `observed_at` | `timestamp with time zone` | بله | ندارد | زمان ـ مشاهده؛ زمان مشاهده/دریافت قیمت. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `source_kind` | `text` | خیر | ندارد | دسته ـ منبع؛ Price provenance: partner_asserted, approved_feed, or platform_observation. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ Database creation timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK (((amount IS NULL) OR (amount >= (0)::numeric)))`
- `CHECK (((price_state <> 'known'::text) OR ((amount IS NOT NULL) AND (currency IS NOT NULL) AND (denomination IS NOT NULL) AND (unit IS NOT NULL) AND (observed_at IS NOT NULL))))`
- `CHECK (((price_state = 'known'::text) OR ((amount IS NULL) AND (currency IS NULL) AND (denomination IS NULL) AND (unit IS NULL) AND (tax_included IS NULL))))`
- `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- `CHECK (((currency IS NULL) OR (currency ~ '^[A-Z]{3}$'::text)))`
- `CHECK ((price_state = ANY (ARRAY['known'::text, 'unknown'::text, 'not_applicable'::text, 'conflicting'::text])))`
- `CHECK ((source_kind = ANY (ARRAY['partner_asserted'::text, 'approved_feed'::text, 'platform_observation'::text])))`
- `FOREIGN KEY (organization_id, offer_id) REFERENCES partner.offers(organization_id, offer_id) ON DELETE RESTRICT`
- `PRIMARY KEY (price_id)`

## partner.review_events

Append-only audit of reviewer decisions.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: Reviewer decision controls; no audit editor..
قاعده نوشتن ثبت‌شده: Written within audited decision routes only; no generic CRUD.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `review_event_id` | `uuid` | خیر | `gen_random_uuid()` | Unique identifier for an immutable review audit event. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | Organization whose record was reviewed. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `entity_type` | `text` | خیر | ندارد | Reviewed object type: organization, verification_case, branch, service, offer, price, schedule, or availability. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `entity_id` | `uuid` | خیر | ندارد | Identifier of the reviewed object within the declared entity type. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `decision` | `text` | خیر | ندارد | تصمیم؛ Audited action: approve, reject, request_changes, suspend, reinstate, activate, or deactivate. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `reviewer_user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر ـ بازبین؛ User account that performed the review action. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `reason` | `text` | خیر | ندارد | دلیل؛ Required decision rationale, 10?2000 characters. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `policy_version` | `text` | خیر | ندارد | نسخه ـ سیاست؛ Version of the decision policy applied. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `occurred_at` | `timestamp with time zone` | خیر | `now()` | زمان ـ وقوع؛ Timestamp when the review action occurred. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK ((decision = ANY (ARRAY['approve'::text, 'reject'::text, 'request_changes'::text, 'suspend'::text, 'reinstate'::text, 'activate'::text, 'deactivate'::text])))`
- `CHECK ((entity_type = ANY (ARRAY['organization'::text, 'verification_case'::text, 'branch'::text, 'service'::text, 'offer'::text, 'price'::text, 'schedule'::text, 'availability'::text])))`
- `CHECK (((length(btrim(reason)) >= 10) AND (length(btrim(reason)) <= 2000)))`
- `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `PRIMARY KEY (review_event_id)`

## partner.schedules

زمان‌بندی خدمت و بازه اعتبار اطلاعات زمانی.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: PartnerWorkspace optional schedule form and edit list..
قاعده نوشتن ثبت‌شده: Create/edit draft schedule; all instants use ISO timestamp and explicit time zone when times exist.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `schedule_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه یکتای زمان‌بندی. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | سازمان مالک زمان‌بندی. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `service_id` | `uuid` | خیر | ندارد | شناسه ـ خدمت؛ خدمت مربوط به زمان‌بندی. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `schedule_type` | `text` | خیر | ندارد | دسته زمان‌بندی و الگوی اجرای آن. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `timezone` | `text` | بله | ندارد | شناسه منطقه زمانی معتبر IANA، در صورت انطباق با قرارداد. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `starts_at` | `timestamp with time zone` | بله | ندارد | لحظه یا زمان شروع. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `ends_at` | `timestamp with time zone` | بله | ندارد | لحظه یا زمان پایان. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `recurrence` | `jsonb` | بله | ندارد | قاعده تکرار؛ فرمت دقیق از API/SQL. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `status` | `text` | خیر | `[redacted string default]` | وضعیت؛ وضعیت زمان‌بندی. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `observed_at` | `timestamp with time zone` | بله | ندارد | زمان ـ مشاهده؛ زمان آخرین مشاهده/تأیید این داده زمانی. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `valid_until` | `timestamp with time zone` | بله | ندارد | تا ـ اعتبار؛ انقضای اعتبار اطلاع زمان‌بندی. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ Database creation timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK (((ends_at IS NULL) OR (starts_at IS NULL) OR (ends_at >= starts_at)))`
- `CHECK (((valid_until IS NULL) OR (observed_at IS NULL) OR (valid_until >= observed_at)))`
- `CHECK ((((starts_at IS NULL) AND (ends_at IS NULL)) OR (timezone IS NOT NULL)))`
- `CHECK (((recurrence IS NULL) OR (jsonb_typeof(recurrence) = 'object'::text)))`
- `CHECK ((schedule_type = ANY (ARRAY['opening_window'::text, 'departure'::text, 'appointment'::text, 'event'::text, 'other'::text])))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'withdrawn'::text, 'expired'::text])))`
- `FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT`
- `PRIMARY KEY (schedule_id)`
- `UNIQUE (organization_id, schedule_id)`
- `UNIQUE (organization_id, service_id, schedule_id)`

## partner.service_destinations

Relationship from a company service to a canonical published destination.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: PartnerWorkspace optional destination-link form; only API-returned published choices..
قاعده نوشتن ثبت‌شده: POST only in current API; relationship is not a publication decision.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `organization_id` | `uuid` | خیر | ندارد | Owning organization and tenant boundary. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `service_id` | `uuid` | خیر | ندارد | شناسه ـ خدمت؛ Organization-owned service related to the canonical destination. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد؛ Canonical destination identifier; API accepts only currently published destinations. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `relation_type` | `text` | خیر | ندارد | Relationship: at, serves, near, or route_endpoint. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `evidence_note` | `text` | بله | ندارد | یادداشت ـ شاهد؛ Optional partner-supplied context for this association; not verification evidence by itself. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `status` | `text` | خیر | `[redacted string default]` | وضعیت؛ Review lifecycle: draft, submitted, approved, rejected, or withdrawn. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ Database creation timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK ((relation_type = ANY (ARRAY['at'::text, 'serves'::text, 'near'::text, 'route_endpoint'::text])))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'rejected'::text, 'withdrawn'::text])))`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- `FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT`
- `PRIMARY KEY (service_id, destination_id)`

## partner.service_localizations

نام و توضیح ترجمه‌شده خدمت در زبان‌های قابل پشتیبانی.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: PartnerWorkspace service name/description fields..
قاعده نوشتن ثبت‌شده: Written as part of service create/update API; no independent SQL form.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `organization_id` | `uuid` | خیر | ندارد | مالک سازمانی ترجمه. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `service_id` | `uuid` | خیر | ندارد | شناسه ـ خدمت؛ ارجاع به خدمت. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `locale` | `text` | خیر | ندارد | زبان/منطقه؛ زبان/محل نمایشی، مانند fa-IR یا en-US بر اساس قرارداد API. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `display_name` | `text` | خیر | ندارد | نام نمایشی خدمت در آن زبان. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `description` | `text` | بله | ندارد | شرح؛ توضیحات خدمت در همان زبان. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `content_status` | `text` | خیر | `[redacted string default]` | وضعیت ـ محتوا؛ Locale content lifecycle: draft, submitted, approved, rejected, or withdrawn. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `reviewed_at` | `timestamp with time zone` | بله | ندارد | زمان ـ بازبینی؛ Timestamp of editorial review when present. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ Database creation timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر؛ Timestamp of the latest localization update. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK ((content_status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'rejected'::text, 'withdrawn'::text])))`
- `CHECK (((length(btrim(display_name)) >= 1) AND (length(btrim(display_name)) <= 240)))`
- `CHECK ((locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text])))`
- `FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT`
- `PRIMARY KEY (service_id, locale)`

## partner.services

خدمات قابل ارائه توسط سازمان؛ اطلاعات عمومی خدمت از قرارداد انتشار جداست.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: PartnerWorkspace first-service form and editable service list..
قاعده نوشتن ثبت‌شده: Create/update private draft or submitted values; service key is generated server-side.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `service_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ خدمت؛ شناسه یکتای خدمت. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | سازمان مالک خدمت. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `branch_id` | `uuid` | بله | ندارد | شعبه مرتبط، اگر خدمت شعبه‌محور باشد. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `service_type` | `text` | خیر | ندارد | نوع ـ خدمت؛ نوع خدمت با مقادیر مجاز تعریف‌شده در API/دیتابیس. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `service_key` | `text` | خیر | ندارد | کلید ـ خدمت؛ شناسه/کلید کسب‌وکاری خدمت نزد سازمان. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `status` | `text` | خیر | `[redacted string default]` | وضعیت؛ وضعیت چرخه عمر خدمت. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `public_fields` | `jsonb` | خیر | `[redacted string default]` | فراداده/فیلدهای عمومی‌شدنی خدمت؛ کلیدهای JSON باید جداگانه مستند شوند. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `internal_notes` | `text` | بله | ندارد | Private organization-side notes; never part of public service output. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_by` | `uuid` | خیر | ندارد | حساب ایجادکننده؛ کاربر ثبت‌کننده خدمت. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ زمان ایجاد خدمت. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر؛ Timestamp of the latest service change. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `published_at` | `timestamp with time zone` | بله | ندارد | زمان ـ منتشرشده؛ Publication timestamp; required only for published state and set by an authorized review path. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK (((status <> 'published'::text) OR (published_at IS NOT NULL)))`
- `CHECK ((jsonb_typeof(public_fields) = 'object'::text))`
- `CHECK (((length(btrim(service_key)) >= 1) AND (length(btrim(service_key)) <= 160)))`
- `CHECK (((length(btrim(service_type)) >= 1) AND (length(btrim(service_type)) <= 80)))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'published'::text, 'suspended'::text, 'withdrawn'::text, 'rejected'::text])))`
- `FOREIGN KEY (created_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (organization_id, branch_id) REFERENCES partner.branches(organization_id, branch_id) ON DELETE RESTRICT`
- `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- `PRIMARY KEY (service_id)`
- `UNIQUE (organization_id, service_id)`
- `UNIQUE (organization_id, service_key)`

## partner.share_eligible_organizations

نمای فقط‌خواندنی سازمان‌های فعال و تأییدشده که می‌توانند درخواست مسافر دریافت کنند.

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: TravelerWorkspace company-sharing selector; absent when there are no eligible organizations..
قاعده نوشتن ثبت‌شده: Read-only view.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `organization_id` | `uuid` | بله | ندارد | شناسه سازمان گیرنده. | نمای مشتق؛ بدون ورود | فرهنگ موجود |
| `display_name` | `text` | بله | ندارد | نام نمایشی گیرنده. | نمای مشتق؛ بدون ورود | فرهنگ موجود |
| `organization_type` | `text` | بله | ندارد | نوع سازمان گیرنده. | نمای مشتق؛ بدون ورود | فرهنگ موجود |

[مرجع lineage](../../database/architecture-usage/view_column_lineage.csv)؛ تطبیق هر خروجی با مبدأ لازم است.

## partner.traveler_request_inbox

Organization-scoped notification for a request revision.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: PartnerWorkspace eligible request inbox..
قاعده نوشتن ثبت‌شده: System-created on each revision; client can mark viewed only.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `inbox_event_id` | `uuid` | خیر | `gen_random_uuid()` | Unique identifier of the organization inbox event. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | Recipient organization and tenant boundary. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `revision_id` | `uuid` | خیر | ندارد | شناسه ـ بازبینی؛ Private request revision represented by the inbox event. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `event_kind` | `text` | خیر | ندارد | Event type: request_shared or request_revised. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ Timestamp when the inbox event was created. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `viewed_at` | `timestamp with time zone` | بله | ندارد | Timestamp the authorized member marked the event viewed. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK ((event_kind = ANY (ARRAY['request_shared'::text, 'request_revised'::text])))`
- `FOREIGN KEY (revision_id) REFERENCES partner.traveler_request_revisions(revision_id) ON DELETE CASCADE`
- `FOREIGN KEY (revision_id, organization_id) REFERENCES partner.traveler_request_revisions(revision_id, organization_id) ON DELETE CASCADE`
- `PRIMARY KEY (inbox_event_id)`
- `UNIQUE (revision_id)`

## partner.traveler_request_revisions

نسخه‌های تغییرناپذیر/بازنگری‌شده درخواست و برنامه اشتراک‌گذاری‌شده با سازمان.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: PartnerWorkspace protected inbox and request/itinerary views..
قاعده نوشتن ثبت‌شده: Created by the revision-capture function; no direct client write grant.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `revision_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ بازبینی؛ شناسه نسخه بازنگری. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `share_id` | `uuid` | خیر | ندارد | اشتراک مرتبط. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | سازمان دریافت‌کننده. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `revision_number` | `integer` | خیر | ندارد | شماره ـ بازبینی؛ شماره ترتیبی نسخه برای همان اشتراک. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `trip_version` | `integer` | خیر | ندارد | نسخه ـ سفر؛ نسخه برنامه/سفر مرجع. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `event_kind` | `text` | خیر | ندارد | نوع رویداد نسخه مانند اشتراک جدید یا بازنگری. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `request_snapshot` | `jsonb` | خیر | ندارد | تصویر ثابت ـ درخواست؛ نمای ثابت و محدودشده شرایط سفر در لحظه ارسال؛ اطلاعات شخصی باید کنترل دسترسی داشته باشد. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `itinerary_snapshot` | `jsonb` | خیر | `[redacted string default]` | تصویر ثابت ـ برنامه سفر؛ نمای ثابت برنامه سفر در لحظه ارسال. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_by` | `uuid` | خیر | ندارد | حساب ایجادکننده؛ Traveler account whose authorized change generated this immutable revision. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ زمان ایجاد نسخه. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی، نه واقعی؛ علامت داده آزمایشی؛ نباید در صندوق تولیدی به کاربر واقعی نشان داده شود. | فرم مستقیم احراز نشده | فرهنگ موجود |

قیود جدول:
- `CHECK ((event_kind = ANY (ARRAY['request_shared'::text, 'request_revised'::text])))`
- `CHECK ((jsonb_typeof(itinerary_snapshot) = 'object'::text))`
- `CHECK ((jsonb_typeof(request_snapshot) = 'object'::text))`
- `CHECK ((revision_number > 0))`
- `CHECK ((trip_version > 0))`
- `FOREIGN KEY (created_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (share_id, organization_id) REFERENCES partner.traveler_request_shares(share_id, organization_id) ON DELETE CASCADE`
- `PRIMARY KEY (revision_id)`
- `UNIQUE (revision_id, organization_id)`
- `UNIQUE (share_id, revision_number)`

## partner.traveler_request_shares

اشتراک‌گذاری موردی و رضایت‌مندانه درخواست یک سفر با یک سازمان.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: Traveler journey company-sharing consent flow..
قاعده نوشتن ثبت‌شده: Created only after explicit traveler consent; traveler may revoke.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `share_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه یکتای اشتراک‌گذاری. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `trip_id` | `uuid` | خیر | ندارد | شناسه ـ سفر؛ سفر مبدا درخواست. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `traveler_id` | `uuid` | خیر | ندارد | شناسه ـ مسافر؛ مالک درخواست سفر. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | سازمان دریافت‌کننده درخواست. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `consent_policy_version` | `text` | خیر | ندارد | نسخه ـ سیاست ـ رضایت؛ نسخه قرارداد رضایت معتبر هنگام اشتراک‌گذاری. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `include_original_request` | `boolean` | خیر | `false` | مشخص می‌کند متن اولیه خام درخواست نیز با رضایت صریح ضمیمه شده یا خیر. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `consented_at` | `timestamp with time zone` | خیر | `now()` | زمان ـ رضایت ثبت‌شده؛ زمان اخذ رضایت و ایجاد دسترسی. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `revoked_at` | `timestamp with time zone` | بله | ندارد | زمان ـ لغوشده؛ زمان لغو دسترسی، در صورت وقوع. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ Timestamp the explicit traveler-authorized share was created. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK (((revoked_at IS NULL) OR (revoked_at >= consented_at)))`
- `CHECK (((length(btrim(consent_policy_version)) >= 1) AND (length(btrim(consent_policy_version)) <= 80)))`
- `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- `FOREIGN KEY (traveler_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- `PRIMARY KEY (share_id)`
- `UNIQUE (share_id, organization_id)`
- `UNIQUE (trip_id, organization_id)`

## partner.trip_company_responses

Company response to an authorized traveler request revision and traveler decision.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: CompanyResponseActions and traveler response panel..
قاعده نوشتن ثبت‌شده: Company submits response; traveler alone updates decision state.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `response_id` | `uuid` | خیر | `gen_random_uuid()` | Unique identifier for the company response. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `client_request_id` | `uuid` | خیر | ندارد | Client-provided idempotency identifier, unique within a share. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `share_id` | `uuid` | خیر | ندارد | Traveler-authorized share being answered. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | Recipient organization and tenant boundary. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `revision_id` | `uuid` | خیر | ندارد | شناسه ـ بازبینی؛ Exact shared request revision the response addresses. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `trip_id` | `uuid` | خیر | ندارد | شناسه ـ سفر؛ Traveler trip referenced by the share. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `traveler_id` | `uuid` | خیر | ندارد | شناسه ـ مسافر؛ Trip owner who receives and decides the response. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `submitted_by` | `uuid` | خیر | ندارد | توسط/بر اساس ـ ارسال‌شده؛ Authorized company member who submitted the response. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `response_kind` | `text` | خیر | ندارد | accepted_as_requested or counter_offer. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `message` | `text` | خیر | `[redacted string default]` | پیام؛ Company response text, maximum 2000 characters. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `proposed_price_toman` | `numeric(14,2)` | بله | ندارد | Optional proposed price in Iranian toman; this is not a payment or booking transaction. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `proposed_start_date` | `date` | بله | ندارد | Optional proposed Gregorian ISO date; set together with proposed_end_date. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `proposed_end_date` | `date` | بله | ندارد | Optional proposed Gregorian ISO date; must be on or after proposed_start_date. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `proposed_schedule_notes` | `text` | خیر | `[redacted string default]` | Optional counter-offer schedule notes, maximum 1500 characters. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `traveler_decision` | `text` | خیر | `[redacted string default]` | تصمیم ـ مسافر؛ Traveler-only decision: pending, accepted, or declined. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `decided_at` | `timestamp with time zone` | بله | ندارد | زمان ـ تصمیم؛ Timestamp of traveler decision; NULL exactly while decision is pending. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ Database creation timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی، نه واقعی؛ Test marker constrained to false for persisted company responses. | فرم مستقیم احراز نشده | فرهنگ موجود |

قیود جدول:
- `CHECK (((proposed_start_date IS NULL) = (proposed_end_date IS NULL)))`
- `CHECK (((proposed_end_date IS NULL) OR (proposed_end_date >= proposed_start_date)))`
- `CHECK (((response_kind <> 'accepted_as_requested'::text) OR ((proposed_price_toman IS NULL) AND (proposed_start_date IS NULL) AND (proposed_schedule_notes = ''::text))))`
- `CHECK (((response_kind <> 'counter_offer'::text) OR ((proposed_price_toman IS NOT NULL) OR (proposed_start_date IS NOT NULL) OR (length(btrim(proposed_schedule_notes)) > 0))))`
- `CHECK (((traveler_decision = 'pending'::text) = (decided_at IS NULL)))`
- `CHECK ((is_synthetic = false))`
- `CHECK ((length(message) <= 2000))`
- `CHECK ((proposed_price_toman >= (0)::numeric))`
- `CHECK ((length(proposed_schedule_notes) <= 1500))`
- `CHECK ((response_kind = ANY (ARRAY['accepted_as_requested'::text, 'counter_offer'::text])))`
- `CHECK ((traveler_decision = ANY (ARRAY['pending'::text, 'accepted'::text, 'declined'::text])))`
- `FOREIGN KEY (revision_id, organization_id) REFERENCES partner.traveler_request_revisions(revision_id, organization_id) ON DELETE CASCADE`
- `FOREIGN KEY (share_id, organization_id) REFERENCES partner.traveler_request_shares(share_id, organization_id) ON DELETE CASCADE`
- `FOREIGN KEY (submitted_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (traveler_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- `PRIMARY KEY (response_id)`
- `UNIQUE (share_id, client_request_id)`

## partner.verification_cases

Organization evidence submission and reviewer decision lifecycle.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: PartnerWorkspace evidence submission and reviewer queue..
قاعده نوشتن ثبت‌شده: POST submission; verification decision only through reviewer capability; self-review is forbidden.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `case_id` | `uuid` | خیر | `gen_random_uuid()` | Unique identifier for one organization verification submission. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `organization_id` | `uuid` | خیر | ندارد | Organization under review. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `status` | `text` | خیر | `[redacted string default]` | وضعیت؛ Verification case lifecycle: draft, submitted, needs_information, verified, rejected, or withdrawn. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `evidence_refs` | `jsonb` | خیر | `[redacted string default]` | ارجاعات ـ شاهد؛ JSON array of evidence references submitted for independent review; values are untrusted until checked. | فرم/API دامنه؛ راهنمای ورود | فرهنگ موجود |
| `submitted_by` | `uuid` | بله | ندارد | توسط/بر اساس ـ ارسال‌شده؛ User account that submitted the evidence. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `reviewer_user_id` | `uuid` | بله | ندارد | شناسه ـ کاربر ـ بازبین؛ Independent reviewer account; must differ from submitter for a final decision. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `policy_version` | `text` | خیر | ندارد | نسخه ـ سیاست؛ Identifier of the review policy used. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `decision_reason` | `text` | بله | ندارد | دلیل ـ تصمیم؛ Reviewer rationale, if a decision has been made. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `submitted_at` | `timestamp with time zone` | بله | ندارد | زمان ـ ارسال‌شده؛ Submission timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `decided_at` | `timestamp with time zone` | بله | ندارد | زمان ـ تصمیم؛ Final decision timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ Database creation timestamp. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK (((status <> ALL (ARRAY['verified'::text, 'rejected'::text])) OR ((reviewer_user_id IS NOT NULL) AND (reviewer_user_id <> submitted_by) AND (decided_at IS NOT NULL))))`
- `CHECK ((jsonb_typeof(evidence_refs) = 'array'::text))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'needs_information'::text, 'verified'::text, 'rejected'::text, 'withdrawn'::text])))`
- `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (submitted_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `PRIMARY KEY (case_id)`
