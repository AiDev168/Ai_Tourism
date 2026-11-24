# partner.review_events

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** Append-only audit of reviewer decisions.
- **دسترسی خواندن:** Reviewer/authorized backend paths; no general table access.
- **دسترسی نوشتن:** Written within audited decision routes only; no generic CRUD.
- **نمایش عمومی:** Never public.
- **API مدل/مسیر:** Inserted by organization verification/application/participation decision endpoints.
- **فیلد فرم UI:** Reviewer decision controls; no audit editor.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'review_event_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier for an immutable review audit event. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | Organization whose record was reviewed. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'entity_type' | 'text' | خیر | — | Reviewed object type: organization, verification_case, branch, service, offer, price, schedule, or availability. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'entity_id' | 'uuid' | خیر | — | Identifier of the reviewed object within the declared entity type. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'decision' | 'text' | خیر | — | Audited action: approve, reject, request_changes, suspend, reinstate, activate, or deactivate. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'reviewer_user_id' | 'uuid' | خیر | — | User account that performed the review action. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'reason' | 'text' | خیر | — | Required decision rationale, 10?2000 characters. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'policy_version' | 'text' | خیر | — | Version of the decision policy applied. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'occurred_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp when the review action occurred. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **review_events_decision_check** (`c`): `CHECK ((decision = ANY (ARRAY['approve'::text, 'reject'::text, 'request_changes'::text, 'suspend'::text, 'reinstate'::text])))`
- **review_events_entity_type_check** (`c`): `CHECK ((entity_type = ANY (ARRAY['organization'::text, 'verification_case'::text, 'branch'::text, 'service'::text, 'offer'::text, 'price'::text, 'schedule'::text, 'availability'::text])))`
- **review_events_reason_check** (`c`): `CHECK (((length(btrim(reason)) >= 10) AND (length(btrim(reason)) <= 2000)))`
- **review_events_organization_id_fkey** (`f`): `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- **review_events_reviewer_user_id_fkey** (`f`): `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **review_events_pkey** (`p`): `PRIMARY KEY (review_event_id)`

## ایندکس‌ها

- `ix_partner_review_events_org_time`: `CREATE INDEX ix_partner_review_events_org_time ON partner.review_events USING btree (organization_id, occurred_at DESC)`
- `review_events_pkey`: `CREATE UNIQUE INDEX review_events_pkey ON partner.review_events USING btree (review_event_id)`

## سیاست‌های RLS

- `review_events_member_read`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'organization_review'::text) OR partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text) OR partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text))`, with_check=`—`
- `review_events_platform_insert`: command=a, roles=[], using=`—`, with_check=`((reviewer_user_id = partner.current_actor_id()) AND (((entity_type = 'organization'::text) AND partner.has_platform_capability(partner.current_actor_id(), 'organization_review'::text)) OR ((entity_type = ANY (ARRAY['service'::text, 'branch'::text])) AND partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)) OR ((entity_type = ANY (ARRAY['offer'::text, 'price'::text, 'schedule'::text, 'availability'::text])) AND partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text))))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **9**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
