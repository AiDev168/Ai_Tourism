# partner.verification_cases

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** Organization evidence submission and reviewer decision lifecycle.
- **دسترسی خواندن:** Submitting organization owner/manager; separate reviewer capability for decisions.
- **دسترسی نوشتن:** POST submission; verification decision only through reviewer capability; self-review is forbidden.
- **نمایش عمومی:** Private. Evidence references must be reviewed independently.
- **API مدل/مسیر:** POST /organizations/{organization_id}/verification-cases; GET /platform/organization-review; POST /platform/verification-cases/{case_id}/decision.
- **فیلد فرم UI:** PartnerWorkspace evidence submission and reviewer queue.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'case_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier for one organization verification submission. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | Organization under review. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'status' | 'text' | خیر | '[redacted string default]' | Verification case lifecycle: draft, submitted, needs_information, verified, rejected, or withdrawn. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'evidence_refs' | 'jsonb' | خیر | '[redacted string default]' | JSON array of evidence references submitted for independent review; values are untrusted until checked. | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'submitted_by' | 'uuid' | بله | — | User account that submitted the evidence. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'reviewer_user_id' | 'uuid' | بله | — | Independent reviewer account; must differ from submitter for a final decision. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'policy_version' | 'text' | خیر | — | Identifier of the review policy used. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'decision_reason' | 'text' | بله | — | Reviewer rationale, if a decision has been made. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'submitted_at' | 'timestamp with time zone' | بله | — | Submission timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'decided_at' | 'timestamp with time zone' | بله | — | Final decision timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **verification_cases_check** (`c`): `CHECK (((status <> ALL (ARRAY['verified'::text, 'rejected'::text])) OR ((reviewer_user_id IS NOT NULL) AND (reviewer_user_id <> submitted_by) AND (decided_at IS NOT NULL))))`
- **verification_cases_evidence_refs_check** (`c`): `CHECK ((jsonb_typeof(evidence_refs) = 'array'::text))`
- **verification_cases_status_check** (`c`): `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'needs_information'::text, 'verified'::text, 'rejected'::text, 'withdrawn'::text])))`
- **verification_cases_organization_id_fkey** (`f`): `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- **verification_cases_reviewer_user_id_fkey** (`f`): `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **verification_cases_submitted_by_fkey** (`f`): `FOREIGN KEY (submitted_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **verification_cases_pkey** (`p`): `PRIMARY KEY (case_id)`

## ایندکس‌ها

- `ix_partner_verification_org_time`: `CREATE INDEX ix_partner_verification_org_time ON partner.verification_cases USING btree (organization_id, created_at DESC)`
- `verification_cases_pkey`: `CREATE UNIQUE INDEX verification_cases_pkey ON partner.verification_cases USING btree (case_id)`

## سیاست‌های RLS

- `verification_case_platform_review`: command=w, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'organization_review'::text)`, with_check=`(partner.has_platform_capability(partner.current_actor_id(), 'organization_review'::text) AND (reviewer_user_id = partner.current_actor_id()) AND (reviewer_user_id <> submitted_by) AND (status = ANY (ARRAY['needs_information'::text, 'verified'::text, 'rejected'::text, 'withdrawn'::text])))`
- `verification_case_select`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'organization_review'::text))`, with_check=`—`
- `verification_case_submit`: command=a, roles=[], using=`—`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text]) AND (submitted_by = partner.current_actor_id()) AND (reviewer_user_id IS NULL) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text, 'withdrawn'::text])))`
- `verification_case_update_self`: command=w, roles=[], using=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text]) AND (reviewer_user_id IS NULL))`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text]) AND (reviewer_user_id IS NULL) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text, 'needs_information'::text, 'withdrawn'::text])))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **11**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
