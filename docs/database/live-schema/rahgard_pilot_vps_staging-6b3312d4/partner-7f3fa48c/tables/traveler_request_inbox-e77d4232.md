# partner.traveler_request_inbox

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** Organization-scoped notification for a request revision.
- **دسترسی خواندن:** Active members of that organization.
- **دسترسی نوشتن:** System-created on each revision; client can mark viewed only.
- **نمایش عمومی:** Private and tenant-scoped.
- **API مدل/مسیر:** GET organization requests; POST /organizations/{organization_id}/requests/{inbox_event_id}/viewed.
- **فیلد فرم UI:** PartnerWorkspace eligible request inbox.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'inbox_event_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier of the organization inbox event. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | Recipient organization and tenant boundary. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'revision_id' | 'uuid' | خیر | — | Private request revision represented by the inbox event. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'event_kind' | 'text' | خیر | — | Event type: request_shared or request_revised. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp when the inbox event was created. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'viewed_at' | 'timestamp with time zone' | بله | — | Timestamp the authorized member marked the event viewed. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **traveler_request_inbox_event_kind_check** (`c`): `CHECK ((event_kind = ANY (ARRAY['request_shared'::text, 'request_revised'::text])))`
- **traveler_request_inbox_revision_id_fkey** (`f`): `FOREIGN KEY (revision_id) REFERENCES partner.traveler_request_revisions(revision_id) ON DELETE CASCADE`
- **traveler_request_inbox_revision_id_organization_id_fkey** (`f`): `FOREIGN KEY (revision_id, organization_id) REFERENCES partner.traveler_request_revisions(revision_id, organization_id) ON DELETE CASCADE`
- **traveler_request_inbox_pkey** (`p`): `PRIMARY KEY (inbox_event_id)`
- **traveler_request_inbox_revision_id_key** (`u`): `UNIQUE (revision_id)`

## ایندکس‌ها

- `ix_traveler_request_inbox_org_unread`: `CREATE INDEX ix_traveler_request_inbox_org_unread ON partner.traveler_request_inbox USING btree (organization_id, created_at DESC) WHERE (viewed_at IS NULL)`
- `traveler_request_inbox_pkey`: `CREATE UNIQUE INDEX traveler_request_inbox_pkey ON partner.traveler_request_inbox USING btree (inbox_event_id)`
- `traveler_request_inbox_revision_id_key`: `CREATE UNIQUE INDEX traveler_request_inbox_revision_id_key ON partner.traveler_request_inbox USING btree (revision_id)`

## سیاست‌های RLS

- `traveler_inbox_read`: command=r, roles=[], using=`partner.has_active_membership(organization_id, partner.current_actor_id())`, with_check=`—`
- `traveler_inbox_view`: command=w, roles=[], using=`partner.has_active_membership(organization_id, partner.current_actor_id())`, with_check=`partner.has_active_membership(organization_id, partner.current_actor_id())`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **6**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
